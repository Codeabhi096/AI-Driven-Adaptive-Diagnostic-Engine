"""
Database Seed Script
────────────────────
Populates the `questions` collection with 20 GRE-style questions spanning:
  Algebra, Geometry, Arithmetic, Vocabulary, Reading Comprehension

Usage:
    python seed/seed_questions.py

Requires a .env file (or environment variables) with MONGODB_URI and MONGODB_DB_NAME.
"""

import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "adaptive_engine")

QUESTIONS = [
    # ── Arithmetic (easy → medium) ──────────────────────────────────────────
    {
        "question_text": "What is 15% of 200?",
        "options": ["20", "25", "30", "35"],
        "correct_answer": "30",
        "difficulty": 0.2,
        "topic": "Arithmetic",
        "tags": ["percentage", "mental-math"],
    },
    {
        "question_text": "If a train travels at 60 mph, how long does it take to cover 150 miles?",
        "options": ["2 hours", "2.5 hours", "3 hours", "3.5 hours"],
        "correct_answer": "2.5 hours",
        "difficulty": 0.3,
        "topic": "Arithmetic",
        "tags": ["speed-distance-time", "word-problem"],
    },
    {
        "question_text": "What is the least common multiple (LCM) of 12 and 18?",
        "options": ["24", "36", "48", "72"],
        "correct_answer": "36",
        "difficulty": 0.4,
        "topic": "Arithmetic",
        "tags": ["LCM", "number-theory"],
    },
    {
        "question_text": (
            "A store offers a 20% discount on a jacket priced at $120. "
            "After the discount, a 10% tax is applied. What is the final price?"
        ),
        "options": ["$96.00", "$100.80", "$105.60", "$108.00"],
        "correct_answer": "$105.60",
        "difficulty": 0.55,
        "topic": "Arithmetic",
        "tags": ["percentage", "discount", "tax"],
    },

    # ── Algebra (easy → hard) ───────────────────────────────────────────────
    {
        "question_text": "Solve for x: 3x + 7 = 22",
        "options": ["3", "4", "5", "6"],
        "correct_answer": "5",
        "difficulty": 0.2,
        "topic": "Algebra",
        "tags": ["linear-equations", "solving"],
    },
    {
        "question_text": "Which of the following is a root of x² − 5x + 6 = 0?",
        "options": ["1", "2", "4", "5"],
        "correct_answer": "2",
        "difficulty": 0.4,
        "topic": "Algebra",
        "tags": ["quadratic", "factoring"],
    },
    {
        "question_text": (
            "If f(x) = 2x² − 3x + 1, what is f(−2)?"
        ),
        "options": ["3", "11", "15", "−3"],
        "correct_answer": "15",
        "difficulty": 0.5,
        "topic": "Algebra",
        "tags": ["functions", "substitution"],
    },
    {
        "question_text": (
            "The sum of two numbers is 40 and their difference is 10. "
            "What is the product of the two numbers?"
        ),
        "options": ["375", "400", "425", "350"],
        "correct_answer": "375",
        "difficulty": 0.6,
        "topic": "Algebra",
        "tags": ["systems-of-equations", "word-problem"],
    },
    {
        "question_text": (
            "For what value of k does kx² − 6x + 3 = 0 have exactly one real solution?"
        ),
        "options": ["k = 1", "k = 2", "k = 3", "k = 4"],
        "correct_answer": "k = 3",
        "difficulty": 0.75,
        "topic": "Algebra",
        "tags": ["discriminant", "quadratic"],
    },

    # ── Geometry (medium → hard) ────────────────────────────────────────────
    {
        "question_text": "What is the area of a circle with radius 7? (Use π ≈ 3.14)",
        "options": ["43.96", "153.86", "144", "176"],
        "correct_answer": "153.86",
        "difficulty": 0.3,
        "topic": "Geometry",
        "tags": ["circle", "area"],
    },
    {
        "question_text": (
            "A right triangle has legs of length 9 and 12. "
            "What is the length of the hypotenuse?"
        ),
        "options": ["13", "15", "17", "21"],
        "correct_answer": "15",
        "difficulty": 0.4,
        "topic": "Geometry",
        "tags": ["Pythagorean-theorem", "right-triangle"],
    },
    {
        "question_text": (
            "Two parallel lines are cut by a transversal. "
            "One co-interior (same-side interior) angle measures 65°. "
            "What is the measure of the other co-interior angle?"
        ),
        "options": ["65°", "115°", "125°", "180°"],
        "correct_answer": "115°",
        "difficulty": 0.55,
        "topic": "Geometry",
        "tags": ["parallel-lines", "transversal", "angles"],
    },
    {
        "question_text": (
            "A cylinder has radius 5 and height 10. "
            "What is its total surface area? (Use π ≈ 3.14)"
        ),
        "options": ["392.5", "471", "314", "628"],
        "correct_answer": "471",
        "difficulty": 0.65,
        "topic": "Geometry",
        "tags": ["cylinder", "surface-area"],
    },
    {
        "question_text": (
            "In a regular hexagon with side length 6, "
            "what is the area? (Use √3 ≈ 1.732)"
        ),
        "options": ["93.53", "54√3", "108√3", "72"],
        "correct_answer": "93.53",
        "difficulty": 0.8,
        "topic": "Geometry",
        "tags": ["regular-polygon", "hexagon", "area"],
    },

    # ── Vocabulary (medium → hard) ──────────────────────────────────────────
    {
        "question_text": "Choose the word most similar in meaning to EPHEMERAL.",
        "options": ["Eternal", "Transient", "Robust", "Constant"],
        "correct_answer": "Transient",
        "difficulty": 0.45,
        "topic": "Vocabulary",
        "tags": ["GRE-words", "synonyms"],
    },
    {
        "question_text": "Choose the word most nearly OPPOSITE in meaning to LOQUACIOUS.",
        "options": ["Verbose", "Taciturn", "Garrulous", "Eloquent"],
        "correct_answer": "Taciturn",
        "difficulty": 0.6,
        "topic": "Vocabulary",
        "tags": ["GRE-words", "antonyms"],
    },
    {
        "question_text": (
            "The professor's lecture was so ABSTRUSE that even the graduate "
            "students found it difficult to follow. "
            "ABSTRUSE most nearly means:"
        ),
        "options": ["Clear", "Esoteric", "Entertaining", "Succinct"],
        "correct_answer": "Esoteric",
        "difficulty": 0.7,
        "topic": "Vocabulary",
        "tags": ["GRE-words", "context-clues"],
    },

    # ── Reading Comprehension (medium → hard) ──────────────────────────────
    {
        "question_text": (
            "Passage: 'Despite initial scepticism, the new renewable-energy policy "
            "gained broad support once economists projected a 15% reduction in long-term "
            "energy costs.' "
            "\n\nWhich of the following best describes the shift described in the passage?"
        ),
        "options": [
            "Opposition that turned into acceptance due to economic evidence.",
            "Government policy that was immediately popular.",
            "A policy that failed due to economic concerns.",
            "A debate between economists and environmentalists.",
        ],
        "correct_answer": "Opposition that turned into acceptance due to economic evidence.",
        "difficulty": 0.5,
        "topic": "Reading Comprehension",
        "tags": ["inference", "main-idea"],
    },
    {
        "question_text": (
            "Passage: 'Cognitive load theory posits that working memory has a finite "
            "capacity. When instructional materials exceed this capacity, learning is "
            "impaired. Therefore, well-designed instruction must minimise extraneous "
            "cognitive load while maximising germane load.' "
            "\n\nThe author's primary purpose is to:"
        ),
        "options": [
            "Argue that working memory is unimportant.",
            "Describe implications of cognitive load theory for instructional design.",
            "Refute cognitive load theory with new evidence.",
            "Summarise the history of cognitive psychology.",
        ],
        "correct_answer": "Describe implications of cognitive load theory for instructional design.",
        "difficulty": 0.65,
        "topic": "Reading Comprehension",
        "tags": ["author-purpose", "inference"],
    },
    {
        "question_text": (
            "Passage: 'The Sapir–Whorf hypothesis, in its strong form, holds that "
            "language determines thought—that speakers of different languages are "
            "cognitively confined to the structures of their mother tongue. "
            "Most contemporary linguists accept only the weak version: that language "
            "influences but does not wholly determine cognition.' "
            "\n\nBased on the passage, which statement would most contemporary "
            "linguists agree with?"
        ),
        "options": [
            "Language has no effect on how people think.",
            "Thought is entirely independent of language.",
            "Language shapes cognition but does not fully constrain it.",
            "Different languages create entirely separate realities for their speakers.",
        ],
        "correct_answer": "Language shapes cognition but does not fully constrain it.",
        "difficulty": 0.8,
        "topic": "Reading Comprehension",
        "tags": ["critical-reading", "inference", "author-stance"],
    },
]


async def seed_database() -> None:
    """Connect to MongoDB and insert question documents, skipping duplicates."""
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    col = db["questions"]

    inserted, skipped = 0, 0

    for q in QUESTIONS:
        # Idempotent: skip if question_text already exists
        existing = await col.find_one({"question_text": q["question_text"]})
        if existing:
            logger.info("SKIP (already exists): %.60s…", q["question_text"])
            skipped += 1
            continue

        await col.insert_one(q)
        logger.info("INSERT: [%-22s d=%.2f] %.60s…", q["topic"], q["difficulty"], q["question_text"])
        inserted += 1

    client.close()
    logger.info("Seed complete — inserted: %d, skipped: %d", inserted, skipped)


if __name__ == "__main__":
    asyncio.run(seed_database())
