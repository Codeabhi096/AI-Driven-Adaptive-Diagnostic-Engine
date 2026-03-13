"""
Pydantic models for the UserSession domain.
"""

from __future__ import annotations
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from app.models.question_model import PyObjectId


class AnswerRecord(BaseModel):
    """A single answered question stored within a session."""

    question_id: str
    is_correct: bool
    difficulty: float
    topic: str
    selected_answer: str


class UserSessionDB(BaseModel):
    """Full session document as stored in MongoDB."""

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str = Field(..., description="Caller-supplied identifier (e.g. UUID or username).")
    ability_score: float = Field(default=0.5, ge=0.1, le=1.0)
    current_question_id: Optional[str] = Field(default=None)
    answers: List[AnswerRecord] = Field(default_factory=list)
    questions_answered: int = Field(default=0)
    is_complete: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# ── Request / Response schemas ──────────────────────────────────────────────

class StartTestRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the test-taker.")


class SubmitAnswerRequest(BaseModel):
    session_id: str = Field(..., description="Active session ObjectId string.")
    question_id: str = Field(..., description="Question ObjectId string.")
    selected_answer: str = Field(..., description="The option string chosen by the student.")


class SessionResultResponse(BaseModel):
    session_id: str
    user_id: str
    final_ability_score: float
    questions_answered: int
    accuracy: float  # 0.0 – 1.0
    topics_missed: List[str]
    topics_correct: List[str]
    study_plan: Optional[str] = None  # LLM-generated, populated when test is complete
