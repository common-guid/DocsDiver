import os
import logging
from typing import Optional, Any
from langfuse import Langfuse

# Configure logging
logger = logging.getLogger(__name__)

class PromptManager:
    _instance = None
    _client: Optional[Langfuse] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
            cls._instance._initialize_client()
        return cls._instance

    def _initialize_client(self):
        """Initialize the Langfuse client if API keys are present."""
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        
        if public_key and secret_key:
            try:
                self._client = Langfuse()
                logger.info("Langfuse client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse client: {e}")
                self._client = None
        else:
            logger.warning("Langfuse credentials not found. Prompt management will be disabled.")
            self._client = None

    def get_prompt_object(self, name: str, label: str = "production", type: str = "text") -> Any:
        """
        Fetch the raw prompt object from Langfuse.

        Args:
            name: The name of the prompt in Langfuse.
            label: The version label (default: "production").
            type: The type of prompt ("text" or "chat").

        Returns:
            The Langfuse prompt object, or None if retrieval fails.
        """
        if not self._client:
            logger.warning(f"Langfuse client not available. Cannot fetch prompt '{name}'.")
            return None

        try:
            return self._client.get_prompt(name, label=label, type=type)
        except Exception as e:
            logger.error(f"Error fetching prompt object '{name}': {e}")
            return None

    def get_prompt(self, name: str, label: str = "production", type: str = "text", **kwargs) -> str:
        """
        Fetch a prompt from Langfuse and compile it.
        
        Args:
            name: The name of the prompt in Langfuse.
            label: The version label (default: "production").
            type: The type of prompt ("text" or "chat").
            **kwargs: Variables to compile into the prompt.
            
        Returns:
            The compiled prompt string, or an empty string/fallback if retrieval fails.
        """
        prompt_obj = self.get_prompt_object(name, label=label, type=type)

        if not prompt_obj:
            return ""

        try:
            # Compile with variables
            return prompt_obj.compile(**kwargs)
        except Exception as e:
            logger.error(f"Error compiling prompt '{name}': {e}")
            return ""

# Global instance
prompt_manager = PromptManager()
