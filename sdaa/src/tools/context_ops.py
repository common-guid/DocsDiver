import os
import logging
from typing import Optional, Any
from sdaa.src.core.config_loader import config_loader

# Attempt to import google-adk types
try:
    from google.adk.sessions import InMemorySessionService
except ImportError:
    InMemorySessionService = None

logger = logging.getLogger(__name__)

class ContextManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ContextManager, cls).__new__(cls)
            cls._instance.service = None
            cls._instance.app_name = None
            cls._instance.user_id = None
            cls._instance.session_id = None
        return cls._instance

    def register_session(self, service: 'InMemorySessionService', app_name: str, user_id: str, session_id: str):
        self.service = service
        self.app_name = app_name
        self.user_id = user_id
        self.session_id = session_id
        logger.info(f"ContextManager registered session: {session_id}")

    def get_active_session(self) -> Optional[Any]:
        if not self.service:
            logger.warning("ContextManager: No session service registered.")
            return None

        # Access internal storage of InMemorySessionService
        # Structure: service.sessions[app_name][user_id][session_id]
        try:
            return self.service.sessions[self.app_name][self.user_id][self.session_id]
        except (KeyError, AttributeError):
            logger.error(f"ContextManager: Session {self.session_id} not found in service.")
            return None

# Singleton instance
context_manager = ContextManager()

def reset_context(summary: str = "") -> str:
    """
    Clears the agent's short-term memory (conversation history) to prevent context overflow.
    It retains the last event (the tool call that triggered this reset) to ensure the
    conversation remains valid (Model Call -> Tool Response).

    Args:
        summary: A brief summary of progress to be returned in the tool response,
                 helping the agent remember its state.
    """
    session = context_manager.get_active_session()
    if not session:
        return "Error: Active session not found. Cannot reset context."

    if not hasattr(session, 'events') or not isinstance(session.events, list):
        return "Error: Session events structure is invalid."

    if not session.events:
        return "Context is already empty."

    # Keep the last event (the tool call) so the runner can append the response correctly
    last_event = session.events[-1]

    # Clear history
    session.events.clear()

    # Restore last event
    session.events.append(last_event)

    msg = "Context reset successfully."
    if summary:
        msg += f" Summary retained: {summary}"
    else:
        msg += " No summary provided."

    return msg

def append_to_notebook(notebook_name: str, content: str) -> str:
    """
    Appends findings to a persistent notebook file.

    Args:
        notebook_name: The name of the notebook (e.g., 'permissions_agent').
                       Use your agent name.
        content: The text content to append.
    """
    artifacts_dir = config_loader.get_artifacts_dir()
    notebooks_dir = os.path.join(artifacts_dir, "notebooks")
    os.makedirs(notebooks_dir, exist_ok=True)

    # Sanitize filename
    safe_name = "".join([c for c in notebook_name if c.isalnum() or c in ('_', '-')])
    filename = f"{safe_name}.md"
    filepath = os.path.join(notebooks_dir, filename)

    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(content + "\n\n")
        return f"Content appended to notebook '{filename}'."
    except Exception as e:
        return f"Error writing to notebook: {str(e)}"

def read_notebook(notebook_name: str) -> str:
    """
    Reads the content of a notebook.

    Args:
        notebook_name: The name of the notebook to read.
    """
    artifacts_dir = config_loader.get_artifacts_dir()

    safe_name = "".join([c for c in notebook_name if c.isalnum() or c in ('_', '-')])
    filename = f"{safe_name}.md"
    filepath = os.path.join(artifacts_dir, "notebooks", filename)

    if not os.path.exists(filepath):
        return f"Notebook '{filename}' does not exist."

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading notebook: {str(e)}"
