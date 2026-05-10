"""
Config for the PM Career Coach A2A server.

Reads from environment / .env file (pm_career_coach_app/a2a_server/.env).
load_dotenv() is called here so that any module importing config gets
env vars populated before first use. Never overwrites shell-level exports.

Refuses to construct Settings if A2A_BEARER_TOKEN is unset — fail-fast
rather than serving insecurely.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


@dataclass(frozen=True)
class Settings:
    bearer_token: str
    public_url: str
    host: str
    port: int
    log_level: str


def _load() -> Settings:
    token = os.environ.get("A2A_BEARER_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "A2A_BEARER_TOKEN environment variable is not set or is empty. "
            "The A2A server refuses to start without a bearer token configured. "
            "Set A2A_BEARER_TOKEN to a long random secret before starting the server. "
            "Example: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    return Settings(
        bearer_token=token,
        public_url=os.environ.get("A2A_PUBLIC_URL", "http://localhost:8000"),
        host=os.environ.get("A2A_HOST", "0.0.0.0"),
        port=int(os.environ.get("A2A_PORT", "8000")),
        log_level=os.environ.get("A2A_LOG_LEVEL", "INFO"),
    )


settings = _load()
