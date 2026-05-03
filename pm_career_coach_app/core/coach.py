"""
High-level coaching functions — the public API consumed by both the
Streamlit app and the MCP server tools.

Each function is a thin orchestration layer:
  inputs → prompt builder → LLM → plain string result

Raises core.llm.LLMError on any LLM failure so callers can handle it
in their own context (st.error for Streamlit, HTTP 500 for MCP).
"""

from .llm import invoke_llm
from .prompts import (
    build_career_positioning_prompt,
    build_gap_analysis_prompt,
    build_interview_prep_prompt,
    build_job_match_prompt,
)
from .retrieval import search_raw


def interview_prep(background: str, target_role: str, questions: str) -> str:
    """
    Return structured PM interview coaching as a markdown string.

    Covers: core themes to lean on, STAR-structured story suggestions,
    likely interview questions for the target role, and delivery guidance.
    Grounded in patterns from 250+ PM coaching sessions.
    """
    system_prompt, user_content = build_interview_prep_prompt(
        background, target_role, questions
    )
    return invoke_llm(system_prompt, user_content)


def gap_analysis(background: str, target_role: str, current_skills: str) -> str:
    """
    Return a PM skill and experience gap analysis as a markdown string.

    Covers: profile-vs-expectations mapping, concrete gaps, a 30–90 day
    development plan, and guidance on demonstrating progress.
    """
    system_prompt, user_content = build_gap_analysis_prompt(
        background, target_role, current_skills
    )
    return invoke_llm(system_prompt, user_content)


def career_positioning(background: str, target_companies: str, narrative: str) -> str:
    """
    Return PM career positioning advice as a markdown string.

    Covers: 1–2 positioning statements, a career narrative, company-type
    variations (big tech / startup / non-tech), and reusable resume/
    LinkedIn lines.
    """
    system_prompt, user_content = build_career_positioning_prompt(
        background, target_companies, narrative
    )
    return invoke_llm(system_prompt, user_content)


def job_match_score(resume: str, job_description: str) -> str:
    """
    Return a structured job-match analysis as a markdown string.

    Covers: match score 1–10, strong matches, gaps to address, positioning
    advice, and concrete resume tweaks. 7+ = strong candidate, 5–6 = viable
    with positioning work, <5 = significant gaps.
    """
    system_prompt, user_content = build_job_match_prompt(resume, job_description)
    return invoke_llm(system_prompt, user_content)


def search_coaching_notes(query: str, top_k: int = 5) -> list[dict]:
    """
    Semantic search over the coaching notes corpus.

    Returns a list of dicts, each with:
      - ``text``  (str)   — the coaching note chunk
      - ``score`` (float) — cosine similarity score

    Returns an empty list when Pinecone is unavailable.
    """
    return search_raw(query, top_k)
