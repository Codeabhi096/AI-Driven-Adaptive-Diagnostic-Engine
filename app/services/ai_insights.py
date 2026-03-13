"""
AI Insights Service – generates a personalised 3-step study plan using
the Anthropic API (Claude) once the adaptive test is complete.

Falls back gracefully if the API key is missing or the call fails,
so the rest of the system keeps working in offline/test environments.
"""

import logging
from typing import List

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_prompt(
    topics_missed: List[str],
    ability_score: float,
    accuracy: float,
) -> str:
    """
    Construct the user-facing prompt sent to the LLM.

    Args:
        topics_missed: List of topic strings where the student got ≥1 question wrong.
        ability_score: Final IRT ability estimate (0.1 – 1.0).
        accuracy:      Fraction of correct answers (0.0 – 1.0).

    Returns:
        A plain-text prompt string.
    """
    missed_str = ", ".join(topics_missed) if topics_missed else "none"
    difficulty_label = (
        "beginner" if ability_score < 0.4
        else "intermediate" if ability_score < 0.7
        else "advanced"
    )

    return (
        f"A student just completed an adaptive GRE-style diagnostic test.\n\n"
        f"Performance summary:\n"
        f"- Final ability score: {ability_score:.2f} / 1.00  ({difficulty_label} level)\n"
        f"- Overall accuracy: {accuracy * 100:.1f}%\n"
        f"- Topics with missed questions: {missed_str}\n\n"
        f"Based on this data, write a concise 3-step personalised study plan. "
        f"Number each step clearly (Step 1, Step 2, Step 3). "
        f"Be specific, actionable, and encouraging. "
        f"Keep the total response under 200 words."
    )


async def generate_study_plan(
    topics_missed: List[str],
    ability_score: float,
    accuracy: float,
) -> str:
    """
    Call the Anthropic Claude API to generate a personalised study plan.

    Args:
        topics_missed: Weak topics derived from the session answer log.
        ability_score: Student's final estimated ability.
        accuracy:      Fraction of correct answers.

    Returns:
        A formatted study plan string, or a fallback message on error.
    """
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set – returning placeholder study plan.")
        return _fallback_plan(topics_missed, ability_score)

    try:
        import anthropic  # local import keeps startup fast when key is absent

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        prompt = _build_prompt(topics_missed, ability_score, accuracy)

        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )

        plan = message.content[0].text.strip()
        logger.info("Study plan generated successfully via Anthropic API.")
        return plan

    except Exception as exc:  # pragma: no cover
        logger.error("Failed to generate study plan via Anthropic: %s", exc, exc_info=True)
        return _fallback_plan(topics_missed, ability_score)


def _fallback_plan(topics_missed: List[str], ability_score: float) -> str:
    """
    Rule-based fallback plan when the LLM is unavailable.
    Ensures the endpoint always returns something useful.
    """
    missed_str = ", ".join(topics_missed[:3]) if topics_missed else "general topics"
    level = "foundational" if ability_score < 0.5 else "intermediate"
    return (
        f"Step 1: Review {level} concepts in {missed_str}.\n"
        f"Step 2: Attempt 10–15 practice problems at difficulty ≈ {ability_score:.1f}.\n"
        f"Step 3: Revisit any incorrectly answered questions and study the underlying concepts."
    )
