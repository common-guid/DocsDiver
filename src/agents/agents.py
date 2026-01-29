from src.bootstrap_env import init_env

init_env()

from crewai import Agent
from src.tools.file_tools import ListFilesTool, ReadFileTool, SearchFilesTool
from src.config.llm_config import (
    get_boundaries_llm,
    get_negative_constraints_llm,
    get_permissions_llm,
    get_supervisor_llm,
)

class AuditAgents:
    def __init__(self):
        # Instantiate tools once to pass to workers
        self.file_tools = [ListFilesTool(), ReadFileTool(), SearchFilesTool()]

        # Load distinct LLMs
        self.supervisor_llm = get_supervisor_llm()
        self.negative_constraints_llm = get_negative_constraints_llm()
        self.permissions_llm = get_permissions_llm()
        self.boundaries_llm = get_boundaries_llm()

    def supervisor_agent(self) -> Agent:
        return Agent(
            role='Audit Supervisor',
            goal='Orchestrate a comprehensive security audit by delegating tasks based on the Table of Contents.',
            backstory=(
                "You are an expert Security Architect. You do not read files directly. "
                "Instead, you review the provided Table of Contents (ToC) and assign "
                "specific investigation tasks to your specialized workers. "
                "You are responsible for compiling their findings into a final report."
            ),
            allow_delegation=True,
            verbose=True,
            llm=self.supervisor_llm,
            tools=[] # CRITICAL: No file tools. Must delegate.
        )

    def negative_constraints_agent(self) -> Agent:
        return Agent(
            role='Negative Constraints Analyst',
            goal='Identify missing "Negative Constraints" (what the system should NOT do).',
            backstory=(
                "You look for logic gaps where the documentation fails to specify preventions. "
                "Example: 'The system allows file uploads' (but doesn't say 'executable files are forbidden')."
            ),
            allow_delegation=False,
            verbose=True,
            llm=self.negative_constraints_llm,
            tools=self.file_tools
        )

    def permissions_agent(self) -> Agent:
        return Agent(
            role='Permissions Analyst',
            goal='Verify RBAC models and permission consistency.',
            backstory=(
                "You analyze authentication and authorization flows. "
                "You look for vague roles (e.g., 'Admin') without definition, or mixed-up user privileges."
            ),
            allow_delegation=False,
            verbose=True,
            llm=self.permissions_llm,
            tools=self.file_tools
        )

    def boundaries_agent(self) -> Agent:
        return Agent(
            role='Boundaries Analyst',
            goal='Check for system limits and data boundaries.',
            backstory=(
                "You look for defined limits: API rate limits, file size limits, data retention policies, "
                "and input character limits. Lack of these is a finding."
            ),
            allow_delegation=False,
            verbose=True,
            llm=self.boundaries_llm,
            tools=self.file_tools
        )
