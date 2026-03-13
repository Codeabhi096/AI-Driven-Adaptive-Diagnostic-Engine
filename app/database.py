"""
Async MongoDB connection management using Motor.
Provides a single shared database client for the entire application lifecycle.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Module-level client – created once, reused across requests
_client: AsyncIOMotorClient | None = None


async def connect_to_mongo() -> None:
    """Open the Motor client connection. Called at application startup."""
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    # Lightweight ping to validate credentials immediately
    await _client.admin.command("ping")
    logger.info("MongoDB connection established.")


async def close_mongo_connection() -> None:
    """Gracefully close the Motor client. Called at application shutdown."""
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    """
    Return the active database handle.

    Raises:
        RuntimeError: If called before `connect_to_mongo()`.
    """
    if _client is None:
        raise RuntimeError("Database client is not initialised. Call connect_to_mongo() first.")
    return _client[settings.mongodb_db_name]


# Collection accessors – thin helpers that keep collection names in one place
def get_questions_collection():
    return get_database()["questions"]


def get_sessions_collection():
    return get_database()["user_sessions"]
