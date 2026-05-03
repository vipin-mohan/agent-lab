# PM Career Coach — MCP Server

An MCP (Model Context Protocol) server that exposes the [PM Career Coach](../README.md) as five callable tools. Connect it to Claude Desktop, Cursor, MCP Inspector, or any Python MCP client to get structured PM career coaching directly inside your AI workflow — grounded in patterns from 250+ one-on-one coaching sessions at UC Berkeley Haas.

---

## What It Does

The PM Career Coach has been coaching MBA students into APM and PM roles at top tech companies for nearly 5 years. This server wraps its four core coaching workflows — plus a direct search over the coaching notes corpus — as MCP tools:

| Tool | What it does |
|---|---|
| `search_coaching_notes` | Raw semantic search over the coaching notes corpus — returns chunks with similarity scores |
| `get_interview_coaching` | Structured interview prep: themes, STAR stories, likely questions, delivery tips |
| `analyze_skill_gaps` | Gap analysis: profile vs. PM hiring expectations + 30–90 day development plan |
| `craft_career_positioning` | Positioning statement, career narrative, company-type variations, resume/LinkedIn lines |
| `score_job_match` | Resume-vs-JD scoring (1–10), strong matches, gaps, positioning advice, resume tweaks |

All responses are grounded in the RAG pipeline — the most relevant coaching patterns from real sessions are injected into every LLM prompt.

---

## Architecture

```
MCP Client
(Claude Desktop / Cursor / Inspector / Python)
         │
         │  POST /mcp  Authorization: Bearer <token>
         ▼
┌─────────────────────────────────────┐
│  Starlette app (port 7860)          │
│                                     │
│  GET /health  ←── no auth           │
│                                     │
│  BearerTokenMiddleware              │
│    └── hmac.compare_digest()        │
│         │                           │
│         ▼                           │
│  FastMCP  (Streamable HTTP)         │
│    ├── search_coaching_notes        │
│    ├── get_interview_coaching       │
│    ├── analyze_skill_gaps           │
│    ├── craft_career_positioning     │
│    └── score_job_match              │
└──────────────┬──────────────────────┘
               │
               ▼
        core/  (Streamlit-free)
         ├── coach.py      ← orchestration
         ├── prompts.py    ← prompt builders
         ├── llm.py        ← multi-provider LLM router
         └── retrieval.py  ← embedding model + Pinecone
               │
       ┌───────┴────────┐
       ▼                ▼
   Pinecone          LLM providers
 (coaching-notes)   Anthropic / OpenAI / Gemini
```

---

## Tools

### `search_coaching_notes(query, top_k=5)`
Semantic search over the PII-redacted coaching notes corpus (250+ Haas one-on-one PM coaching sessions). Returns a list of relevant chunks, each containing the chunk text and similarity score. Use this when you want raw coaching context rather than a synthesized answer.

### `get_interview_coaching(background, target_role, questions)`
Get structured PM interview coaching for a candidate. Returns markdown with: 2–4 core themes to lean on, structured answers for key stories (STAR/problem-solution-impact), 3–5 likely PM interview questions for the target role, and delivery improvement guidance.

### `analyze_skill_gaps(background, target_role, current_skills)`
Analyze a candidate's current profile against PM hiring expectations for their target role. Returns markdown with: profile-vs-expectations mapping, concrete skill/experience/signaling gaps, a 30–90 day development plan, and guidance on demonstrating progress on resume/LinkedIn/in conversations.

### `craft_career_positioning(background, target_companies, narrative)`
Craft a PM career positioning statement and narrative tailored to target companies. Returns markdown with: 1–2 concise positioning statements, a clear career narrative connecting past experience to PM, narrative variations for different company types (big tech / startup / non-tech), and 3–5 reusable lines for resume/LinkedIn headline/About section.

### `score_job_match(resume, job_description)`
Score a resume against a specific job description from a PM recruiter's perspective. Returns markdown with: a match score 1–10, strong matches in the candidate's favor, gaps to address, positioning advice for this specific role, and concrete resume tweaks. A score of 7+ means strong candidate, 5–6 means viable with positioning work, below 5 means significant gaps.

---

## Scope Design Note

All five tools share a single scope: **`coach:access`**.

This is a deliberate choice for the current milestone. All tools are read-only and informational — they query a shared knowledge base and call an LLM; there is no per-user state, no write path, and no sensitive data differentiation between tools. A flat single-scope model is simpler, easier to reason about, and appropriate for personal/demo use.

