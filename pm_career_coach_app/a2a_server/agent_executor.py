"""
A2A AgentExecutor for PM Career Coach.

Implements the canonical 4-event streaming pattern from the helloworld reference:
  1. Task (SUBMITTED)  — initial task object
  2. TaskStatusUpdateEvent (WORKING) — one per tool call, from router ProgressEvents
  3. TaskArtifactUpdateEvent — the final coaching answer
  4. TaskStatusUpdateEvent (COMPLETED) — signals end of processing

Multi-turn support:
  Conversation history per context_id is kept in _history_store (module-level dict).
  After each successful execution the user prompt and assistant reply are appended.
  On the next request with the same context_id the prior history is prepended to
  the router's messages list, giving Claude full conversation context.
"""

import logging
from typing import Final

from a2a.helpers import new_task_from_user_message, new_text_artifact, new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types.a2a_pb2 import (
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from .router import FinalAnswerEvent, ProgressEvent, route

logger = logging.getLogger(__name__)

# In-memory multi-turn history store.
# Maps context_id -> list of Anthropic message dicts {"role": ..., "content": ...}.
# Cleared on server restart — acceptable for Spec 1 (InMemoryTaskStore has the
# same lifetime). Replace with a persistent store in a later spec if needed.
_history_store: dict[str, list[dict]] = {}

_MAX_HISTORY_MESSAGES: Final[int] = 20  # cap to avoid unbounded growth


class CareerCoachAgentExecutor(AgentExecutor):
    """Handles incoming A2A Tasks and drives the router loop."""

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        # 1. Extract text from the incoming message.
        prompt_parts: list[str] = []
        for part in context.message.parts:
            if part.HasField("text") and part.text:
                prompt_parts.append(part.text)
        prompt = "\n".join(prompt_parts).strip()

        if not prompt:
            prompt = "(empty message)"

        # 2. Emit initial Task event (SUBMITTED).
        task = context.current_task or new_task_from_user_message(context.message)
        await event_queue.enqueue_event(task)

        # 3. Retrieve prior conversation history for this context_id.
        context_history = list(_history_store.get(context.context_id, []))

        collected_answer = ""

        try:
            # 4. Drive the routing loop, mapping RouterEvents to A2A events.
            async for event in route(prompt, context_history):
                if isinstance(event, ProgressEvent):
                    await event_queue.enqueue_event(
                        TaskStatusUpdateEvent(
                            task_id=context.task_id,
                            context_id=context.context_id,
                            status=TaskStatus(
                                state=TaskState.TASK_STATE_WORKING,
                                message=new_text_message(event.message),
                            ),
                        )
                    )

                elif isinstance(event, FinalAnswerEvent):
                    collected_answer = event.text
                    await event_queue.enqueue_event(
                        TaskArtifactUpdateEvent(
                            task_id=context.task_id,
                            context_id=context.context_id,
                            artifact=new_text_artifact(
                                name="coaching_result",
                                text=event.text,
                            ),
                        )
                    )

            # 5. Update history for the next turn in this context.
            updated_history = list(context_history)
            updated_history.append({"role": "user", "content": prompt})
            if collected_answer:
                updated_history.append(
                    {"role": "assistant", "content": collected_answer}
                )
            # Trim to keep the history bounded.
            _history_store[context.context_id] = updated_history[-_MAX_HISTORY_MESSAGES:]

            # 6. Final COMPLETED status.
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=context.task_id,
                    context_id=context.context_id,
                    status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
                )
            )

        except Exception as exc:
            logger.exception("Error executing task %s", context.task_id)
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=context.task_id,
                    context_id=context.context_id,
                    status=TaskStatus(
                        state=TaskState.TASK_STATE_FAILED,
                        message=new_text_message(f"Error: {exc}"),
                    ),
                )
            )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        raise NotImplementedError("Cancel not supported in this version")
