"""
PM Career Coach — Interactive A2A CLI Client.

Streams Task events from the A2A server and renders them with rich.
Multi-turn conversations are kept alive via context_id.

Run from pm_career_coach_app/ directory (server must be running first):
    python -m a2a_server.cli_client

The server is NOT started by the CLI — two-process model, same as a real
A2A deployment.
"""

import asyncio
import sys
import time
from typing import Optional

import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Prompt

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import (
    display_agent_card,
    get_artifact_text,
    get_message_text,
    new_text_message,
)
from a2a.types.a2a_pb2 import Role, SendMessageRequest, TaskState

from .config import settings  # reuses the server's .env loader

console = Console()

_HELP_TEXT = (
    "[bold]/new[/bold]      Start a new conversation (reset context_id)\n"
    "[bold]/card[/bold]     Re-fetch and show the full agent card\n"
    "[bold]/skills[/bold]   List available skills (compact)\n"
    "[bold]/help[/bold]     Show this help\n"
    "[bold]/exit[/bold]     Exit the CLI  (also /q, /quit, or Ctrl+C)"
)


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

def _ctx_label(context_id: Optional[str]) -> str:
    if not context_id:
        return "(new context)"
    return f"(ctx: {context_id[:8]}…)"


def _prompt_str(context_id: Optional[str]) -> str:
    return f"[bold cyan]you[/bold cyan] [dim]{_ctx_label(context_id)}[/dim] ❯"


# ---------------------------------------------------------------------------
# Streaming turn renderer
# ---------------------------------------------------------------------------

async def _run_turn(
    client,
    user_input: str,
    current_context_id: Optional[str],
) -> Optional[str]:
    """
    Send one streaming message and render the 4-event A2A sequence.

    Event mapping (canonical helloworld pattern):
      task chunk            → "Task submitted" panel (cyan)
      status WORKING        → yellow "→ {progress text}" line
      artifact_update       → green Panel with Markdown content
      status COMPLETED      → green "✓ Completed in X.Xs"
      status FAILED         → red "✗ Failed: {msg}"
      status CANCELLED      → red "✗ Cancelled"
      message chunk         → green Panel with Markdown (rare; direct message response)
      anything else         → dim debug repr

    Returns the captured context_id (or current_context_id on error).

    Dispatch note: uses HasField() not WhichOneof('payload') — the SDK's own
    get_stream_response_text uses HasField, confirming that WhichOneof raises
    ValueError for StreamResponse.
    """
    message = new_text_message(
        user_input,
        role=Role.ROLE_USER,
        context_id=current_context_id,  # None on first turn; SDK generates one
    )
    request = SendMessageRequest(message=message)

    captured_context_id: Optional[str] = current_context_id
    start_time: Optional[float] = None

    try:
        async for chunk in client.send_message(request):
            try:
                if chunk.HasField("task"):
                    task = chunk.task
                    if not captured_context_id:
                        captured_context_id = task.context_id
                    start_time = time.monotonic()
                    console.print(
                        Panel(
                            f"[dim]task_id  : {task.id}[/dim]\n"
                            f"[dim]context  : {task.context_id}[/dim]",
                            title="[cyan]Task submitted[/cyan]",
                            border_style="cyan",
                        )
                    )

                elif chunk.HasField("status_update"):
                    su = chunk.status_update
                    state = su.status.state

                    if state == TaskState.TASK_STATE_WORKING:
                        if su.status.HasField("message"):
                            progress = escape(get_message_text(su.status.message))
                        else:
                            progress = "Working…"
                        console.print(f"[yellow]→[/yellow] {progress}")

                    elif state == TaskState.TASK_STATE_COMPLETED:
                        elapsed = (
                            time.monotonic() - start_time if start_time is not None else 0.0
                        )
                        console.print(f"[green]✓ Completed in {elapsed:.1f}s[/green]")

                    elif state == TaskState.TASK_STATE_FAILED:
                        err = ""
                        if su.status.HasField("message"):
                            err = escape(get_message_text(su.status.message))
                        console.print(f"[red]✗ Failed: {err}[/red]")

                    elif state == TaskState.TASK_STATE_CANCELLED:
                        console.print("[red]✗ Cancelled[/red]")

                    else:
                        console.print(f"[dim]status state: {state}[/dim]")

                elif chunk.HasField("artifact_update"):
                    artifact = chunk.artifact_update.artifact
                    title = escape(artifact.name) if artifact.name else "Result"
                    text = get_artifact_text(artifact)
                    console.print(
                        Panel(
                            Markdown(text),
                            title=title,
                            border_style="green",
                        )
                    )

                elif chunk.HasField("message"):
                    # Direct message response (no task lifecycle)
                    msg_text = get_message_text(chunk.message)
                    if msg_text:
                        console.print(
                            Panel(Markdown(msg_text), title="Response", border_style="green")
                        )
                    else:
                        console.print(f"[dim]event: {repr(chunk)}[/dim]")

                else:
                    console.print(f"[dim]event: {repr(chunk)}[/dim]")

            except Exception as render_err:
                console.print(
                    f"[red]Internal error rendering event: {escape(str(render_err))}[/red]"
                )

    except httpx.TimeoutException:
        console.print(
            "[red]Request timed out after 300s — the server may still be working. "
            "Try again or use /new to reset.[/red]"
        )

    except httpx.HTTPStatusError as http_err:
        if http_err.response.status_code == 401:
            console.print(
                "[red]Authentication failed — check A2A_BEARER_TOKEN in .env[/red]"
            )
        else:
            console.print(
                f"[red]HTTP error {http_err.response.status_code}: "
                f"{escape(str(http_err))}[/red]"
            )

    except (httpx.ConnectError, httpx.RemoteProtocolError) as conn_err:
        console.print(
            f"[red]Connection error: {escape(str(conn_err))}. "
            "Is the server still running?[/red]"
        )

    except Exception as exc:
        console.print(f"[red]Unexpected error: {escape(str(exc))}[/red]")

    return captured_context_id


