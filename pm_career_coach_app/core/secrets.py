"""
Environment-variable-only secret loader.

Reads exclusively from os.environ (and .env files loaded via python-dotenv).
The Streamlit app has its own thin wrapper that first checks st.secrets and
then falls back here by populating os.environ before calling core functions.
"""

import os


def get_secret(name: str) -> str | None:
    """Return the named secret from environment variables, or None if absent."""
    return os.getenv(name)
