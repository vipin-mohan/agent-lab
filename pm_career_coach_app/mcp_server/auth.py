"""
Bearer token authentication middleware for the PM Career Coach MCP server.

Security properties:
- Reads MCP_BEARER_TOKEN from the environment at startup; refuses to start
  if the variable is unset.
- Uses hmac.compare_digest() for constant-time comparison to prevent
  timing attacks.
- Returns 401 with a mandatory WWW-Authenticate header on any auth failure
  so MCP clients can discover that authentication is required.
- Skips auth for GET /health so Hugging Face Spaces health probes work
  without a token.
- Never logs token values; debug logging redacts to first 10 chars + length.
"""

import hmac
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_UNSET = object()
_token: object = _UNSET


def _load_token() -> str:
    """Load and validate MCP_BEARER_TOKEN from the environment."""
    raw = os.environ.get("MCP_BEARER_TOKEN", "").strip()
    if not raw:
        raise RuntimeError(
            "MCP_BEARER_TOKEN environment variable is not set or is empty. "
            "The MCP server refuses to start without a bearer token configured. "
            "Set MCP_BEARER_TOKEN to a long random secret before starting the server."
        )
    return raw


def get_token() -> str:
    """Return the cached bearer token, loading it on first call."""
    global _token
    if _token is _UNSET:
        _token = _load_token()
    return _token  # type: ignore[return-value]


_UNAUTHORIZED = JSONResponse(
    status_code=401,
    content={
        "error": "invalid_token",
        "error_description": "Missing or invalid bearer token",
    },
    headers={"WWW-Authenticate": 'Bearer realm="mcp"'},
)


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces bearer token auth on every request."""

    async def dispatch(self, request: Request, call_next):
        # CORS preflight — let CORSMiddleware handle it; don't 401 it.
        if request.method == "OPTIONS":
            return await call_next(request)

        # Health probe endpoint is exempt from auth.
        if request.url.path == "/health":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return _UNAUTHORIZED

        provided = auth_header[len("Bearer "):]
        expected = get_token()

        if not hmac.compare_digest(
            provided.encode("utf-8"), expected.encode("utf-8")
        ):
            return _UNAUTHORIZED

        return await call_next(request)
