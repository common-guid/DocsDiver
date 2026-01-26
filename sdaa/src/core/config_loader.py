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

    def get_output_dir(self) -> str:
        """Resolve the configured output directory and ensure it exists.

        Returns the absolute path to the directory where SDAA should write
        generated artifacts such as ToC.json and Security_Threat_Model.md.
        """
        raw_path = self.get("system.output_dir", ".")
        if not raw_path:
            raw_path = "."

        # Expand user (~) and make absolute if needed
        path = os.path.expanduser(raw_path)
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        os.makedirs(path, exist_ok=True)
        return path

    def get_reports_dir(self) -> str:
        """Resolve the configured reports directory and ensure it exists.

        Returns the absolute path to output/reports/.
        """
        output_dir = self.get_output_dir()
        reports_name = self.get("system.reports_dir", "reports")
        path = os.path.join(output_dir, reports_name)
        os.makedirs(path, exist_ok=True)
        return path

    def get_artifacts_dir(self) -> str:
        """Resolve the configured artifacts directory and ensure it exists.

        Returns the absolute path to output/artifacts/.
        """
        output_dir = self.get_output_dir()
        artifacts_name = self.get("system.artifacts_dir", "artifacts")
        path = os.path.join(output_dir, artifacts_name)
        os.makedirs(path, exist_ok=True)
        return path

# Singleton access
config_loader = ConfigLoader()
