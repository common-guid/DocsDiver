# Project Progress

## Phase: Bug Fixes & Improvements | 2026-01-24
Resolved compatibility issues with Python 3.14 and validated the application flow.

### Tasks Completed
- [x] Fixed `langfuse` import crash on Python 3.14 by adding a fallback mechanism in `sdaa/src/core/instrumentation.py`.
- [x] Verified the fix with regression tests in `tests/test_instrumentation.py`.
- [x] Fixed `sdaa/src/core/map_maker.py` which was hardcoding `mock-model`, preventing use of real Gemini models.
- [x] Updated `sdaa/config/config.yaml` to use `gemini-2.5-pro` as the default model, matching available models in the environment.
- [x] Validated application startup and API connectivity by running `main.py -m gemini`.
- [x] Created `scripts/validate_connections.py` to allow users to verify API connectivity (Gemini/OpenRouter).
- [x] Extended `sdaa/src/core/map_maker.py` and `ToC.json` generation to include three keyword tags per file, and updated `tests/test_map_maker.py` to cover the new format.
- [x] Updated worker agent prompts in `sdaa/src/agents/workers.py` so agents explicitly use ToC `tags` when selecting relevant documentation files.

### Next Steps & Continuity
- Verify successful generation of `ToC.json` and full audit workflow.
- Address rate limiting issues if they persist during full audit.
