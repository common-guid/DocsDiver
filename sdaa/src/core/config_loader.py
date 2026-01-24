import os
import yaml
from dotenv import load_dotenv

load_dotenv()

class ConfigLoader:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), '../../../sdaa/config/config.yaml')
        config_path = os.path.abspath(config_path)

        if not os.path.exists(config_path):
             # Fallback for when running from root or different relative paths
             config_path = 'sdaa/config/config.yaml'

        try:
            with open(config_path, 'r') as f:
                self._config = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at {config_path}")

    @property
    def config(self):
        return self._config

    def get(self, path, default=None):
        keys = path.split('.')
        value = self._config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

# Singleton access
config_loader = ConfigLoader()
