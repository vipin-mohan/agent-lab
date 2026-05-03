import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Bridge: push Streamlit Cloud secrets into os.environ so that core/
# modules (which read env vars only) see them when running on Streamlit Cloud.
# This must happen before any core import triggers secret reads.
# ---------------------------------------------------------------------------

def _sync_streamlit_secrets_to_env() -> None:
    """Copy Streamlit secrets into os.environ for core/ modules to read."""
    keys = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "PINECONE_API_KEY",
    ]
    for key in keys:
        if key not in os.environ:
            try:
                value = st.secrets[key]  # type: ignore[index]
                if value:
                    os.environ[key] = str(value)
            except Exception:
                pass


_sync_streamlit_secrets_to_env()

# ---------------------------------------------------------------------------
# Core imports — Streamlit-free shared logic
# ---------------------------------------------------------------------------

import core.coach as coach
from core.llm import LLMError
from core.retrieval import get_pinecone_index


# ---------------------------------------------------------------------------
# Tab renderers
# ---------------------------------------------------------------------------

def render_interview_prep_tab() -> None:
    st.subheader("Interview Prep")
    st.info("💡 Powered by insights from 250+ PM coaching sessions at UC Berkeley Haas over 5 years — not generic advice.")
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

    if st.button("Get Interview Coaching", type="primary", key="btn_interview_prep", use_container_width=True):
        with st.spinner("Thinking through your PM interview strategy..."):
            try:
                answer = coach.interview_prep(background, target_role, questions)
            except LLMError as exc:
                st.error(str(exc))
                return
        if answer:
            st.markdown("### Coaching Recommendations")
            st.markdown(answer)


def render_gap_analysis_tab() -> None:
    st.subheader("Gap Analysis")
    st.info("💡 Powered by insights from 250+ PM coaching sessions at UC Berkeley Haas over 5 years — not generic advice.")
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

    if st.button("Run Gap Analysis", type="primary", key="btn_gap_analysis", use_container_width=True):
        with st.spinner("Analyzing your profile against PM expectations..."):
            try:
                answer = coach.gap_analysis(background, target_role, current_skills)
            except LLMError as exc:
                st.error(str(exc))
                return
        if answer:
            st.markdown("### Gap Analysis and Development Plan")
            st.markdown(answer)


def render_career_positioning_tab() -> None:
    st.subheader("Career Positioning")
    st.info("💡 Powered by insights from 250+ PM coaching sessions at UC Berkeley Haas over 5 years — not generic advice.")
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

    if st.button("Refine My Positioning", type="primary", key="btn_career_positioning", use_container_width=True):
        with st.spinner("Crafting your PM career narrative..."):
            try:
                answer = coach.career_positioning(background, target_companies, narrative)
            except LLMError as exc:
                st.error(str(exc))
                return
        if answer:
            st.markdown("### Positioning and Narrative")
            st.markdown(answer)


def render_job_match_tab() -> None:
    st.subheader("Job Match Score")
    st.info("💡 Powered by insights from 250+ PM coaching sessions at UC Berkeley Haas over 5 years — not generic advice.")
    st.write(
        "Paste your resume and a job description to get a structured match analysis — "
        "including a score out of 10, your strengths, gaps, and specific resume tweaks."
    )

    col1, col2 = st.columns(2)

    with col1:
        resume = st.text_area(
            "Your Resume",
            placeholder="Paste your full resume here",
            height=400,
        )

    with col2:
        job_description = st.text_area(
            "Job Description",
            placeholder="Paste the full job description here",
            height=400,
        )

    if st.button("Analyze Match", type="primary", key="btn_job_match", use_container_width=True):
        if not resume.strip() or not job_description.strip():
            st.warning("Please paste both your resume and the job description before submitting.")
        else:
            with st.spinner("Scoring your resume against the job description..."):
                try:
                    answer = coach.job_match_score(resume, job_description)
                except LLMError as exc:
                    st.error(str(exc))
                    return
            if answer:
                st.markdown(answer)


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def _inject_responsive_css() -> None:
    st.markdown(
        """
        <style>
        /* Stack columns vertically on mobile screens */
        @media (max-width: 768px) {
            div[data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                padding-top: 2rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="PM Career Coach", layout="wide")
    _inject_responsive_css()
    st.title("PM Career Coach")
    st.caption("AI-powered career coaching for aspiring and current product managers.")

    with st.sidebar:
        if get_pinecone_index() is not None:
            st.success("✅ Coaching knowledge base active")
        else:
            st.warning("⚠️ Coaching knowledge base unavailable")

    tab_interview, tab_gap, tab_positioning, tab_job_match = st.tabs(
        ["Interview Prep", "Gap Analysis", "Career Positioning", "Job Match Score"]
    )

    with tab_interview:
        render_interview_prep_tab()
    with tab_gap:
        render_gap_analysis_tab()
    with tab_positioning:
        render_career_positioning_tab()
    with tab_job_match:
        render_job_match_tab()


if __name__ == "__main__":
    main()
