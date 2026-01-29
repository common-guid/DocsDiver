## Comprehensive README | 2026-01-28
Created a full project README covering architecture, setup/usage, extensibility, testing, and roadmap so new contributors can get started quickly.

## Per-agent model configuration | 2026-01-28
Added `config.yaml` with environment-variable overrides and wired each agent to its own model setting via a shared config loader.

## LiteLLM proxy dependency fix | 2026-01-28
Installed LiteLLM proxy extras in the project venv to resolve missing proxy logging dependencies (fastapi/apscheduler).

## Configurable paths + ToC skip | 2026-01-28
Added app configuration for docs input, ToC output, and artifacts output (with env overrides), and made the Librarian phase skip when a ToC already exists.
