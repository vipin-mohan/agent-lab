import os
from textwrap import dedent

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv


load_dotenv()


def get_anthropic_client() -> Anthropic | None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("Anthropic API key not found. Please add ANTHROPIC_API_KEY to your .env file.")
        return None
    try:
        return Anthropic(api_key=api_key)
    except Exception as exc:  # pragma: no cover - defensive
        st.error(f"Error initializing Anthropic client: {exc}")
        return None


def call_claude(system_prompt: str, user_content: str) -> str:
    client = get_anthropic_client()
    if client is None:
        return ""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception as exc:  # pragma: no cover - defensive
        st.error(f"Error calling Anthropic Claude API: {exc}")
        return ""

    text_chunks: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_chunks.append(block.text)
    return "".join(text_chunks).strip()


BASE_SYSTEM_PROMPT = dedent(
    """
    You are "PM Career Coach", an expert product management career coach with over 10 years
    of experience coaching MBA students and early-career PMs into APM/PM roles at top
    tech companies, high-growth startups, and leading enterprises.

    Core principles:
    - Give specific, actionable feedback tailored to the user's target roles and background.
    - Use clear structure with headings, subheadings, and bullet points.
    - Reference common PM frameworks (e.g., problem → insight → hypothesis → experiment → metric).
    - Emphasize prioritization, stakeholder management, and product sense.
    - Be encouraging but direct; point out gaps concretely and propose ways to close them.

    Formatting guidelines:
    - Use concise paragraphs and bullet points.
    - Use numbered steps when proposing plans or roadmaps.
    - Avoid generic platitudes; focus on practical, PM-specific advice.
    - When appropriate, include example phrases or sample responses the user can adapt.
    """
).strip()


def build_interview_prep_prompt(background: str, target_role: str, questions: str) -> tuple[str, str]:
    system_prompt = BASE_SYSTEM_PROMPT + (
        "\n\nYou are currently helping the user with **PM interview preparation**. "
        "Focus on structured answers, behavioral examples, product sense, metrics, and tradeoffs. "
        "Help them turn their experience into compelling, concise interview stories."
    )

    user_content = dedent(
        f"""
        Context about my background:
        {background or '[User did not provide background details]'}

        Target role / company / level:
        {target_role or '[User did not specify a target role or company]'}

        Interview prep questions or areas I want help with:
        {questions or '[User did not specify particular questions]'}

        Please:
        - Identify 2–4 core themes I should lean on in PM interviews.
        - Suggest structured answers (using frameworks like STAR or problem → solution → impact) for my key stories.
        - Propose 3–5 likely PM interview questions based on my target role and context.
        - Give bullet-point guidance on how to improve my delivery and depth in answers.
        """
    ).strip()

    return system_prompt, user_content


def build_gap_analysis_prompt(background: str, target_role: str, current_skills: str) -> tuple[str, str]:
    system_prompt = BASE_SYSTEM_PROMPT + (
        "\n\nYou are currently helping the user with a **PM skill and experience gap analysis**. "
        "Be specific about where they stand versus typical expectations for their target roles. "
        "Translate gaps into a focused, time-bound development plan."
    )

    user_content = dedent(
        f"""
        Current background and experience:
        {background or '[User did not provide background details]'}

        Target PM role(s), level, and timeline:
        {target_role or '[User did not specify a target role or timeline]'}

        Current PM-relevant skills, projects, or experiences:
        {current_skills or '[User did not list current skills or experiences]'}

        Please:
        - Map my current profile against expectations for my target PM roles.
        - Identify concrete skill, experience, and signaling gaps.
        - Propose a 30–90 day development plan with specific projects, habits, or deliverables.
        - Recommend how to demonstrate progress clearly on my resume, LinkedIn, and in conversations.
        """
    ).strip()

    return system_prompt, user_content


def build_career_positioning_prompt(background: str, target_companies: str, narrative: str) -> tuple[str, str]:
    system_prompt = BASE_SYSTEM_PROMPT + (
        "\n\nYou are currently helping the user with **PM career positioning and narrative**. "
        "Help them craft a compelling positioning statement and narrative tailored to their target companies."
    )

    user_content = dedent(
        f"""
        My background (education, past roles, domains, key skills):
        {background or '[User did not provide background details]'}

        Target companies / industries / product areas:
        {target_companies or '[User did not specify target companies or industries]'}

        My current career story or positioning (if any):
        {narrative or '[User did not provide a current narrative]'}

        Please:
        - Craft 1–2 concise PM positioning statements I can use in intros and summaries.
        - Propose a clear career narrative that connects my past experience to PM roles.
        - Suggest how to tailor this narrative for different types of companies (big tech, startup, non-tech).
        - Provide 3–5 concrete lines I can reuse on my resume / LinkedIn headline / About section.
        """
    ).strip()

    return system_prompt, user_content


