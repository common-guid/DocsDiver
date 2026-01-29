from __future__ import annotations

import os

from dotenv import load_dotenv


def init_env() -> None:
    load_dotenv()
    log_level = os.getenv("LITELLM_LOG", "").strip()
    if not log_level:
        os.environ["LITELLM_LOG"] = "INFO"
