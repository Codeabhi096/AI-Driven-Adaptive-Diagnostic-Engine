"""
Adaptive Engine – 1-Dimension IRT-inspired ability estimator.

Algorithm overview
──────────────────
1. Each student starts with ability_score = 0.5  (mid-range).
2. After every answer the score is updated with a logistic-IRT delta:

       P(correct) = 1 / (1 + exp(-(ability - difficulty)))
       ability_new = ability_old + η * (result - P(correct))

   where η (learning_rate) = 0.1 and result ∈ {0, 1}.

3. The score is clamped to [0.1, 1.0] so it stays meaningful.

4. The next question is chosen as the unanswered question whose
   difficulty is *closest* to the current ability score.  This
   maximises information gain and keeps the test well-calibrated.
"""

import math
import logging
from typing import List, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def probability_correct(ability: float, difficulty: float) -> float:
    """
    1-PL (Rasch) logistic model: probability that a student with the
    given ability answers a question of given difficulty correctly.

    Args:
        ability:    Student ability estimate, clamped [0.1, 1.0].
        difficulty: Question difficulty parameter, in [0.1, 1.0].

    Returns:
        Float in (0, 1).
    """
    return 1.0 / (1.0 + math.exp(-(ability - difficulty)))


def update_ability(
    ability: float,
    difficulty: float,
    is_correct: bool,
    learning_rate: float | None = None,
) -> float:
    """
    Update the student's ability estimate after one response.

    Args:
        ability:       Current ability score.
        difficulty:    Difficulty of the question just answered.
        is_correct:    Whether the student's answer was correct.
        learning_rate: Override for η (defaults to settings value).

    Returns:
        New ability score, clamped to [ability_min, ability_max].
    """
    η = learning_rate if learning_rate is not None else settings.learning_rate
    result = 1.0 if is_correct else 0.0
    p = probability_correct(ability, difficulty)

    new_ability = ability + η * (result - p)

    clamped = max(settings.ability_min, min(settings.ability_max, new_ability))
    logger.debug(
        "Ability update | old=%.4f difficulty=%.2f correct=%s p=%.4f new=%.4f clamped=%.4f",
        ability, difficulty, is_correct, p, new_ability, clamped,
    )
    return round(clamped, 4)


def select_next_question(
    ability: float,
    answered_ids: List[str],
    candidate_questions: List[dict],
) -> Optional[dict]:
    """
    Choose the best next question using the *maximum information* heuristic:
    pick the unanswered question whose difficulty is closest to the current
    ability estimate.

    Args:
        ability:             Current ability score.
        answered_ids:        List of question _id strings already used.
        candidate_questions: Full list of question dicts from MongoDB.

    Returns:
        The selected question dict, or None if all questions are exhausted.
    """
    answered_set = set(answered_ids)
    available = [q for q in candidate_questions if str(q["_id"]) not in answered_set]

    if not available:
        logger.info("No available questions remaining for ability=%.4f", ability)
        return None

    # Sort by absolute distance to current ability; stable sort keeps
    # insertion order for ties, giving a deterministic selection.
    best = min(available, key=lambda q: abs(q["difficulty"] - ability))
    logger.debug(
        "Selected question id=%s difficulty=%.2f for ability=%.4f",
        best["_id"], best["difficulty"], ability,
    )
    return best