def render_interview_prep_tab():
    st.subheader("Interview Prep")
    st.write(
        "Get structured coaching on how to tell your story, answer PM interview questions, "
        "and showcase product sense for your target roles."
    )

    col1, col2 = st.columns(2)

    with col1:
        background = st.text_area(
            "Your background",
            placeholder="Share your education, work experience, domains, and any PM-relevant projects.",
            height=180,
        )
        target_role = st.text_area(
            "Target role and company",
            placeholder="e.g., APM at a big tech company, PM at a Series B B2B SaaS startup, etc.",
            height=120,
        )

    with col2:
        questions = st.text_area(
            "Interview questions or concerns",
            placeholder=(
                "Paste practice questions, recruiter prompts, or specific areas you want help with.\n"
                "For example: product sense, execution, behavioral questions, or case-style prompts."
            ),
            height=260,
        )

    if st.button("Get Interview Coaching", type="primary", key="btn_interview_prep"):
        with st.spinner("Thinking through your PM interview strategy..."):
            system_prompt, user_prompt = build_interview_prep_prompt(background, target_role, questions)
            answer = call_claude(system_prompt, user_prompt)
        if answer:
            st.markdown("### Coaching Recommendations")
            st.markdown(answer)


def render_gap_analysis_tab():
    st.subheader("Gap Analysis")
    st.write(
        "Understand where you stand relative to PM hiring expectations and get a concrete plan "
        "to close the most important gaps."
    )

    background = st.text_area(
        "Current background",
        placeholder="Summarize your current role(s), education, domains, and PM exposure.",
        height=160,
    )
    target_role = st.text_area(
        "Target PM roles and timeline",
        placeholder="Describe your ideal PM roles, levels, and when you hope to transition.",
        height=140,
    )
    current_skills = st.text_area(
        "Current PM-relevant skills and projects",
        placeholder=(
            "List experiences that show product thinking, analytics, execution, leadership, or customer empathy.\n"
            "Include side projects, internships, class projects, and on-the-job work."
        ),
        height=180,
    )

    if st.button("Run Gap Analysis", type="primary", key="btn_gap_analysis"):
        with st.spinner("Analyzing your profile against PM expectations..."):
            system_prompt, user_prompt = build_gap_analysis_prompt(background, target_role, current_skills)
            answer = call_claude(system_prompt, user_prompt)
        if answer:
            st.markdown("### Gap Analysis and Development Plan")
            st.markdown(answer)


def render_career_positioning_tab():
    st.subheader("Career Positioning")
    st.write(
        "Refine how you position yourself as a PM, from your career narrative to your resume and LinkedIn story."
    )

    background = st.text_area(
        "Your background",
        placeholder="Summarize your story so far: education, roles, industries, PM exposure, and strengths.",
        height=140,
    )
    target_companies = st.text_area(
        "Target companies and product areas",
        placeholder="List specific companies, industries, and product types you are most excited about.",
        height=120,
    )
    narrative = st.text_area(
        "Current narrative or pitch",
        placeholder=(
            "If you already have a version of your pitch or summary, paste it here.\n"
            "If not, describe how you currently talk about your interest in PM."
        ),
        height=160,
    )

    if st.button("Refine My Positioning", type="primary", key="btn_career_positioning"):
        with st.spinner("Crafting your PM career narrative..."):
            system_prompt, user_prompt = build_career_positioning_prompt(background, target_companies, narrative)
            answer = call_claude(system_prompt, user_prompt)
        if answer:
            st.markdown("### Positioning and Narrative")
            st.markdown(answer)


def main():
    st.set_page_config(page_title="PM Career Coach", layout="wide")
    st.title("PM Career Coach")
    st.caption("Anthropic Claude-powered career coaching for aspiring and current product managers.")

    tab_interview, tab_gap, tab_positioning = st.tabs(
        ["Interview Prep", "Gap Analysis", "Career Positioning"]
    )

    with tab_interview:
        render_interview_prep_tab()
    with tab_gap:
        render_gap_analysis_tab()
    with tab_positioning:
        render_career_positioning_tab()


if __name__ == "__main__":
    main()

