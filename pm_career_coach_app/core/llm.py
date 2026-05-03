"""
Multi-provider LLM router.

Priority order:
  1. ANTHROPIC_API_KEY  → claude-sonnet-4-6
  2. OPENAI_API_KEY     → gpt-4.1-mini
  3. GEMINI_API_KEY     → gemini-2.0-flash

Raises LLMError (a plain Python exception) instead of calling st.error.
Callers — including the Streamlit app — are responsible for displaying the
error in their own context.
"""

from .secrets import get_secret

MAX_OUTPUT_TOKENS = 4096


class LLMError(Exception):
    """Raised when the LLM call fails for any reason."""


def invoke_llm(system_prompt: str, user_content: str) -> str:
    """
    Route the request to the first available LLM provider and return the
    text response.

    Raises:
        LLMError: if no API key is configured or the provider call fails.
    """
    anthropic_key = get_secret("ANTHROPIC_API_KEY")
    openai_key = get_secret("OPENAI_API_KEY")
    gemini_key = get_secret("GEMINI_API_KEY")

    if anthropic_key:
        provider = "anthropic"
    elif openai_key:
        provider = "openai"
    elif gemini_key:
        provider = "gemini"
    else:
        raise LLMError(
            "No model API key found. Please set at least one of "
            "ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY."
        )

    try:
        if provider == "anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=anthropic_key)
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=MAX_OUTPUT_TOKENS,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            return "".join(
                block.text
                for block in response.content
                if getattr(block, "type", None) == "text"
            ).strip()

        if provider == "openai":
            try:
                from openai import OpenAI  # type: ignore[import]
            except ImportError:
                raise LLMError(
                    "OpenAI support requires the 'openai' package. "
                    "Install it with `pip install openai` or unset OPENAI_API_KEY."
                )
            client = OpenAI(api_key=openai_key)
            response = client.responses.create(
                model="gpt-4.1-mini",
                instructions=system_prompt,
                input=user_content,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                temperature=0.7,
            )
            return (response.output_text or "").strip()

        if provider == "gemini":
            try:
                from google import genai  # type: ignore[import]
            except ImportError:
                raise LLMError(
                    "Gemini support requires the 'google-genai' package. "
                    "Install it with `pip install google-genai` or unset GEMINI_API_KEY."
                )
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"{system_prompt}\n\n{user_content}",
                generation_config={"max_output_tokens": MAX_OUTPUT_TOKENS},
            )
            return (getattr(response, "text", "") or "").strip()

    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(f"Error calling language model ({provider}): {exc}") from exc

    return ""
