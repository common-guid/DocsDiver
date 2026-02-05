from typing import Optional, Any, Dict
from google.adk.sessions import InMemorySessionService, Session
from google.adk.sessions.base_session_service import GetSessionConfig
import logging

logger = logging.getLogger(__name__)

class SharedMemorySessionService(InMemorySessionService):
    """
    A variant of InMemorySessionService that returns references to session objects
    instead of deep copies. This allows tools (like reset_context) to modify
    the active session state (e.g., clearing events) in a way that is visible
    to the Runner loop.

    WARNING: Not thread-safe. Use only in single-threaded event loops.
    """

    def _get_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        if app_name not in self.sessions:
            return None
        if user_id not in self.sessions[app_name]:
            return None
        if session_id not in self.sessions[app_name][user_id]:
            return None

        # Return REFERENCE
        session = self.sessions[app_name][user_id].get(session_id)

        # Note: We ignore 'config.num_recent_events' and 'config.after_timestamp'
        # because enforcing them would require slicing events, which implies a copy.
        # Since we want to modify the master list, we return the full object.
        if config and (config.num_recent_events or config.after_timestamp):
            logger.warning("SharedMemorySessionService ignoring GetSessionConfig filters to preserve reference.")

        # Merge state into the reference (idempotent operation)
        return self._merge_state(app_name, user_id, session)

    def _create_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        # Create using parent logic (which stores it in self.sessions and returns a copy)
        # We accept the overhead of creating a copy we discard, to reuse logic.
        sess_copy = super()._create_session_impl(
            app_name=app_name,
            user_id=user_id,
            state=state,
            session_id=session_id
        )

        # Retrieve and return the stored REFERENCE
        return self.sessions[app_name][user_id][sess_copy.id]
