import os
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class KeyRotator:
    """
    Manages a list of API keys and rotates them on demand.
    """
    def __init__(self, provider_name: str, env_var_name: str):
        self.provider_name = provider_name
        self.env_var_name = env_var_name
        self.keys: List[str] = self._load_keys()
        self._current_index = 0

    def _load_keys(self) -> List[str]:
        """Loads keys from the environment variable, comma-separated."""
        raw_keys = os.getenv(self.env_var_name, "")
        keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        if not keys:
            logger.warning(f"No API keys found for {self.provider_name} in {self.env_var_name}")
            return []
        if len(keys) > 1:
            logger.info(f"Loaded {len(keys)} keys for {self.provider_name}")
        return keys

    def get_current_key(self) -> Optional[str]:
        """Returns the currently active key."""
        if not self.keys:
            return None
        return self.keys[self._current_index]

    def rotate_key(self) -> str:
        """
        Rotates to the next key in the list.
        Returns the new key.
        """
        if not self.keys:
            raise ValueError(f"No keys available for {self.provider_name}")

        old_index = self._current_index
        self._current_index = (self._current_index + 1) % len(self.keys)
        logger.info(f"Rotated {self.provider_name} key from index {old_index} to {self._current_index}")
        return self.keys[self._current_index]

    def get_key_count(self) -> int:
        return len(self.keys)


# Singleton instances
_rotators = {}

def get_key_rotator(provider_name: str) -> KeyRotator:
    """
    Factory method to get or create a KeyRotator for a given provider.
    Supported providers: 'openrouter', 'gemini'
    """
    if provider_name not in _rotators:
        if provider_name == "openrouter":
            _rotators[provider_name] = KeyRotator("openrouter", "OPENROUTER_API_KEY")
        elif provider_name == "gemini":
            _rotators[provider_name] = KeyRotator("gemini", "GEMINI_API_KEY")
        else:
            raise ValueError(f"Unknown provider for key rotation: {provider_name}")

    return _rotators[provider_name]
