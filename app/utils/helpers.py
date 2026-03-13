"""
Shared utility helpers used across services and routes.
"""

from __future__ import annotations
from typing import List
from datetime import datetime, timezone

from app.models.session_model import AnswerRecord
from app.models.question_model import QuestionResponse


def compute_accuracy(answers: List[AnswerRecord]) -> float:
    """
    Calculate the fraction of correct answers in a session.

    Returns:
        Float in [0.0, 1.0].  Returns 0.0 for an empty answer list.
    """
    if not answers:
        return 0.0
    correct = sum(1 for a in answers if a.is_correct)
    return round(correct / len(answers), 4)


def extract_topics_missed(answers: List[AnswerRecord]) -> List[str]:
    """
    Return a deduplicated list of topics where the student got ≥1 question wrong.

    Args:
        answers: Full answer log from the session.

    Returns:
        Sorted list of topic strings.
    """
    missed = {a.topic for a in answers if not a.is_correct}
    return sorted(missed)


def extract_topics_correct(answers: List[AnswerRecord]) -> List[str]:
    """Return deduplicated topics where the student answered every question correctly."""
    correct_topics = {a.topic for a in answers if a.is_correct}
    missed_topics = {a.topic for a in answers if not a.is_correct}
    purely_correct = correct_topics - missed_topics
    return sorted(purely_correct)


def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def question_doc_to_response(doc: dict) -> QuestionResponse:
    """Convert a raw MongoDB question document into a QuestionResponse (no answer leak)."""
    return QuestionResponse(
        id=str(doc["_id"]),
        question_text=doc["question_text"],
        options=doc["options"],
        difficulty=doc["difficulty"],
        topic=doc["topic"],
        tags=doc.get("tags", []),
    )
