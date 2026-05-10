"""
Thin async adapters over core/ coaching functions.

Each function wraps a synchronous core.coach function in asyncio.to_thread
so it can be called from the async executor without blocking the event loop.
No coaching logic lives here — that all stays in core/.

Run from the pm_career_coach_app/ directory so that `core` resolves correctly.
"""

import asyncio

from core.coach import (
    career_positioning as _career_positioning,
    gap_analysis as _gap_analysis,
    interview_prep as _interview_prep,
    job_match_score as _job_match_score,
)


async def interview_prep(
    background: str,
    target_role: str,
    questions: str | None = None,
) -> str:
    return await asyncio.to_thread(
        _interview_prep, background, target_role, questions or ""
    )


async def gap_analysis(
    background: str,
    target_role: str,
    current_skills: str | None = None,
) -> str:
    return await asyncio.to_thread(
        _gap_analysis, background, target_role, current_skills or ""
    )


async def career_positioning(
    background: str,
    target_companies: str,
    narrative: str | None = None,
) -> str:
    return await asyncio.to_thread(
        _career_positioning, background, target_companies, narrative or ""
    )


async def job_match_score(resume: str, job_description: str) -> str:
    return await asyncio.to_thread(_job_match_score, resume, job_description)
