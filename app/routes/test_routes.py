"""
Test Routes – all HTTP endpoints for the Adaptive Diagnostic Engine.

Endpoints
─────────
POST   /start-test                → Create session, return first question.
GET    /next-question/{session_id} → Return next adaptive question.
POST   /submit-answer             → Grade answer, update ability, return next question.
GET    /results/{session_id}      → Return final results and LLM study plan.
"""

import logging
from datetime import timezone, datetime
from typing import Any, Dict

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status

from app.database import get_sessions_collection
from app.models.session_model import (
    StartTestRequest,
    SubmitAnswerRequest,
    SessionResultResponse,
    AnswerRecord,
    UserSessionDB,
)
from app.models.question_model import QuestionResponse
from app.services.adaptive_engine import update_ability, select_next_question
from app.services.question_service import get_all_questions, get_question_by_id
from app.services.ai_insights import generate_study_plan
from app.utils.helpers import (
    compute_accuracy,
    extract_topics_missed,
    extract_topics_correct,
    question_doc_to_response,
    utc_now,
)
from app.config import get_settings

router = APIRouter(tags=["Adaptive Test"])
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_session_or_404(session_id: str) -> dict:
    """Fetch a session document by id, raising 404 if not found or id is invalid."""
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session_id format.")

    col = get_sessions_collection()
    session = await col.find_one({"_id": ObjectId(session_id)})
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return session


def _session_to_domain(doc: dict) -> UserSessionDB:
    """Map a raw MongoDB dict back to the UserSessionDB Pydantic model."""
    answers = [AnswerRecord(**a) for a in doc.get("answers", [])]
    return UserSessionDB(
        _id=str(doc["_id"]),
        user_id=doc["user_id"],
        ability_score=doc["ability_score"],
        current_question_id=doc.get("current_question_id"),
        answers=answers,
        questions_answered=doc["questions_answered"],
        is_complete=doc.get("is_complete", False),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


# ── POST /start-test ──────────────────────────────────────────────────────────

@router.post(
    "/start-test",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Start a new adaptive test session",
)
async def start_test(body: StartTestRequest) -> Dict[str, Any]:
    """
    Create a fresh UserSession at the baseline ability score (0.5),
    select the best-matching first question, and return it to the client.

    Request body:
        user_id (str): Any string identifying the student.

    Returns:
        session_id, first question details, and current ability score.
    """
    all_questions = await get_all_questions()
    if not all_questions:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No questions available. Please seed the database.",
        )

    initial_ability = settings.ability_initial
    first_q = select_next_question(initial_ability, [], all_questions)
    if first_q is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not select first question.")

    now = utc_now()
    session_doc = {
        "user_id": body.user_id,
        "ability_score": initial_ability,
        "current_question_id": str(first_q["_id"]),
        "answers": [],
        "questions_answered": 0,
        "is_complete": False,
        "created_at": now,
        "updated_at": now,
    }

    col = get_sessions_collection()
    result = await col.insert_one(session_doc)
    session_id = str(result.inserted_id)

    logger.info("New session created: %s for user: %s", session_id, body.user_id)

    return {
        "session_id": session_id,
        "ability_score": initial_ability,
        "question": question_doc_to_response(first_q).model_dump(),
        "questions_answered": 0,
        "total_questions": settings.max_questions_per_session,
    }


# ── GET /next-question/{session_id} ──────────────────────────────────────────

@router.get(
    "/next-question/{session_id}",
    response_model=Dict[str, Any],
    summary="Get the next adaptive question for an active session",
)
async def get_next_question(session_id: str) -> Dict[str, Any]:
    """
    Return the next question tailored to the student's current ability score.
    The question whose difficulty is closest to the ability score is chosen,
    excluding all previously answered questions.

    Path param:
        session_id: Active session ObjectId string.

    Returns:
        Next question and current session metadata.
    """
    session = await _get_session_or_404(session_id)
    domain = _session_to_domain(session)

    if domain.is_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This test session is already complete. Fetch /results instead.",
        )

    all_questions = await get_all_questions()
    answered_ids = [a.question_id for a in domain.answers]
    next_q = select_next_question(domain.ability_score, answered_ids, all_questions)

    if next_q is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No more questions available for this session.",
        )

    return {
        "session_id": session_id,
        "ability_score": domain.ability_score,
        "question": question_doc_to_response(next_q).model_dump(),
        "questions_answered": domain.questions_answered,
        "total_questions": settings.max_questions_per_session,
    }


