"""
System prompts and prompt builders for PM Career Coach.

All functions return (system_prompt, user_content) tuples — plain strings,
no Streamlit dependencies. The retrieval call is the only I/O here; it
degrades gracefully to an empty string when Pinecone is unavailable.
"""

from textwrap import dedent

from .retrieval import retrieve_relevant_coaching

# ---------------------------------------------------------------------------
# System-prompt constants
# ---------------------------------------------------------------------------

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

JOB_MATCH_SYSTEM_PROMPT = (
    "You are an expert PM recruiter and career coach who has reviewed thousands of PM resumes "
    "and job descriptions at top tech companies. Given a resume and job description, score the "
    "match from 1–10 based on: skills alignment, domain experience, seniority fit, and "
    "language/keyword match. Be direct and specific — reference actual content from both the "
    "resume and JD, not generic advice. A score of 7+ means strong candidate, 5–6 means viable "
    "with positioning work, below 5 means significant gaps exist."
)


# ---------------------------------------------------------------------------
# Prompt builders — return (system_prompt, user_content)
# ---------------------------------------------------------------------------

def build_interview_prep_prompt(
    background: str, target_role: str, questions: str
) -> tuple[str, str]:
    coaching_context = retrieve_relevant_coaching(
        f"PM interview prep {target_role} {background}"
    )
    system_prompt = BASE_SYSTEM_PROMPT + (
        "\n\nYou are currently helping the user with **PM interview preparation**. "
        "Focus on structured answers, behavioral examples, product sense, metrics, and tradeoffs. "
        "Help them turn their experience into compelling, concise interview stories."
    )
    if coaching_context:
        system_prompt += coaching_context

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


def build_gap_analysis_prompt(
    background: str, target_role: str, current_skills: str
) -> tuple[str, str]:
    coaching_context = retrieve_relevant_coaching(
        f"PM skill gaps {target_role} {current_skills}"
    )
    system_prompt = BASE_SYSTEM_PROMPT + (
        "\n\nYou are currently helping the user with a **PM skill and experience gap analysis**. "
        "Be specific about where they stand versus typical expectations for their target roles. "
        "Translate gaps into a focused, time-bound development plan."
    )
    if coaching_context:
        system_prompt += coaching_context

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


def build_career_positioning_prompt(
    background: str, target_companies: str, narrative: str
) -> tuple[str, str]:
    coaching_context = retrieve_relevant_coaching(
        f"PM career narrative positioning {target_companies}"
    )
    system_prompt = BASE_SYSTEM_PROMPT + (
        "\n\nYou are currently helping the user with **PM career positioning and narrative**. "
        "Help them craft a compelling positioning statement and narrative tailored to their target companies."
    )
    if coaching_context:
        system_prompt += coaching_context

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


def build_job_match_prompt(resume: str, job_description: str) -> tuple[str, str]:
    coaching_context = retrieve_relevant_coaching(
        f"PM job match resume scoring {job_description}"
    )
    system_prompt = JOB_MATCH_SYSTEM_PROMPT
    if coaching_context:
        system_prompt += coaching_context

    user_content = dedent(
        f"""
        Here is my resume:
        {resume}

        Here is the job description:
        {job_description}

        Please evaluate my fit and return your response in exactly this format:

        ## Match Score: X/10

        ### ✅ Strong Matches (what's working in your favor)
        - ...

        ### ⚠️ Gaps to Address (what's missing or weak)
        - ...

        ### 💡 How to Position Yourself for This Role
        - ...

        ### 📝 Suggested Resume Tweaks
        - ...
        """
    ).strip()

    return system_prompt, user_content