A tiered scope model (e.g., `coach:read` for search, `coach:coach` for LLM-backed tools, `coach:write` for saving sessions) would make sense when stateful tools are added — persisting user stories, tracking practice sessions, or building a long-running profile. That is planned for a future spec alongside the OAuth 2.1 / PKCE migration. When that work lands, scopes will be split at that point rather than prematurely over-engineering the current flat model.

---

## Local Development

### 1. Clone the repo and install dependencies

```bash
git clone https://github.com/vipin-mohan/agent-lab.git
cd agent-lab/pm_career_coach_app

pip install -r mcp_server/requirements.txt
```

### 2. Configure environment variables

```bash
cp mcp_server/.env.example .env
# Edit .env and fill in your secrets
```

Required:
- `MCP_BEARER_TOKEN` — a long random secret (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `PINECONE_API_KEY` — for RAG-grounded responses
- At least one of: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`

### 3. Start the server

```bash
# From pm_career_coach_app/
python -m mcp_server.server
```

Server starts at `http://localhost:7860`. MCP endpoint: `http://localhost:7860/mcp`.

### 4. Run the test suite

```bash
bash mcp_server/test_local.sh
```

---

## Hugging Face Spaces Deployment

### 1. Create a new Space

Go to [huggingface.co/new-space](https://huggingface.co/new-space), choose **Docker** SDK.

### 2. Upload files

Push the `pm_career_coach_app/` directory contents to the Space. The Dockerfile expects this layout at the Docker build root:

```
core/
mcp_server/
    Dockerfile        ← must be at Space root, or set as the Docker file path
    requirements.txt
    ...
```

Copy `mcp_server/Dockerfile` to the Space root, then push `core/` and `mcp_server/`.

### 3. Set Space secrets

In the Space settings → **Secrets**, add:

```
MCP_BEARER_TOKEN   = your-long-random-secret
ANTHROPIC_API_KEY  = sk-ant-...
PINECONE_API_KEY   = pcsk-...
```

### 4. Build and deploy

HF Spaces auto-builds on push. The server listens on port 7860 (required by HF Spaces). Your public URL will be:

```
https://<your-username>-pm-career-coach-mcp.hf.space/mcp
```

---

## Connecting Clients

### MCP Inspector

1. Open [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
2. Add server URL: `http://localhost:7860/mcp`
3. In **Headers**, add: `Authorization: Bearer your-token-here`
4. Click **Connect** — you should see all 5 tools listed

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "pm-career-coach": {
      "url": "http://localhost:7860/mcp",
      "headers": {
        "Authorization": "Bearer your-token-here"
      }
    }
  }
}
```

Restart Claude Desktop. The five PM coaching tools will appear in the tool list.

For a deployed HF Space, replace `http://localhost:7860/mcp` with your Space URL.

### Python MCP client

```python
import asyncio
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

async def main():
    server_url = "http://localhost:7860/mcp"
    token = "your-token-here"

    async with streamablehttp_client(
        server_url,
        headers={"Authorization": f"Bearer {token}"},
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            for tool in tools.tools:
                print(tool.name, "—", tool.description[:60])

            # Call a tool
            result = await session.call_tool(
                "search_coaching_notes",
                {"query": "PM behavioral interview", "top_k": 3},
            )
            print(result.content)

asyncio.run(main())
```

---

## Security Notes

The current authentication model — a single static bearer token passed in an HTTP header — is suitable for **personal or demo use** where you control all clients and the server is not publicly exposed without additional network-level controls (e.g., Cloudflare Access, VPN).

**It is not suitable for multi-tenant production use** because:
- A single compromised token grants full access
- There is no per-user identity, audit trail, or token rotation
- The token is long-lived with no expiry

The planned follow-up spec (Spec 2) will migrate to **OAuth 2.1 with PKCE**, per-user token issuance, and JWT validation — at which point scopes will also be split as described in the Scope Design Note above.

Until then: treat `MCP_BEARER_TOKEN` like a root password. Use a long random value, rotate it if you suspect exposure, and store it only in environment variables / secrets managers — never in code or committed `.env` files.

---

## About the Author

I'm a product leader with 8+ years at AWS, where I currently lead agentic AI products for Amazon Quick. I've shipped 15+ AI agent integrations using MCP and A2A protocols, and I coach MBA students at UC Berkeley Haas on breaking into product management.

[LinkedIn](https://www.linkedin.com/in/vipinmohan) · [GitHub](https://github.com/vipin-mohan)
