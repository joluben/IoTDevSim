"""
Session Memory Manager
Lightweight in-process session memory with sliding window and TTL.
Redis backup is optional (Epic 4).
"""

import time
import uuid
import structlog
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from threading import Lock

from app.core.config import settings

logger = structlog.get_logger()


@dataclass
class SessionMemory:
    """Memory for a single chat session."""

    session_id: str
    user_id: str
    max_turns: int = settings.SESSION_MAX_TURNS
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    _history: List[Any] = field(default_factory=list)

    def get_history(self) -> List[Any]:
        """Get the message history for PydanticAI agent.run_stream()."""
        self.last_accessed = time.time()
        return list(self._history)

    def add_turn(self, messages: List[Any]):
        """
        Add messages from a completed agent turn.
        Maintains a sliding window of max_turns.
        """
        self.last_accessed = time.time()
        self._history.extend(messages)
        # Keep only the last N turns (each turn ~2 messages: user + assistant)
        max_messages = self.max_turns * 2
        if len(self._history) > max_messages:
            self._history = self._history[-max_messages:]

    @property
    def is_expired(self) -> bool:
        """Check if this session has exceeded its TTL."""
        return (time.time() - self.last_accessed) > settings.SESSION_TTL_SECONDS

    @property
    def turn_count(self) -> int:
        """Approximate number of conversation turns."""
        return len(self._history) // 2


class SessionMemoryManager:
    """
    Manages all active chat sessions.
    In-process dict with LRU eviction and TTL cleanup.
    """

    def __init__(self):
        self._sessions: Dict[str, SessionMemory] = {}
        self._lock = Lock()

    def get_or_create(
        self, session_id: Optional[str], user_id: str
    ) -> SessionMemory:
        """Get an existing session or create a new one."""
        with self._lock:
            # Cleanup expired sessions periodically
            self._cleanup_expired()

            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                if session.user_id != user_id:
                    logger.warning(
                        "Session user_id mismatch — creating new session",
                        session_id=session_id,
                        expected_user=user_id,
                    )
                    session_id = None
                elif session.is_expired:
                    logger.info(
                        "Session expired — creating new session",
                        session_id=session_id,
                    )
                    del self._sessions[session_id]
                    session_id = None
                else:
                    return session

            # Create new session
            new_id = session_id or str(uuid.uuid4())
            session = SessionMemory(session_id=new_id, user_id=user_id)

            # LRU eviction if at capacity
            if len(self._sessions) >= settings.SESSION_MAX_CONCURRENT:
                self._evict_oldest()

            self._sessions[new_id] = session

            logger.info(
                "New session created",
                session_id=new_id,
                user_id=user_id,
                active_sessions=len(self._sessions),
            )
            return session

    def _cleanup_expired(self):
        """Remove expired sessions."""
        expired = [
            sid
            for sid, session in self._sessions.items()
            if session.is_expired
        ]
        for sid in expired:
            del self._sessions[sid]
        if expired:
            logger.debug(
                "Cleaned up expired sessions",
                count=len(expired),
                remaining=len(self._sessions),
            )

    def _evict_oldest(self):
        """Evict the least recently accessed session."""
        if not self._sessions:
            return
        oldest_id = min(
            self._sessions,
            key=lambda sid: self._sessions[sid].last_accessed,
        )
        del self._sessions[oldest_id]
        logger.debug("Evicted oldest session", session_id=oldest_id)

    @property
    def active_count(self) -> int:
        return len(self._sessions)


# Singleton instance
session_manager = SessionMemoryManager()
