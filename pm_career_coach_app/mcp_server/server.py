"""
PM Career Coach — MCP server entry point.

Transport : Streamable HTTP (modern MCP default)
MCP endpoint : POST/GET /mcp
Health probe  : GET  /health  (no auth required)

Run locally:
    cd pm_career_coach_app
    MCP_BEARER_TOKEN=mysecret ANTHROPIC_API_KEY=sk-... python -m mcp_server.server

Or via uvicorn directly (same working directory):
    uvicorn mcp_server.server:app --host 0.0.0.0 --port 7860
"""

import asyncio
from functools import partial
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from mcp_server/ using an absolute path anchored to this file.
# Must happen before any import that reads environment variables
# (auth.py calls get_token() → os.environ, core.secrets does the same).
# load_dotenv() never overwrites variables already set in the shell, so
# inline exports in test_local.sh continue to take precedence.
# ---------------------------------------------------------------------------
_ENV_PATH = Path(__file__).parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)

from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

import core.coach as _coach
from .auth import BearerTokenMiddleware, get_token

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Validate auth token at import time so the server refuses to start with an
# unconfigured token rather than accepting requests until the first auth check.
# ---------------------------------------------------------------------------
get_token()

# Log which env vars are present so startup issues are immediately visible.
for _key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "PINECONE_API_KEY"):
    _val = os.environ.get(_key, "")
    logger.info("env: %s = %s", _key, f"SET (len={len(_val)})" if _val else "NOT SET")

# ---------------------------------------------------------------------------
# FastMCP server definition
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="PM Career Coach",
    instructions=(
        "Tools for PM career coaching grounded in patterns from 250+ one-on-one "
        "coaching sessions at UC Berkeley Haas. All tools require scope: coach:access."
    ),
)


@mcp.tool()
async def search_coaching_notes(query: str, top_k: int = 5) -> list[dict]:
    """
    Semantic search over the PII-redacted coaching notes corpus
    (250+ Haas one-on-one PM coaching sessions).

    Returns a list of relevant chunks, each containing the chunk text
    and similarity score. Use this when you want raw coaching context
    rather than a synthesized answer.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(_coach.search_coaching_notes, query, top_k)
    )


@mcp.tool()
async def get_interview_coaching(
    background: str, target_role: str, questions: str
) -> str:
    """
    Get structured PM interview coaching for a candidate.

    Returns markdown with: 2-4 core themes to lean on, structured
    answers for key stories (STAR/problem-solution-impact), 3-5 likely
    PM interview questions for the target role, and delivery
    improvement guidance.

    Grounded in patterns from 250+ PM coaching sessions.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(_coach.interview_prep, background, target_role, questions)
    )


@mcp.tool()
async def analyze_skill_gaps(
    background: str, target_role: str, current_skills: str
) -> str:
    """
    Analyze a candidate's current profile against PM hiring expectations
    for their target role.

    Returns markdown with: profile-vs-expectations mapping, concrete
    skill/experience/signaling gaps, a 30-90 day development plan, and
    guidance on demonstrating progress on resume/LinkedIn/in conversations.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(_coach.gap_analysis, background, target_role, current_skills)
    )


@mcp.tool()
async def craft_career_positioning(
    background: str, target_companies: str, narrative: str
) -> str:
    """
    Craft a PM career positioning statement and narrative tailored to
    target companies.

    Returns markdown with: 1-2 concise positioning statements, a clear
    career narrative connecting past experience to PM, narrative
    variations for different company types (big tech / startup /
    non-tech), and 3-5 reusable lines for resume/LinkedIn headline/
    About section.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        partial(_coach.career_positioning, background, target_companies, narrative),
    )


@mcp.tool()
async def score_job_match(resume: str, job_description: str) -> str:
    """
    Score a resume against a specific job description from a PM
    recruiter's perspective.

    Returns markdown with: a match score 1-10, strong matches in the
    candidate's favor, gaps to address, positioning advice for this
    specific role, and concrete resume tweaks. A score of 7+ means
    strong candidate, 5-6 means viable with positioning work, below 5
    means significant gaps.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(_coach.job_match_score, resume, job_description)
    )


# ---------------------------------------------------------------------------
# ASGI application
#
# Use mcp.streamable_http_app() directly as the root app. This avoids all
# nested-Starlette routing problems:
#
#   Problem with Mount("/", app=mcp_app):
#     The inner mcp_app is a separate Starlette instance with its own
#     redirect_slashes=True default.  That inner app sees path "/mcp" and,
#     depending on version, may 307-redirect to "/mcp/" before FastMCP's
#     handler ever runs.  Nesting also forces manual lifespan wiring.
#
#   Solution:
#     mcp.streamable_http_app() already returns a Starlette app whose
#     lifespan IS the session manager (task-group initialisation is handled
#     automatically when uvicorn starts this app).  We just:
#       1. Disable slash-redirect on its router so POST /mcp is never 307'd.
#       2. Prepend a /health Route so health probes are served before FastMCP
#          routing runs.
#       3. Attach BearerTokenMiddleware (it exempts /health internally).
# ---------------------------------------------------------------------------

async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "server": "pm-career-coach-mcp"})


# Single flat app — no nesting, no separate lifespan wiring needed.
app = mcp.streamable_http_app()

# Prevent Starlette from issuing 307 /mcp → /mcp/ redirects.
app.router.redirect_slashes = False

# /health must be checked before FastMCP's own routes.
app.router.routes.insert(0, Route("/health", health, methods=["GET"]))

# ---------------------------------------------------------------------------
# Middleware stack
#
# Starlette runs middleware in REVERSE add_middleware() order — last added
# runs first on the incoming request.  We need:
#
#   Request → CORS → BearerToken → routing
#
# So CORS is added LAST (runs first) and BearerToken is added FIRST (runs second).
#
# Why CORS must be outermost:
#   Browser preflight (OPTIONS) requests carry no Authorization header.
#   If BearerTokenMiddleware ran first it would 401 the preflight and the
#   browser would block the real POST before it's ever sent.  CORS middleware
#   intercepts OPTIONS and returns the Access-Control-Allow-* headers
#   immediately, so the preflight succeeds and the browser proceeds.
#   BearerTokenMiddleware also exempts OPTIONS explicitly as a belt-and-
#   suspenders guard (see auth.py).
# ---------------------------------------------------------------------------

# 1st added → 2nd in chain: validates Bearer token on every non-OPTIONS,
#   non-/health request.
app.add_middleware(BearerTokenMiddleware)

# 2nd added → 1st in chain: handles CORS preflight and injects
#   Access-Control-Allow-* headers on every response.
#
# allow_origins="*" is fine for local dev / personal HF Space use.
# For a multi-tenant deployment, set MCP_CORS_ALLOWED_ORIGINS in the
# environment (comma-separated list) and replace the value below with:
#   os.getenv("MCP_CORS_ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    # expose_headers lets browser JS read these response headers.
    # mcp-session-id is required for the MCP session handshake;
    # WWW-Authenticate lets clients surface auth errors cleanly.
    expose_headers=["mcp-session-id", "WWW-Authenticate"],
)

# ---------------------------------------------------------------------------
# Local dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
