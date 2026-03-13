"""
Pydantic models for the Question domain.
These are used for API I/O validation and MongoDB document shaping.
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from bson import ObjectId


class PyObjectId(str):
    """Custom type to serialise MongoDB ObjectId as a plain string in JSON."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if not ObjectId.is_valid(str(value)):
            raise ValueError(f"Invalid ObjectId: {value}")
        return str(value)


class QuestionDB(BaseModel):
    """Represents a question document as stored in MongoDB."""

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    question_text: str = Field(..., description="The full question prompt.")
    options: List[str] = Field(..., min_length=4, max_length=4, description="Exactly 4 answer choices.")
    correct_answer: str = Field(..., description="The single correct option string.")
    difficulty: float = Field(..., ge=0.1, le=1.0, description="IRT difficulty parameter (0.1 – 1.0).")
    topic: str = Field(..., description="High-level subject category.")
    tags: List[str] = Field(default_factory=list, description="Fine-grained topic tags.")

    @field_validator("correct_answer")
    @classmethod
    def correct_answer_must_be_in_options(cls, v: str, info) -> str:
        options = info.data.get("options", [])
        if options and v not in options:
            raise ValueError("correct_answer must be one of the provided options.")
        return v

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class QuestionResponse(BaseModel):
    """Sanitised question payload returned to the client (no correct_answer leakage)."""

    id: str
    question_text: str
    options: List[str]
    difficulty: float
    topic: str
    tags: List[str]
