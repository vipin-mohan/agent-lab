# PM Career Coach — A2A Server

An [A2A protocol](https://github.com/a2aproject/A2A) server that exposes the PM Career Coach as a single agent with four skills: interview prep, skill gap analysis, career positioning, and job match scoring. Backed by 250+ real coaching sessions with MBA students at UC Berkeley Haas.

This README covers the **server** (Spec 1) and the **interactive CLI client** (Spec 2).

---

## Requirements

- **Python 3.11** — required. The `a2a-sdk` dependency (`pydantic-core`) has no prebuilt Windows wheels for Python 3.14 and falls back to Rust compilation which requires the MSVC linker. If `py -3.11` fails with "No suitable Python runtime found," install Python 3.11 from [python.org](https://www.python.org/downloads/) or run `winget install Python.Python.3.11`.
- **Do NOT use uv-managed Pythons** on Windows machines with Application Control / WDAC enabled — these cause DLL load failures on `_overlapped`.
- At least one LLM API key (`ANTHROPIC_API_KEY` strongly recommended — also used for the tool-use routing layer)
- A Pinecone API key (for grounded RAG responses from `core/`)

---

## Setup (PowerShell)

```powershell
# 1. Navigate to the a2a_server directory from the repo root
cd pm_career_coach_app\a2a_server

# 2. Create a venv with Python 3.11 specifically
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Verify the right Python version
python --version    # MUST print Python 3.11.x — NOT 3.10 or 3.14

# 4. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 5. Set up environment variables
copy .env.example .env
# Edit .env to fill in A2A_BEARER_TOKEN, ANTHROPIC_API_KEY, PINECONE_API_KEY
```

---

## Running the Server

Run from the **`pm_career_coach_app/` directory** (same working directory as the MCP server — required for `core/` imports to resolve):

```powershell
# From repo root
cd pm_career_coach_app

# Activate the venv (if not already active)
..\pm_career_coach_app\a2a_server\.venv\Scripts\Activate.ps1

# Start the server
python -m a2a_server.server
```

The server starts on `http://localhost:8000` by default. You should see:

```
INFO: Started server process
INFO: Waiting for application startup.
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:8000
```

To change the port or host, set `A2A_PORT` / `A2A_HOST` in `.env` or export them before running.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `A2A_BEARER_TOKEN` | **Yes** | — | Static bearer token for auth. Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ANTHROPIC_API_KEY` | **Yes** | — | Used for tool-use routing AND as primary LLM for skill execution |
| `PINECONE_API_KEY` | **Yes** | — | RAG pipeline for grounded coaching responses |
| `A2A_PUBLIC_URL` | No | `http://localhost:8000` | URL advertised in the Agent Card |
| `A2A_HOST` | No | `0.0.0.0` | Bind address |
| `A2A_PORT` | No | `8000` | Port |
| `A2A_LOG_LEVEL` | No | `INFO` | Logging level |
| `OPENAI_API_KEY` | No | — | Fallback LLM provider |
| `GEMINI_API_KEY` | No | — | Fallback LLM provider |
| `PINECONE_INDEX_NAME` | No | `coaching-notes` | Pinecone index name |

---

## Testing with PowerShell

### 1. Agent Card discovery (no auth required)

```powershell
Invoke-RestMethod http://localhost:8000/.well-known/agent-card.json | ConvertTo-Json -Depth 10
```

Expected: JSON with `name`, `description`, `version`, `capabilities`, `skills` (4 entries), `supportedInterfaces`.

### 2. Auth enforcement check

```powershell
# Should return 401
Invoke-RestMethod -Uri http://localhost:8000/ -Method Post `
  -ContentType "application/json" `
  -Body '{"jsonrpc":"2.0","method":"message/send","id":"1","params":{}}'
```

### 3. Single-skill: job match score

Replace `YOUR_TOKEN` with the value from your `.env` file.

```powershell
$headers = @{ Authorization = "Bearer YOUR_TOKEN"; "Content-Type" = "application/json" }

$body = @{
    jsonrpc = "2.0"
    id      = "req-1"
    method  = "message/send"
    params  = @{
        message = @{
            role    = "ROLE_USER"
            parts   = @(@{ text = "Score this resume against this JD: [paste resume here] / [paste job description here]" })
            messageId = "msg-1"
        }
    }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri http://localhost:8000/ -Method Post -Headers $headers -Body $body
```

Expected: A Task object with `status.state = TASK_STATE_COMPLETED` and an `artifacts` array containing the coaching analysis.

### 4. Multi-skill: gap analysis AND job match

```powershell
$body = @{
    jsonrpc = "2.0"
    id      = "req-2"
    method  = "message/send"
    params  = @{
        message = @{
            role    = "ROLE_USER"
            parts   = @(@{ text = "Score this resume against this JD AND tell me the skill gaps to close: [resume] / [jd]" })
            messageId = "msg-2"
        }
    }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri http://localhost:8000/ -Method Post -Headers $headers -Body $body
```

Expected: The router calls both `job_match_score` and `gap_analysis`, and the final artifact synthesizes both results.

### 5. SSE streaming (message/stream)

```powershell
$body = @{
    jsonrpc = "2.0"
    id      = "req-3"
    method  = "message/stream"
    params  = @{
        message = @{
            role    = "ROLE_USER"
            parts   = @(@{ text = "Help me prep for a Senior PM interview at Adobe." })
            messageId = "msg-3"
        }
    }
} | ConvertTo-Json -Depth 10

Invoke-WebRequest -Uri http://localhost:8000/ -Method Post -Headers $headers -Body $body
```

Expected: SSE event stream with 4+ events: `Task` (SUBMITTED), `TaskStatusUpdateEvent` (WORKING), `TaskArtifactUpdateEvent` (result), `TaskStatusUpdateEvent` (COMPLETED).

---

## Architecture

```
pm_career_coach_app/
├── core/               # shared coaching engine (unchanged)
├── mcp_server/         # MCP server (unchanged, peer not dependency)
└── a2a_server/         # Spec 1 + 2
    ├── server.py       # entry point: Starlette app + middleware
    ├── agent_card.py   # AgentCard with 4 skills (SDK v1.0 pattern)
    ├── agent_executor.py  # AgentExecutor: drives router loop, emits A2A events
    ├── router.py       # Claude tool-use loop: prompt → skill calls → answer
    ├── skills.py       # thin asyncio.to_thread wrappers over core/ functions
    ├── auth.py         # BearerAuthMiddleware (exempts /.well-known/agent-card.json)
    ├── config.py       # env var loading, fails fast if A2A_BEARER_TOKEN unset
    ├── cli_client.py   # interactive CLI client (Spec 2)
    └── test_client.py  # smoke test (non-interactive, validates server health)
```

The A2A server calls `core/` directly (same as the MCP server). They are peers — neither depends on the other.

---

## Interactive CLI client

A rich terminal REPL that streams Task events from the server in real time. Demonstrates the full A2A client experience: discovery, streaming events, multi-turn context continuity.

### Run (server must be running first in another terminal)

```powershell
# From repo root
cd pm_career_coach_app

# Activate the venv (same one the server uses)
.\a2a_server\.venv\Scripts\Activate.ps1

# Install dependencies (adds rich if not already present)
pip install -r a2a_server\requirements.txt

# Start the CLI — reads A2A_BEARER_TOKEN and A2A_PUBLIC_URL from a2a_server/.env
python -m a2a_server.cli_client
```

The CLI prints a welcome banner, shows the Agent Card, then opens an interactive prompt. Start the server in a separate PowerShell window first.

### Slash commands

| Command | Behavior |
|---|---|
| `/new` | Reset `context_id` — start a fresh conversation |
| `/card` | Re-fetch and render the full Agent Card |
| `/skills` | Compact list of skill IDs and descriptions |
| `/help` | Show command list |
| `/exit` (or `/q`, `/quit`, Ctrl+C) | Exit cleanly |

### Multi-turn conversations

The CLI captures `context_id` from the first Task response and attaches it to every subsequent message. The server uses it to look up prior conversation history so Claude has full context. The prompt shows the active context: `(ctx: abc12345…)`. Type `/new` to reset.

### Streaming event display

Each message send produces a 4-event sequence rendered live:

1. **Cyan panel** — "Task submitted" with `task_id` and `context_id`
2. **Yellow `→` lines** — one per tool call (e.g. `→ Calling job_match_score…`)
3. **Green panel** — the coaching response rendered as Markdown
4. **Green `✓`** — "Completed in X.Xs"

Multi-skill prompts produce multiple yellow lines before the final green panel.

---

## Notes

- **Task storage**: `InMemoryTaskStore` — tasks are lost on server restart.
- **Multi-turn history**: stored in-memory per `context_id`; also lost on server restart. Use `/new` in the CLI to start fresh if the server was restarted.
- **Timeouts**: CLI sets a 300s timeout. Multi-skill prompts (calling 2+ core/ functions) can take 2–5 minutes — this is expected.
- **Deployment**: Not deployed in this spec. For Hugging Face Spaces, set `A2A_HOST=0.0.0.0`, `A2A_PORT=7860`, `A2A_PUBLIC_URL=https://your-space.hf.space`.
