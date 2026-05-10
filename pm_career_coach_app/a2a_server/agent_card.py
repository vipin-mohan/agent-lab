"""
Builds the A2A AgentCard for the PM Career Coach.

Uses A2A SDK v1.0 patterns:
- supported_interfaces with AgentInterface (replaces top-level url field from v0.3)
- AgentCapabilities with streaming=True
- Four skills matching the core/ coaching functions
"""

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)


def build_agent_card(public_url: str) -> AgentCard:
    """Build and return the public AgentCard served at /.well-known/agent-card.json."""
    skills = [
        AgentSkill(
            id="interview_prep",
            name="Interview Prep",
            description=(
                "Generate PM interview preparation: themes to lean on, STAR-formatted "
                "story guidance, likely questions for the role, delivery tips. Use when "
                "the user is preparing for upcoming interviews."
            ),
            tags=["pm", "interview", "coaching"],
            examples=[
                "Help me prep for a Senior PM interview at Adobe focused on agentic platforms.",
                "What questions should I expect for a Director of Product role at NTT Data?",
            ],
        ),
        AgentSkill(
            id="gap_analysis",
            name="Skill Gap Analysis",
            description=(
                "Map the user's current background against PM hiring expectations and "
                "produce a 30-90 day development plan with specific deliverables. Use "
                "when the user wants to know what gaps to close."
            ),
            tags=["pm", "career", "skill-gap"],
            examples=[
                "What gaps do I need to close to be a strong candidate for a Director of PM role at Adobe?",
            ],
        ),
        AgentSkill(
            id="career_positioning",
            name="Career Positioning",
            description=(
                "Craft positioning statements, career narrative, company-type variations, "
                "and reusable resume/LinkedIn lines. Use when the user is framing or "
                "reframing their story."
            ),
            tags=["pm", "positioning", "narrative"],
            examples=[
                "Help me craft a positioning statement for senior PM roles at AI infrastructure startups.",
            ],
        ),
        AgentSkill(
            id="job_match_score",
            name="Job Match Score",
            description=(
                "Score a resume against a job description (1-10) with strong matches, "
                "gaps, positioning advice, and resume tweaks. Use when the user provides "
                "a JD and wants a fit assessment."
            ),
            tags=["pm", "job-match", "resume"],
            examples=[
                "Score my resume against this Adobe Senior Director of PM job description.",
            ],
        ),
    ]

    return AgentCard(
        name="PM Career Coach",
        description=(
            "An A2A agent that provides PM career coaching: interview prep, skill gap "
            "analysis, career positioning, and job match scoring. Backed by 250+ real "
            "coaching sessions with MBA students at UC Berkeley Haas."
        ),
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                url=public_url,
            )
        ],
        skills=skills,
    )
