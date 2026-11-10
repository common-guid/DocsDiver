---
name: dev-logbook
description: Record all code modifications and significant project events in the LOGBOOK.md. Use this after every implementation or bug fix to maintain project history.
---

# Dev Logbook

This skill automates the recording of project modifications to ensure the `LOGBOOK.md` remains a consistent source of truth for "why" changes were made.

## Usage

When you have completed a task or fixed a bug, run the logging script:

```bash
bash .agents/skills/dev-logbook/scripts/log.sh "<Title of the Change>" "<Brief summary of why and what was changed>"
```

The script will automatically:
1. Capture the current date and time.
2. Identify the active Git branch.
3. Format and append the entry to `LOGBOOK.md`.

## Mandatory Protocol

As defined in the project's `AGENTS.md` and `GEMINI.md`, you MUST run `.agents/skills/dev-logbook/scripts/log.sh` via `run_command` after ANY code modification or significant task completion. 

> [!IMPORTANT]
> DO NOT edit `LOGBOOK.md` directly with file editing tools (`replace_file_content` or `write_to_file`). Always execute `bash .agents/skills/dev-logbook/scripts/log.sh "<Title>" "<Summary>"` via `run_command` to maintain canonical formatting, automatic timestamping, and git branch tagging.
