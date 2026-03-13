"""
Question Service – handles all MongoDB interactions for the questions collection.
"""

import logging
from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.database import get_questions_collection
from app.models.question_model import QuestionDB, QuestionResponse

logger = logging.getLogger(__name__)


def _to_question_response(doc: dict) -> QuestionResponse:
    """Convert a raw MongoDB document to the sanitised API response model."""
    return QuestionResponse(
        id=str(doc["_id"]),
        question_text=doc["question_text"],
        options=doc["options"],
        difficulty=doc["difficulty"],
        topic=doc["topic"],
        tags=doc.get("tags", []),
    )


async def get_all_questions() -> List[dict]:
    """
    Fetch every question document from MongoDB.
    Returns raw dicts so the adaptive engine can work with them directly.
    """
    col: AsyncIOMotorCollection = get_questions_collection()
    cursor = col.find({})
    questions = await cursor.to_list(length=None)
    logger.debug("Fetched %d questions from DB.", len(questions))
    return questions


async def get_question_by_id(question_id: str) -> Optional[dict]:
    """
    Retrieve a single question document by its ObjectId string.

    Args:
        question_id: Hex string of the MongoDB ObjectId.

    Returns:
        Raw question dict, or None if not found / invalid id.
    """
    if not ObjectId.is_valid(question_id):
        logger.warning("get_question_by_id called with invalid id: %s", question_id)
        return None

    col: AsyncIOMotorCollection = get_questions_collection()
    doc = await col.find_one({"_id": ObjectId(question_id)})
    return doc


async def get_question_response_by_id(question_id: str) -> Optional[QuestionResponse]:
    """Return a sanitised QuestionResponse (no correct_answer) for the given id."""
    doc = await get_question_by_id(question_id)
    if doc is None:
        return None
    return _to_question_response(doc)
