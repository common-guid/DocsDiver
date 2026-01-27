
1. the file IMPLEMENTATION_PLAN.md contains the development plan. This file will guide your operations and decisions on development
2. the PROGRESS.md file records the projects progression. The file must be consulted upon any of the following events:
	1. Each time you are prompted by the user review the IMPLEMENTATION_PLAN.md.
	2. Upon beginning a new session always begin by checking the PROGRESS.md file
	3. Prior to starting a new phase of the IMPLEMENTATION_PLAN.md, working on a feature request, or implementing a bug fix.
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
4. Be sure to ask the user any clarifying questions you have about the next step or phase in the execution plan. If you have no questions then proceed with the next section of the plan.
5. review the LOG_BOOK.md file this file will be used to log each of the tasks, outside of the scope of the execution plan, that the agent (you) have completed. For each feature or fix you complete append a new section to the LOG_BOOK.md file in the following format:
```markdown
## name of feature or fix | date of completion
1 or 2 sentence description of the feature or fix.
```
6. whenever possible Dockerize the application and use docker compose. 
7. IF using python: ALWAYS use a python virtual env for python if not in a container.
8. see the llms.txt file for links to the CrewAI documentation pages.
9. See the OUTLINE.md file for a description of the project, and a high-level view of the project and implementation plan spec.
