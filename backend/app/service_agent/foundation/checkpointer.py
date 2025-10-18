"""
Checkpointer management module
Provides checkpoint functionality for state persistence using AsyncPostgresSaver
"""

import logging
from pathlib import Path
from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.service_agent.foundation.config import Config

logger = logging.getLogger(__name__)


class CheckpointerManager:
    """
    Manages checkpoint creation and retrieval using AsyncPostgresSaver
    """

    def __init__(self):
        """Initialize the checkpointer manager"""
        self.checkpoint_dir = Config.CHECKPOINT_DIR  # Kept for backward compatibility
        self._checkpointers = {}  # Cache for checkpointer instances
        self._context_managers = {}  # Cache for async context managers
        logger.info(f"CheckpointerManager initialized with PostgreSQL")

    def _ensure_checkpoint_dir_exists(self):
        """Ensure the checkpoint directory exists"""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def get_checkpoint_path(self, agent_name: str, session_id: str) -> Path:
        """
        Get the checkpoint database path for a specific agent and session

        Args:
            agent_name: Name of the agent
            session_id: Session identifier

        Returns:
            Path to the checkpoint database file
        """
        return Config.get_checkpoint_path(agent_name, session_id)

    async def create_checkpointer(self, db_path: Optional[str] = None) -> AsyncPostgresSaver:
        """
        Create and setup an AsyncPostgresSaver checkpointer instance

        Args:
            db_path: Not used for PostgreSQL (kept for backward compatibility)

        Returns:
            AsyncPostgresSaver instance

        Raises:
            Exception: If checkpointer setup fails
        """
        # Get PostgreSQL connection string from settings
        from app.core.config import settings
        conn_string = settings.DATABASE_URL

        # Check cache
        if conn_string in self._checkpointers:
            logger.debug(f"Returning cached checkpointer for PostgreSQL")
            return self._checkpointers[conn_string]

        logger.info(f"Creating AsyncPostgresSaver checkpointer")

        try:
            # AsyncPostgresSaver.from_conn_string returns an async context manager
            # We need to enter the context and keep it alive
            context_manager = AsyncPostgresSaver.from_conn_string(conn_string)

            # Enter the async context manager
            actual_checkpointer = await context_manager.__aenter__()

            # Setup PostgreSQL tables (creates checkpoints, checkpoint_blobs, checkpoint_writes)
            await actual_checkpointer.setup()

            # Cache both the checkpointer and context manager (to keep it alive)
            self._checkpointers[conn_string] = actual_checkpointer
            self._context_managers[conn_string] = context_manager

            logger.info(f"AsyncPostgresSaver checkpointer created and setup successfully")
            return actual_checkpointer

        except Exception as e:
            logger.error(f"Failed to create checkpointer: {e}", exc_info=True)
            raise

    async def close_checkpointer(self, db_path: Optional[str] = None):
        """
        Close a checkpointer and its context manager properly

        Args:
            db_path: Not used for PostgreSQL (kept for backward compatibility)
        """
        from app.core.config import settings
        conn_string = settings.DATABASE_URL

        if conn_string in self._context_managers:
            try:
                context_manager = self._context_managers[conn_string]
                await context_manager.__aexit__(None, None, None)
                logger.info(f"Checkpointer closed for PostgreSQL")
            except Exception as e:
                logger.error(f"Error closing checkpointer: {e}")
            finally:
                # Clean up cache
                self._context_managers.pop(conn_string, None)
                self._checkpointers.pop(conn_string, None)

    async def close_all(self):
        """Close all open checkpointers"""
        for conn_string in list(self._context_managers.keys()):
            try:
                context_manager = self._context_managers[conn_string]
                await context_manager.__aexit__(None, None, None)
                logger.info(f"Checkpointer closed: {conn_string}")
            except Exception as e:
                logger.error(f"Error closing checkpointer: {e}")
            finally:
                self._context_managers.pop(conn_string, None)
                self._checkpointers.pop(conn_string, None)

    def validate_checkpoint_setup(self) -> bool:
        """
        Validate that the checkpoint system is properly configured

        Returns:
            True if everything is set up correctly
        """
        from app.core.config import settings

        checks = []

        # Check DATABASE_URL is configured
        if not settings.DATABASE_URL:
            checks.append("DATABASE_URL not configured in .env")

        # Check DATABASE_URL format (must be PostgreSQL)
        if settings.DATABASE_URL and not settings.DATABASE_URL.startswith("postgresql"):
            checks.append(f"DATABASE_URL must start with 'postgresql://' or 'postgresql+psycopg://': {settings.DATABASE_URL}")

        if checks:
            for check in checks:
                logger.error(check)
            return False

        logger.info("Checkpoint setup validation passed (PostgreSQL)")
        return True


# Module-level singleton instance
_checkpointer_manager = None


def get_checkpointer_manager() -> CheckpointerManager:
    """
    Get the singleton CheckpointerManager instance

    Returns:
        CheckpointerManager singleton instance
    """
    global _checkpointer_manager
    if _checkpointer_manager is None:
        _checkpointer_manager = CheckpointerManager()
    return _checkpointer_manager


async def create_checkpointer(db_path: Optional[str] = None) -> AsyncPostgresSaver:
    """
    Convenience function to create a checkpointer

    Args:
        db_path: Not used for PostgreSQL (kept for backward compatibility)

    Returns:
        AsyncPostgresSaver instance
    """
    manager = get_checkpointer_manager()
    return await manager.create_checkpointer(db_path)