# ── POST /submit-answer ───────────────────────────────────────────────────────

@router.post(
    "/submit-answer",
    response_model=Dict[str, Any],
    summary="Submit an answer and receive the next question (or final results)",
)
async def submit_answer(body: SubmitAnswerRequest) -> Dict[str, Any]:
    """
    Grade the student's answer, update the IRT ability estimate, persist the
    answer record, and return either the next question or a completion notice.

    Request body:
        session_id      (str): Active session id.
        question_id     (str): The question being answered.
        selected_answer (str): The student's chosen option string.

    Returns:
        Correctness feedback, updated ability score, and the next question
        (or a completion flag when max_questions is reached).
    """
    session = await _get_session_or_404(body.session_id)
    domain = _session_to_domain(session)

    if domain.is_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is already complete.",
        )

    # ── Fetch & validate question ──────────────────────────────────────────
    q_doc = await get_question_by_id(body.question_id)
    if q_doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    already_answered = [a.question_id for a in domain.answers]
    if body.question_id in already_answered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This question has already been answered in this session.",
        )

    # ── Grade answer ───────────────────────────────────────────────────────
    is_correct = body.selected_answer == q_doc["correct_answer"]
    new_ability = update_ability(domain.ability_score, q_doc["difficulty"], is_correct)

    answer_record = AnswerRecord(
        question_id=body.question_id,
        is_correct=is_correct,
        difficulty=q_doc["difficulty"],
        topic=q_doc["topic"],
        selected_answer=body.selected_answer,
    )

    updated_answers = domain.answers + [answer_record]
    questions_answered = domain.questions_answered + 1
    is_complete = questions_answered >= settings.max_questions_per_session

    # ── Persist to MongoDB ─────────────────────────────────────────────────
    col = get_sessions_collection()
    await col.update_one(
        {"_id": ObjectId(body.session_id)},
        {
            "$set": {
                "ability_score": new_ability,
                "questions_answered": questions_answered,
                "is_complete": is_complete,
                "updated_at": utc_now(),
            },
            "$push": {"answers": answer_record.model_dump()},
        },
    )

    # ── Build response ─────────────────────────────────────────────────────
    response: Dict[str, Any] = {
        "session_id": body.session_id,
        "is_correct": is_correct,
        "correct_answer": q_doc["correct_answer"],
        "ability_score": new_ability,
        "questions_answered": questions_answered,
        "total_questions": settings.max_questions_per_session,
        "is_complete": is_complete,
    }

    if is_complete:
        response["message"] = "Test complete! Fetch /results/{session_id} for your full report."
        logger.info("Session %s completed. Final ability=%.4f", body.session_id, new_ability)
    else:
        all_questions = await get_all_questions()
        answered_ids = [a.question_id for a in updated_answers]
        next_q = select_next_question(new_ability, answered_ids, all_questions)
        if next_q:
            response["next_question"] = question_doc_to_response(next_q).model_dump()

    return response


# ── GET /results/{session_id} ─────────────────────────────────────────────────

@router.get(
    "/results/{session_id}",
    response_model=SessionResultResponse,
    summary="Retrieve final results and AI-generated study plan for a completed session",
)
async def get_results(session_id: str) -> SessionResultResponse:
    """
    Return the student's performance report and LLM-generated personalised
    study plan.  The study plan is generated on first access and cached in
    the session document to avoid redundant API calls.

    Path param:
        session_id: Session ObjectId string.

    Returns:
        SessionResultResponse with ability score, accuracy, topics, and study plan.
    """
    session = await _get_session_or_404(session_id)
    domain = _session_to_domain(session)

    accuracy = compute_accuracy(domain.answers)
    topics_missed = extract_topics_missed(domain.answers)
    topics_correct = extract_topics_correct(domain.answers)

    # Retrieve cached plan or generate a new one
    study_plan: str | None = session.get("study_plan")
    if study_plan is None and domain.is_complete:
        study_plan = await generate_study_plan(topics_missed, domain.ability_score, accuracy)
        # Cache in DB to avoid re-calling the LLM on subsequent fetches
        col = get_sessions_collection()
        await col.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"study_plan": study_plan, "updated_at": utc_now()}},
        )

    return SessionResultResponse(
        session_id=session_id,
        user_id=domain.user_id,
        final_ability_score=domain.ability_score,
        questions_answered=domain.questions_answered,
        accuracy=accuracy,
        topics_missed=topics_missed,
        topics_correct=topics_correct,
        study_plan=study_plan,
    )
