"""
PM Career Coach A2A server entry point.

Wires together:
  - AgentCard (served at /.well-known/agent-card.json, no auth)
  - DefaultRequestHandler + InMemoryTaskStore
  - BearerAuthMiddleware (all routes except agent-card)
  - CORSMiddleware (outermost, handles preflight before auth)

Run from pm_career_coach_app/ directory:
    python -m a2a_server.server

Middleware order note (matches MCP server pattern):
  Starlette runs middleware in REVERSE add_middleware() order.
  add_middleware(BearerAuthMiddleware)  → added 1st → runs 2nd
  add_middleware(CORSMiddleware)        → added 2nd → runs 1st (outermost)
  This ensures CORS preflight (OPTIONS, no auth header) is handled before
  BearerAuthMiddleware sees the request.
"""

import logging

import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware

from .agent_card import build_agent_card
from .agent_executor import CareerCoachAgentExecutor
from .auth import BearerAuthMiddleware
from .config import settings  # also triggers load_dotenv for a2a_server/.env

# config.settings is validated at import time; if A2A_BEARER_TOKEN is missing
# the import itself raises RuntimeError and the server never starts.

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_log_env_vars = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "PINECONE_API_KEY",
)
for _key in _log_env_vars:
    import os as _os
    _val = _os.environ.get(_key, "")
    logger.info("env: %s = %s", _key, f"SET (len={len(_val)})" if _val else "NOT SET")


def build_app() -> Starlette:
    agent_card = build_agent_card(public_url=settings.public_url)

    handler = DefaultRequestHandler(
        agent_executor=CareerCoachAgentExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    routes = []
    routes.extend(create_agent_card_routes(agent_card))
    routes.extend(create_jsonrpc_routes(handler, "/"))

    app = Starlette(routes=routes)

    # 1st added → 2nd in chain: validates Bearer token on non-exempt requests.
    app.add_middleware(BearerAuthMiddleware, token=settings.bearer_token)

    # 2nd added → 1st in chain (outermost): handles CORS preflight before auth.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["WWW-Authenticate"],
    )

    return app


def main() -> None:
    app = build_app()
    logger.info(
        "Starting PM Career Coach A2A server on %s:%d", settings.host, settings.port
    )
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
