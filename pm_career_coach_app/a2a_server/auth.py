"""
Bearer token authentication middleware for the PM Career Coach A2A server.

Security properties:
- Token is injected at construction time from config.settings (validated at
  startup — server refuses to start if A2A_BEARER_TOKEN is unset).
- Uses hmac.compare_digest() for constant-time comparison.
- Returns 401 with WWW-Authenticate header on auth failure.
- Exempts /.well-known/agent-card.json — required by A2A spec for
  unauthenticated agent discovery.
- Exempts OPTIONS preflight so CORS middleware can respond before auth runs.
"""

import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_AGENT_CARD_PATH = "/.well-known/agent-card.json"

_UNAUTHORIZED = JSONResponse(
    status_code=401,
    content={
        "error": "invalid_token",
        "error_description": "Missing or invalid bearer token",
    },
    headers={"WWW-Authenticate": 'Bearer realm="a2a"'},
)


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces bearer token auth on every request."""

    def __init__(self, app, token: str) -> None:
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next):
        # CORS preflight — let CORSMiddleware handle it; don't 401 it.
        if request.method == "OPTIONS":
            return await call_next(request)

        # Agent Card must be publicly accessible for A2A discovery (spec requirement).
        if request.url.path == _AGENT_CARD_PATH:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _UNAUTHORIZED

        provided = auth_header[len("Bearer "):]
        if not hmac.compare_digest(
            provided.encode("utf-8"), self._token.encode("utf-8")
        ):
            return _UNAUTHORIZED

        return await call_next(request)
