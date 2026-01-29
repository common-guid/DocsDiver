from src.bootstrap_env import init_env

init_env()

from crewai import Task

class AuditTasks:
    def supervisor_orchestration_task(self, agent, toc_context: str):
        return Task(
            description=(
                f"REVIEW the following Table of Contents (ToC) carefully:\n\n"
                f"{toc_context}\n\n"
                "1. Based on the tags and summaries, DELEGATE analysis tasks to your workers.\n"
                "2. Instruct workers to look for specific risks relevant to the file contents.\n"
                "3. WAIT for their results.\n"
                "4. COMPILE the 'FINAL_AUDIT_REPORT.md' with an Executive Summary and a table of findings."
            ),
            expected_output="A comprehensive Markdown report named 'FINAL_AUDIT_REPORT.md' containing Executive Summary, Methodology, and Aggregated Findings.",
            agent=agent
        )

    def negative_constraints_analysis(self, agent):
        return Task(
            description=(
                "Scan the assigned documentation files for 'Negative Constraints'. "
                "Look for features that lack exclusion logic (e.g., 'Uploads allowed' without 'No .exe'). "
                "Use the SearchTool to find keywords like 'limit', 'prevent', 'restrict', 'not allowed'."
            ),
            expected_output=(
                "A list of findings. EACH finding must be strictly formatted as: "
                "[SEVERITY] : [FILENAME] : [ISSUE] : [CONTEXT_QUOTE]"
            ),
            agent=agent,
            async_execution=True # Worker runs in parallel
        )

    def permissions_analysis(self, agent):
        return Task(
            description=(
                "Scan the assigned documentation files for Permissions/RBAC issues. "
                "Identify undefined roles, mixed privileges, or weak authorization checks."
            ),
            expected_output=(
                "A list of findings. EACH finding must be strictly formatted as: "
                "[SEVERITY] : [FILENAME] : [ISSUE] : [CONTEXT_QUOTE]"
            ),
            agent=agent,
            async_execution=True # Worker runs in parallel
        )

    def boundaries_analysis(self, agent):
        return Task(
            description=(
                "Scan the assigned documentation files for System Boundaries. "
                "Identify missing rate limits, retention policies, or input size limits."
            ),
            expected_output=(
                "A list of findings. EACH finding must be strictly formatted as: "
                "[SEVERITY] : [FILENAME] : [ISSUE] : [CONTEXT_QUOTE]"
            ),
            agent=agent,
            async_execution=True # Worker runs in parallel
        )
