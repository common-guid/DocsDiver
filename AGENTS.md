
1. the file EXECUTION_PLAN.md contains the development plan. This file will guide your operations and decisions on development
2. the PROGRESS.md file records the projects progression. The file must be consulted upon any of the following events:
	1. Upon beginning a new session always begin by checking the PROGRESS.md file
	2. Prior to starting a new session, working on a feature request, or implementing a bug fix.
3. after completing each feature or fix assigned to you you must update the PROGRESS.md file with a summary of the actions taken and accomplishments. Include your intended next steps for continuity between sessions. 
3. after completing each step from the IMPLEMENTATION_PLAN.md stop execution and update the PROGRESS.md file with a summary of your actions for the completion of the step or phase. Include your intended next steps for continuity between sessions. 
```markdown
# Project Progress

## Phase 1 <title> | <date>
<phase summary>
<execution plan tasks completed>

### Next Steps & Continuity

## Phase 2 <title> | <date>
...

## Outstanding
<running list of any items that were deferred or skipped during phase execution. cross out or strikethrough items when completed>
```
4. Be sure to ask the user any clarifying questions you have about the task. If you have no questions then proceed with execution of the plan.
5. the LOG_BOOK.md file will be used to log each task, feature, or bug fix you complete. For each feature or fix you complete append a new section to the LOG_BOOK.md file in the following format:
```markdown
## name of feature or fix | date of completion
1 or 2 sentence description of the feature or fix.
```
6. whenever possible Dockerize the application and use docker compose. 
7. IF using python: ALWAYS use a python virtual env for python if not in a container.
8. References:
  - llms.txt - links to the ADK python SDK documentation
  - llms-langchain-langsmith.txt - llms.txt contains links to documentation for the langchain framework and langsmith observability platform.
  - llms-langfuse.txt - llms.txt contains links to documentation for the langfuse observability platform.