# ---------------------------------------------------------------------------
# Main REPL
# ---------------------------------------------------------------------------

async def main() -> int:
    base_url = settings.public_url.rstrip("/")
    token = settings.bearer_token

    # Welcome banner
    console.print(
        Panel(
            f"Connected to [bold]{base_url}[/bold]\n"
            "Type [bold]/help[/bold] for commands, [bold]/exit[/bold] to quit",
            title="[bold]PM Career Coach — A2A CLI Client[/bold]",
            border_style="cyan",
        )
    )

    auth_headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(headers=auth_headers, timeout=300.0) as httpx_client:

        # --- Discovery ---------------------------------------------------
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        try:
            public_card = await resolver.get_agent_card()
        except httpx.ConnectError:
            console.print(
                f"[red]Cannot reach server at {base_url} — is it running?[/red]"
            )
            return 1
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                console.print(
                    "[red]Authentication failed — check A2A_BEARER_TOKEN in .env[/red]"
                )
            else:
                console.print(
                    f"[red]Server error during discovery: {e.response.status_code}[/red]"
                )
            return 1
        except Exception as e:
            console.print(f"[red]Discovery failed: {escape(str(e))}[/red]")
            return 1

        console.print()
        display_agent_card(public_card)
        console.print()

        # --- Build streaming client (reused across all turns) ------------
        config = ClientConfig(streaming=True, httpx_client=httpx_client)
        client = await create_client(agent=public_card, client_config=config)

        # --- Slash command helpers (closures; share current_context_id) --
        def _skills_text() -> str:
            lines: list[str] = []
            for skill in public_card.skills:
                lines.append(
                    f"[bold]{escape(skill.name)}[/bold] [dim]({skill.id})[/dim]"
                )
                lines.append(f"  {escape(skill.description)}")
                lines.append("")
            return "\n".join(lines).rstrip()

        # --- REPL --------------------------------------------------------
        current_context_id: Optional[str] = None

        while True:
            try:
                user_input = Prompt.ask(_prompt_str(current_context_id))
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Goodbye![/dim]")
                return 0

            stripped = user_input.strip()
            if not stripped:
                continue  # empty input — redraw prompt, no network call

            cmd = stripped.lower()

            # Slash command dispatch
            if cmd in ("/exit", "/q", "/quit"):
                console.print("[dim]Goodbye![/dim]")
                return 0

            if cmd == "/new":
                current_context_id = None
                console.print("[cyan]Started new conversation context[/cyan]")
                continue

            if cmd == "/card":
                try:
                    fresh_card = await resolver.get_agent_card()
                    display_agent_card(fresh_card)
                except Exception as e:
                    console.print(
                        f"[red]Failed to fetch agent card: {escape(str(e))}[/red]"
                    )
                continue

            if cmd == "/skills":
                console.print(_skills_text())
                continue

            if cmd in ("/help", "/?"):
                console.print(
                    Panel(_HELP_TEXT, title="Commands", border_style="dim")
                )
                continue

            if stripped.startswith("/"):
                console.print(
                    f"[red]Unknown command: {escape(stripped)}. "
                    "Type /help for help.[/red]"
                )
                continue

            # Regular message — stream to agent
            new_ctx = await _run_turn(client, stripped, current_context_id)
            if new_ctx and not current_context_id:
                current_context_id = new_ctx

    return 0  # unreachable; loop exits via return


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(0)