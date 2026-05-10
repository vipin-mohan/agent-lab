"""
Claude tool-use routing layer.

route() is an async generator: it yields RouterEvents as the LLM
decides which skill(s) to call and accumulates results. The AgentExecutor
iterates over these events and maps them to A2A protocol events.

Why a separate Anthropic client here (not reusing core/llm.py):
  core/llm.py uses a one-shot prompt pattern (no tool use).
  Tool use requires reading structured tool_use blocks from the response
  and driving a multi-turn conversation loop — incompatible with
  core/llm.py's invoke_llm(system, user) interface.
"""

import os
from dataclasses import dataclass
from typing import AsyncGenerator, Union

import anthropic

from . import skills as _skills

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 4096
_MAX_TOOL_ROUNDS = 5

_SYSTEM_PROMPT = (
    "You are a PM career coach. The user will ask you for help with their PM career. "
    "You have four tools available: interview_prep, gap_analysis, career_positioning, "
    "job_match_score. Pick the right tool(s) for the user's request. You may call "
    "multiple tools in sequence. When you have enough information from tool results, "
    "respond with a final synthesized answer in plain text."
)

TOOLS: list[dict] = [
    {
        "name": "interview_prep",
        "description": (
            "Generate PM interview prep — themes to lean on, STAR-formatted story "
            "guidance, likely questions for the role, delivery tips."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "background": {
                    "type": "string",
                    "description": "User's PM background and experience",
                },
                "target_role": {
                    "type": "string",
                    "description": "The role they're interviewing for",
                },
                "questions": {
                    "type": "string",
                    "description": "Optional specific questions to focus on",
                },
            },
            "required": ["background", "target_role"],
        },
    },
    {
        "name": "gap_analysis",
        "description": (
            "Map the user's background against PM hiring expectations and produce "
            "a 30-90 day development plan with specific deliverables."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "background": {
                    "type": "string",
                    "description": "User's PM background and experience",
                },
                "target_role": {
                    "type": "string",
                    "description": "The target PM role",
                },
                "current_skills": {
                    "type": "string",
                    "description": "Optional current skills assessment",
                },
            },
            "required": ["background", "target_role"],
        },
    },
    {
        "name": "career_positioning",
        "description": (
            "Craft positioning statements, career narrative, company-type variations, "
            "and reusable resume/LinkedIn lines."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "background": {
                    "type": "string",
                    "description": "User's PM background and experience",
                },
                "target_companies": {
                    "type": "string",
                    "description": "Types or names of target companies",
                },
                "narrative": {
                    "type": "string",
                    "description": "Optional existing narrative to refine",
                },
            },
            "required": ["background", "target_companies"],
        },
    },
    {
        "name": "job_match_score",
        "description": (
            "Score a resume against a job description (1-10) with strong matches, "
            "gaps, positioning advice, and concrete resume tweaks."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "resume": {
                    "type": "string",
                    "description": "The user's resume text",
                },
                "job_description": {
                    "type": "string",
                    "description": "The job description text",
                },
            },
            "required": ["resume", "job_description"],
        },
    },
]

_SKILL_DISPATCH = {
    "interview_prep": _skills.interview_prep,
    "gap_analysis": _skills.gap_analysis,
    "career_positioning": _skills.career_positioning,
    "job_match_score": _skills.job_match_score,
}


@dataclass
class ProgressEvent:
    """Yielded when a tool call starts. Maps to a WORKING status update."""
    message: str


@dataclass
class FinalAnswerEvent:
    """Yielded when Claude returns its final synthesized answer."""
    text: str


RouterEvent = Union[ProgressEvent, FinalAnswerEvent]


async def route(
    prompt: str,
    context_history: list[dict],
) -> AsyncGenerator[RouterEvent, None]:
    """
    Drive Claude tool-use loop and yield RouterEvents.

    context_history: prior Anthropic-format message dicts for this context_id,
    enabling multi-turn conversation continuity.
    """
    client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    messages = list(context_history) + [{"role": "user", "content": prompt}]

    for _ in range(_MAX_TOOL_ROUNDS):
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            tools=TOOLS,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
        )

        if response.stop_reason == "tool_use":
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            # Append assistant turn (all content blocks including tool_use).
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool and collect results.
            tool_results = []
            for tu in tool_use_blocks:
                yield ProgressEvent(f"Calling {tu.name}...")
                skill_fn = _SKILL_DISPATCH[tu.name]
                result = await skill_fn(**tu.input)  # type: ignore[arg-type]
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": result,
                    }
                )

            messages.append({"role": "user", "content": tool_results})
            continue

        if response.stop_reason == "end_turn":
            text_parts = [
                b.text for b in response.content if hasattr(b, "text") and b.text
            ]
            yield FinalAnswerEvent(text="\n\n".join(text_parts))
            return

    # Fell through max rounds without end_turn — surface whatever we have.
    yield FinalAnswerEvent(
        text="I reached the maximum number of tool-call rounds without a final answer. "
        "Please try rephrasing your request."
    )
