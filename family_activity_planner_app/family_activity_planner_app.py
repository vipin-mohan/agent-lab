import os
from textwrap import dedent

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv


load_dotenv()

# Upper bound on how long model responses can be.
MAX_OUTPUT_TOKENS = 4096


def _get_secret(name: str) -> str | None:
    """Fetch a secret from Streamlit Cloud or environment variables."""
    # Streamlit Cloud: app-wide secrets configured in .streamlit/secrets.toml
    try:
        value = st.secrets[name]  # type: ignore[index]
        if value:
            return str(value)
    except Exception:
        pass

    # Local dev: .env file or shell environment
    return os.getenv(name)


def call_family_activity_planner(system_prompt: str, user_content: str) -> str:
    """
    Route the request to Anthropic, OpenAI, or Gemini depending on which API key is available.

    Priority:
      1. ANTHROPIC_API_KEY
      2. OPENAI_API_KEY
      3. GEMINI_API_KEY
    """
    anthropic_key = _get_secret("ANTHROPIC_API_KEY")
    openai_key = _get_secret("OPENAI_API_KEY")
    gemini_key = _get_secret("GEMINI_API_KEY")

    provider: str | None
    if anthropic_key:
        provider = "anthropic"
    elif openai_key:
        provider = "openai"
    elif gemini_key:
        provider = "gemini"
    else:
        st.error(
            "No model API key found. Please set at least one of "
            "ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY in your "
            "Streamlit secrets (secrets.toml) or in a local .env file."
        )
        return ""

    try:
        if provider == "anthropic":
            client = Anthropic(api_key=anthropic_key)  # type: ignore[arg-type]
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=MAX_OUTPUT_TOKENS,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            text_chunks: list[str] = []
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    text_chunks.append(block.text)
            return "".join(text_chunks).strip()

        if provider == "openai":
            try:
                # Lazy import so the app still runs if openai is not installed
                from openai import OpenAI  # type: ignore[import]
            except ImportError:
                st.error(
                    "OpenAI support requires the 'openai' package. "
                    "Install it with `pip install openai` or unset OPENAI_API_KEY."
                )
                return ""

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
                # Lazy import so the app still runs if google-genai is not installed
                from google import genai  # type: ignore[import]
            except ImportError:
                st.error(
                    "Gemini support requires the 'google-genai' package. "
                    "Install it with `pip install google-genai` or unset GEMINI_API_KEY."
                )
                return ""

            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"{system_prompt}\n\n{user_content}",
                generation_config={"max_output_tokens": MAX_OUTPUT_TOKENS},
            )
            return (getattr(response, "text", "") or "").strip()

    except Exception as exc:  # pragma: no cover - defensive
        st.error(f"Error calling language model ({provider}): {exc}")

    return ""


FAMILY_PLANNER_SYSTEM_PROMPT = dedent(
    """
    You are a creative family activity planner who knows the US well by zip code — neighborhoods, nearby parks, cultural institutions, and family-friendly venues. Suggest 5 specific, realistic activities for busy working parents. For weekday evenings, every suggestion must be completable in 60 minutes or less — no exceptions. Use the zip code to make suggestions location-aware: reference real neighborhoods, nearby areas, or the general region. Make sure every suggestion is age-appropriate for every child specified — if ages vary widely, prioritize activities that genuinely work for all ages in the group. For each activity return: 🎯 Activity name, ⏱ Time needed, 📍 Location tip (specific to their area), 🛒 What you need, ⭐ Why kids will love it, 💡 Parent tip. Format each as a clean card using markdown. Be specific and practical — never generic.
    """
).strip()


def build_user_message(
    zip_code: str,
    mode: str,
    num_kids: int,
    child_ages: list[float],
    kids_scope: str,
    specific_child_label: str | None,
    energy_level: str,
    location_pref: str,
    budget: str,
    screen_free: bool,
) -> str:
    parts: list[str] = []
    parts.append(f"Zip code: {zip_code}.")
    parts.append(f"Mode: {mode}.")
    if kids_scope == "All kids together":
        parts.append("Kids: All together.")
    else:
        label = specific_child_label or "Child 1"
        parts.append(f"Kids: Specific child ({label}).")
    parts.append(f"Number of kids: {num_kids}.")

    for idx, age in enumerate(child_ages, start=1):
        # Render age nicely (e.g., 3.5, 8)
        age_str = f"{age:.1f}".rstrip("0").rstrip(".")
        parts.append(f"Child {idx}: {age_str} years.")

    parts.append(f"Energy level: {energy_level}.")
    parts.append(f"Location: {location_pref}.")
    parts.append(f"Budget: {budget}.")
    parts.append(f"Screen-free: {'Yes' if screen_free else 'No'}.")
    parts.append("Suggest 5 activities.")

    return " ".join(parts)


def main():
    st.set_page_config(page_title="Family Activity Planner", layout="wide")
    st.title("Family Activity Planner")

    mode = st.radio("When are you planning for?", ["Weekend", "Weekday Evening"], horizontal=True)
    if mode == "Weekday Evening":
        st.info("All suggestions will be under 60 minutes, perfect for busy weekday evenings.")

    with st.sidebar:
        st.header("Plan details")

        zip_code = st.text_input("Zip code", placeholder="e.g., 95051")

        num_kids = st.number_input(
            "Number of kids",
            min_value=1,
            max_value=6,
            value=1,
            step=1,
        )

        child_ages: list[float] = []
        for i in range(int(num_kids)):
            age = st.number_input(
                f"Child {i + 1} age",
                min_value=1.0,
                max_value=17.0,
                value=8.0 if i == 0 else 5.0,
                step=0.5,
                key=f"child_age_{i + 1}",
            )
            child_ages.append(float(age))

        kids_scope = st.selectbox(
            "Which kids to plan for",
            ["All kids together", "Specific child"],
        )

        specific_child_label: str | None = None
        if kids_scope == "Specific child":
            child_labels = [f"Child {i + 1}" for i in range(int(num_kids))]
            specific_child_label = st.selectbox("Select child", child_labels)

        energy_level = st.selectbox(
            "Energy level",
            ["Low (calm day)", "Medium", "High (burn some energy)"],
        )

        location_pref = st.selectbox(
            "Location preference",
            ["At home", "Outdoors", "Either"],
        )

        budget = st.selectbox(
            "Budget",
            ["Free", "Under $20", "No limit"],
        )

        screen_free = st.checkbox("Screen-free only")

        submit = st.button("Plan activities", type="primary")

    if submit:
        if not zip_code.strip():
            st.error("Please enter a zip code.")
            return

        user_message = build_user_message(
            zip_code=zip_code.strip(),
            mode=mode,
            num_kids=int(num_kids),
            child_ages=child_ages,
            kids_scope=kids_scope,
            specific_child_label=specific_child_label,
            energy_level=energy_level,
            location_pref=location_pref,
            budget=budget,
            screen_free=screen_free,
        )

        with st.spinner("Planning family-friendly activities..."):
            answer = call_family_activity_planner(FAMILY_PLANNER_SYSTEM_PROMPT, user_message)

        if answer:
            st.markdown(answer)


if __name__ == "__main__":
    main()

