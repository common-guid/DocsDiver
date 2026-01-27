## phase 1
### Finalized Phase 1 Implementation Plan: Custom File Tools

Based on your confirmation—**simple text search** and **strict `.md` support**—here is the locked-in implementation for Phase 1.

#### 1. Objective

Build the I/O layer that allows agents to navigate the file system. These tools will be imported by the Supervisor and Worker agents in Phase 3.

#### 2. Directory & Dependencies

* **File Path:** `src/tools/file_tools.py`
* **Dependencies:** Ensure your `requirements.txt` includes:
```text
crewai
crewai-tools
pydantic

```



#### 3. Final Code Implementation

This code includes the **Context-Aware logic** (3 lines before/after) required by the QC strategy, strictly limited to `.md` files and simple string matching.

**File:** `src/tools/file_tools.py`

```python
import os
from typing import List, Type
from pydantic import BaseModel, Field
from crewai_tools import BaseTool

# --- 1. List Files Tool ---
class ListFilesToolInput(BaseModel):
    directory: str = Field(..., description="The absolute or relative path to the directory to list files from.")

class ListFilesTool(BaseTool):
    name: str = "List Markdown Files"
    description: str = (
        "Recursively lists all file paths ending in .md in a given directory. "
        "Useful for discovering the documentation structure before reading specific files."
    )
    args_schema: Type[BaseModel] = ListFilesToolInput

    def _run(self, directory: str) -> List[str]:
        md_files = []
        if not os.path.exists(directory):
            return [f"Error: Directory '{directory}' does not exist."]

        for root, dirs, files in os.walk(directory):
            for file in files:
                # CONSTRAINT CHECK: Strict .md only
                if file.endswith(".md"):
                    full_path = os.path.join(root, file)
                    md_files.append(full_path)
        
        return md_files if md_files else [f"No .md files found in {directory}"]

# --- 2. Read File Tool ---
class ReadFileToolInput(BaseModel):
    file_path: str = Field(..., description="The full path of the markdown file to read.")

class ReadFileTool(BaseTool):
    name: str = "Read Markdown File"
    description: str = (
        "Reads the complete content of a specified markdown file. "
        "Use this to analyze the full context of a document found via ListFiles."
    )
    args_schema: Type[BaseModel] = ReadFileToolInput

    def _run(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' not found."
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

# --- 3. Search Files Tool (Context-Aware) ---
class SearchFilesToolInput(BaseModel):
    query: str = Field(..., description="The keyword or phrase to search for.")
    directory: str = Field(..., description="The directory to search within.")

class SearchFilesTool(BaseTool):
    name: str = "Search Files with Context"
    description: str = (
        "Searches for a keyword across all .md files in a directory. "
        "Returns the file path, line number, and a snippet of text (3 lines before and after) "
        "to provide context for the match."
    )
    args_schema: Type[BaseModel] = SearchFilesToolInput

    def _run(self, query: str, directory: str) -> str:
        results = []
        if not os.path.exists(directory):
            return f"Error: Directory '{directory}' does not exist."

        # CONSTRAINT CHECK: Simple text search (no regex)
        query_lower = query.lower()

        for root, dirs, files in os.walk(directory):
            for file in files:
                # CONSTRAINT CHECK: Strict .md only
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            
                        for i, line in enumerate(lines):
                            if query_lower in line.lower(): 
                                # LOGIC: Capture 3 lines before and 4 lines after (slice exclusive)
                                start_index = max(0, i - 3)
                                end_index = min(len(lines), i + 4) 
                                
                                snippet_lines = []
                                for j in range(start_index, end_index):
                                    # Visual marker for the exact match line
                                    prefix = ">> " if j == i else "   " 
                                    snippet_lines.append(f"{prefix}Line {j+1}: {lines[j].strip()}")
                                
                                snippet_block = "\n".join(snippet_lines)
                                
                                results.append(
                                    f"Found in: {file_path}\n"
                                    f"Context:\n{snippet_block}\n"
                                    f"{'-'*40}"
                                )
                    except Exception as e:
                        results.append(f"Could not read {file_path}: {str(e)}")

        if not results:
            return f"No matches found for '{query}' in {directory}."
            
        return "\n\n".join(results)

```

#### 4. Verification Step (Unit Test)

Before moving to Phase 2, verify these tools work without the agents. Create a temporary `test_tools.py`:

```python
from src.tools.file_tools import ListFilesTool, ReadFileTool, SearchFilesTool

# 1. Setup
list_tool = ListFilesTool()
read_tool = ReadFileTool()
search_tool = SearchFilesTool()

# 2. Test
print("--- List Files ---")
files = list_tool._run("./docs") # Ensure you have a dummy ./docs folder
print(files)

print("\n--- Search 'password' ---")
results = search_tool._run("password", "./docs")
print(results)

```
## phase 2
This phase focuses on the "Librarian" pre-processing script. Per your specific requests, we will use **Gemini 2 Flash** (via `litellm`), process files **sequentially** for simplicity, and output the required `ToC.json`.

### **Phase 2: Implementation**

#### 1. Dependencies

Update your `requirements.txt` to ensure `litellm` is explicitly listed (CrewAI installs it, but this script runs independently).

```text
crewai
crewai-tools
pydantic
litellm
google-generativeai # Required for Gemini interactions

```

#### 2. The Librarian Script (`src/utils/toc_generator.py`)

This script acts as the "Librarian." It walks the directory, reads each markdown file, and sends it to **Gemini 2 Flash** to extract the summary and tags.

**Key Features:**

* **Model:** Defaults to `gemini/gemini-2.0-flash` (configurable).
* **Robustness:** Uses a `try/except` loop so one bad file doesn't crash the generation.
* **Output validation:** Strips markdown code blocks (```json) often returned by LLMs to ensure valid JSON parsing.

```python
import os
import json
from typing import List, Dict
from litellm import completion

class ToCGenerator:
    def __init__(self, root_dir: str, model_name: str = "gemini/gemini-2.0-flash"):
        self.root_dir = root_dir
        self.model_name = model_name
        self.toc_data: List[Dict] = []

    def _get_files(self) -> List[str]:
        """Recursively find all .md files."""
        md_files = []
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if file.endswith(".md"):
                    md_files.append(os.path.join(root, file))
        return md_files

    def _generate_summary(self, file_path: str, content: str) -> Dict:
        """Calls Gemini 2 Flash to summarize the content."""
        
        prompt = f"""
        You are a Technical Librarian. Analyze the following documentation file.
        
        FILE PATH: {file_path}
        
        CONTENT:
        {content[:4000]}  # Truncate to first 4k chars to save tokens/time if files are huge
        
        ---
        Your Goal:
        1. Write a 1-sentence summary of what this file covers.
        2. Assign 2-5 relevant tags (e.g., "auth", "payment", "user-input", "logging").
        
        Return strictly JSON in this format:
        {{
            "summary": "The summary text here.",
            "tags": ["tag1", "tag2"]
        }}
        """

        try:
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1 # Low temp for consistent JSON
            )
            
            content_str = response.choices[0].message.content
            
            # Clean up potential markdown formatting (```json ... ```)
            content_str = content_str.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(content_str)
            return data
        except Exception as e:
            print(f"xx Failed to process {file_path}: {e}")
            return {"summary": "Error processing file.", "tags": ["error"]}

    def generate(self):
        print(f"📚 Librarian starting scan of: {self.root_dir}")
        print(f"🤖 Using Model: {self.model_name}")
        
        files = self._get_files()
        print(f"found {len(files)} markdown files.")

        for file_path in files:
            print(f"   ... processing: {os.path.basename(file_path)}")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                meta = self._generate_summary(file_path, content)
                
                # Append to Master Record
                self.toc_data.append({
                    "file": os.path.basename(file_path),
                    "path": file_path,
                    "summary": meta.get("summary", "No summary"),
                    "tags": meta.get("tags", [])
                })
            except Exception as e:
                print(f"xx Critical error reading {file_path}: {e}")

        # Save to Disk
        output_path = "ToC.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.toc_data, f, indent=2)
        
        print(f"✅ ToC generated! Saved to {output_path}")

# Standalone execution for testing
if __name__ == "__main__":
    # Ensure GEMINI_API_KEY is set in your environment
    generator = ToCGenerator(root_dir="./docs") # Default to ./docs
    generator.generate()

```

#### 3. Verification Steps

Before moving to Phase 3, you should run this script manually to confirm it produces a valid `ToC.json`.

1. Create a dummy folder `./docs/` and add `auth.md` (content: "Users log in using OAuth2...").
2. Set your environment variable: `export GEMINI_API_KEY=your_key_here`.
3. Run the script: `python src/utils/toc_generator.py`.
4. Check `ToC.json`. It should look like:
```json
[
  {
    "file": "auth.md",
    "path": "./docs/auth.md",
    "summary": "Overview of the OAuth2 login flow.",
    "tags": ["auth", "security"]
  }
]

```

## phase 3

### **Phase 3: Implementation**

#### **1. Directory Setup**

Ensure your `src` folder structure includes these new files:

```text
src/
├── agents/
│   ├── __init__.py
│   ├── agents.py       # Agent Definitions
│   └── tasks.py        # Task Definitions
├── config/
│   └── llm_config.py   # Centralized Model Configuration
└── main.py             # Updated Orchestrator

```

#### **2. LLM Configuration (`src/config/llm_config.py`)**

This file manages the "Independent Configurable LLM" requirement. It ensures you can swap models easily without touching the agent logic.

```python
import os
from crewai import LLM

# Define your specific model names here
SUPERVISOR_MODEL_NAME = "gpt-4o" 
WORKER_MODEL_NAME = "gemini/gemini-2.0-flash" 

def get_supervisor_llm():
    """Returns the high-reasoning LLM for the Supervisor."""
    return LLM(model=SUPERVISOR_MODEL_NAME)

def get_worker_llm():
    """Returns the fast/efficient LLM for Worker agents."""
    return LLM(model=WORKER_MODEL_NAME)

```

#### **3. Agent Definitions (`src/agents/agents.py`)**

Here we enforce the **Tool Access Constraint**: The Supervisor gets `tools=[]`, while Workers get the File Tools.

```python
from crewai import Agent
from src.tools.file_tools import ListFilesTool, ReadFileTool, SearchFilesTool
from src.config.llm_config import get_supervisor_llm, get_worker_llm

class AuditAgents:
    def __init__(self):
        # Instantiate tools once to pass to workers
        self.file_tools = [ListFilesTool(), ReadFileTool(), SearchFilesTool()]
        
        # Load distinct LLMs
        self.supervisor_llm = get_supervisor_llm()
        self.worker_llm = get_worker_llm()

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
            llm=self.worker_llm,
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
            llm=self.worker_llm,
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
            llm=self.worker_llm,
            tools=self.file_tools
        )

```

#### **4. Task Definitions (`src/agents/tasks.py`)**

This file handles the **Task Logic**, including the **Async Execution** and **Strict Output Formatting**.

```python
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

```

#### **5. Updated Orchestrator (`src/main.py`)**

This script brings it all together, adding the **Token Check** and the **ToC Injection**.

```python
import os
import sys
from crewai import Crew, Process
from src.utils.toc_generator import ToCGenerator
from src.agents.agents import AuditAgents
from src.agents.tasks import AuditTasks

# Configuration
DOCS_DIR = "./docs"
TOC_FILE = "ToC.json"

def check_token_limit(content: str, threshold: int = 500000):
    """
    Estimates token count (approx 4 chars per token).
    Alerts user if content exceeds the threshold.
    """
    estimated_tokens = len(content) / 4
    if estimated_tokens > threshold:
        print(f"\n⚠️  ALERT: ToC size ({int(estimated_tokens)} tokens) exceeds safety threshold of {threshold}!")
        print("    Proceeding, but context window truncation may occur.\n")
    else:
        print(f"ℹ️  ToC Context Size: ~{int(estimated_tokens)} tokens (Safe)")

def main():
    # 1. Phase 2: Run Librarian (ToC Generation)
    print("## 1. Running Librarian Pre-processing...")
    if not os.path.exists(DOCS_DIR):
        print(f"Error: Directory {DOCS_DIR} not found.")
        sys.exit(1)
        
    toc_gen = ToCGenerator(root_dir=DOCS_DIR)
    toc_gen.generate()

    # 2. Load ToC Context
    print("## 2. Loading Context...")
    try:
        with open(TOC_FILE, "r", encoding="utf-8") as f:
            toc_content = f.read()
    except FileNotFoundError:
        print("Error: ToC.json was not generated.")
        sys.exit(1)

    # 3. Token Safety Check
    check_token_limit(toc_content)

    # 4. Phase 3: Initialize Agents & Tasks
    print("## 3. Initializing Crew...")
    agents = AuditAgents()
    tasks = AuditTasks()

    # Instantiate Agents
    supervisor = agents.supervisor_agent()
    neg_agent = agents.negative_constraints_agent()
    perm_agent = agents.permissions_agent()
    bound_agent = agents.boundaries_agent()

    # Instantiate Tasks
    # Note: Worker tasks are generic templates here; 
    # The Supervisor will delegate specific sub-tasks dynamically, 
    # but providing these templates helps ground the workers' behavior.
    
    # We define the Supervisor's task with the injected ToC
    supervisor_task = tasks.supervisor_orchestration_task(supervisor, toc_content)

    # 5. Define Crew (Hierarchical)
    doc_audit_crew = Crew(
        agents=[neg_agent, perm_agent, bound_agent],
        manager_agent=supervisor,
        tasks=[supervisor_task], # Supervisor delegates to the others
        process=Process.hierarchical,
        verbose=True,
        planning=True,            # Optional: helps Supervisor break down the ToC
        memory=True               # Helps agents remember findings across files
    )

    # 6. Kickoff
    print("## 4. Starting Audit...")
    result = doc_audit_crew.kickoff()
    
    print("\n\n########################")
    print("## AUDIT COMPLETE ##")
    print("########################\n")
    print(result)

if __name__ == "__main__":
    main()

```

### **Phase 3 Verification Checklist**

Before moving to QC/Testing:

1. **Configure `.env`:** Ensure `OPENAI_API_KEY` (for Supervisor) and `GEMINI_API_KEY` (for Workers) are set.
2. **Verify Imports:** Ensure `src.tools.file_tools` is accessible to `src.agents.agents`.
3. **Run `main.py`:** It should generate the ToC, print the token count (~100 tokens for a small test), and then start the Crew loop.
## phase 4

### **Refined Phase 4 Implementation Spec**

Here is the finalized `src/main.py` incorporating these improvements.

```python
import os
import sys
import argparse
from crewai import Crew, Process
from src.utils.toc_generator import ToCGenerator
from src.agents.agents import AuditAgents
from src.agents.tasks import AuditTasks

def parse_args():
    parser = argparse.ArgumentParser(description="DocsDiver-Crew CLI")
    parser.add_argument(
        "--dir", 
        type=str, 
        default="./docs", 
        help="Path to the documentation directory (default: ./docs)"
    )
    return parser.parse_args()

def validate_environment(target_dir):
    """Fail fast if keys or dirs are missing."""
    # 1. Check Directory
    if not os.path.exists(target_dir):
        print(f"❌ Error: Directory '{target_dir}' does not exist.")
        sys.exit(1)
    
    # 2. Check Keys (Add others if needed)
    required_keys = ["OPENAI_API_KEY", "GEMINI_API_KEY"]
    missing = [key for key in required_keys if key not in os.environ]
    if missing:
        print(f"❌ Error: Missing environment variables: {', '.join(missing)}")
        print("   Please set them in your .env file or terminal session.")
        sys.exit(1)
    
    print("✅ Environment checks passed.")

def check_token_limit(content: str, threshold: int = 500000):
    estimated_tokens = len(content) / 4
    if estimated_tokens > threshold:
        print(f"\n⚠️  ALERT: ToC size ({int(estimated_tokens)} tokens) exceeds threshold!")
    else:
        print(f"ℹ️  ToC Context Size: ~{int(estimated_tokens)} tokens (Safe)")

def main():
    args = parse_args()
    DOCS_DIR = args.dir
    TOC_FILE = "ToC.json"

    print(f"\n🚀 Starting DocsDiver on: {DOCS_DIR}\n" + "="*40)
    validate_environment(DOCS_DIR)

    # --- Phase 2: Librarian ---
    print("\n## 1. Running Librarian (ToC Generator)...")
    toc_gen = ToCGenerator(root_dir=DOCS_DIR)
    toc_gen.generate()

    # Load ToC
    try:
        with open(TOC_FILE, "r", encoding="utf-8") as f:
            toc_content = f.read()
    except FileNotFoundError:
        print("❌ Error: ToC.json generation failed.")
        sys.exit(1)

    check_token_limit(toc_content)

    # --- Phase 3: Crew Setup ---
    print("\n## 2. Initializing Agents & Tasks...")
    agents = AuditAgents()
    tasks = AuditTasks()

    # Instantiate Agents
    supervisor = agents.supervisor_agent()
    neg_agent = agents.negative_constraints_agent()
    perm_agent = agents.permissions_agent()
    bound_agent = agents.boundaries_agent()

    # Instantiate Tasks
    supervisor_task = tasks.supervisor_orchestration_task(supervisor, toc_content)
    
    # We assign worker tasks to the crew structure, 
    # but the Supervisor will dynamically delegate to them.
    # (CrewAI Hierarchical processes usually auto-assign, 
    # but defining them here ensures the specialized tasks exist).
    
    doc_audit_crew = Crew(
        agents=[neg_agent, perm_agent, bound_agent],
        manager_agent=supervisor,
        tasks=[supervisor_task], 
        process=Process.hierarchical,
        verbose=True,
        planning=True,
        memory=True
    )

    # --- Execution ---
    print("\n## 3. Kicking off Audit Crew (this may take time)...")
    try:
        result = doc_audit_crew.kickoff()
    except Exception as e:
        print(f"\n❌ Crew Execution Failed: {e}")
        sys.exit(1)

    # --- Phase 4: Output Handling ---
    print("\n## 4. Saving Report...")
    output_filename = "FINAL_AUDIT_REPORT.md"
    
    # Convert result to string if it's a CrewOutput object
    final_content = str(result) 
    
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(f"✅ Success! Report saved to: {os.path.abspath(output_filename)}")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()

```

## phase 5

### **Phase 5: Implementation**

#### **1. Directory Structure for Testing**

Create the following structure inside your project root:

```text
tests/
├── fixtures/               # Where we generate "Bad Docs"
├── unit/
│   ├── __init__.py
│   └── test_tools.py       # Mocked tests for File I/O
├── integration/
│   ├── __init__.py
│   └── test_full_audit.py  # The "Automated Grader" script
└── generate_fixtures.py    # Script to reset the test environment

```

---

#### **2. Fixture Generator (`tests/generate_fixtures.py`)**

This script creates a controlled environment with known vulnerabilities. We inject **Canary Tokens** (e.g., `[CANARY-AUTH-01]`) directly into the text.

```python
import os

FIXTURE_DIR = "./tests/fixtures/vulnerable_docs"

def create_fixtures():
    if not os.path.exists(FIXTURE_DIR):
        os.makedirs(FIXTURE_DIR)

    # 1. Vulnerable Auth Doc (Permissions Agent Target)
    auth_content = """
    # Authentication System
    
    The system uses basic JWT tokens.
    
    ## User Roles
    * **Admin**: Full access.
    * **User**: Standard access.
    * **Guest**: Read-only.
    
    ## Password Policy
    To ensure ease of use, there is **no maximum retry limit** on password attempts. 
    (Ref: [CANARY-AUTH-01])
    """
    
    # 2. Vulnerable Upload Doc (Negative Constraints Agent Target)
    upload_content = """
    # File Uploads
    
    Users can upload profile pictures via the `/api/upload` endpoint.
    The system accepts all file types to ensure compatibility with all cameras.
    There is no restriction on file extensions.
    (Ref: [CANARY-NEG-01])
    """

    # Write files
    with open(os.path.join(FIXTURE_DIR, "auth_bad.md"), "w") as f:
        f.write(auth_content)
        
    with open(os.path.join(FIXTURE_DIR, "upload_bad.md"), "w") as f:
        f.write(upload_content)

    print(f"✅ Fixtures generated in {FIXTURE_DIR}")
    print("   - auth_bad.md (Contains [CANARY-AUTH-01])")
    print("   - upload_bad.md (Contains [CANARY-NEG-01])")

if __name__ == "__main__":
    create_fixtures()

```

---

#### **3. The "Automated Grader" (`tests/integration/test_full_audit.py`)**

This script runs the actual `main.py` against the fixture directory and automatically grades the result. It satisfies your requirement for **Pass/Fail printing** + **Artifact generation**.

```python
import unittest
import os
import sys
from io import StringIO

# Add src to path to import main
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.main import main, parse_args
from tests.generate_fixtures import create_fixtures

class TestAuditCrewIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Run once before tests: Setup fixtures and run the Crew."""
        print("\n🔵 SETTING UP INTEGRATION TEST...")
        create_fixtures()
        
        # Override sys.argv to point to our test fixtures
        test_dir = "./tests/fixtures/vulnerable_docs"
        sys.argv = ["main.py", "--dir", test_dir]
        
        # Execute the main audit logic
        # We assume main() writes 'FINAL_AUDIT_REPORT.md' to disk
        try:
            main()
        except SystemExit as e:
            # Catch sys.exit(0) if main ends gracefully
            pass

    def test_report_exists(self):
        """Check if the report file was actually created."""
        self.assertTrue(os.path.exists("FINAL_AUDIT_REPORT.md"))

    def test_canary_auth_found(self):
        """Did the crew find the Infinite Retry vulnerability?"""
        with open("FINAL_AUDIT_REPORT.md", "r") as f:
            report_content = f.read()
        
        # We look for the finding, OR the reference ID if the agent cited it
        # Since agents might paraphrase, looking for the ID is safest if instructed to cite it.
        # Otherwise, look for keywords.
        
        failure_msg = "FAILED: The crew missed the 'Infinite Password Retry' vulnerability."
        
        # Check for specific Keywords associated with the vulnerability
        condition = "retry" in report_content.lower() and "limit" in report_content.lower()
        self.assertTrue(condition, failure_msg)
        
        if condition:
            print("   ✅ PASS: Auth Vulnerability detected.")

    def test_canary_upload_found(self):
        """Did the crew find the Unrestricted File Upload vulnerability?"""
        with open("FINAL_AUDIT_REPORT.md", "r") as f:
            report_content = f.read()
            
        failure_msg = "FAILED: The crew missed the 'Unrestricted File Upload' vulnerability."
        
        condition = "file type" in report_content.lower() or "extension" in report_content.lower()
        self.assertTrue(condition, failure_msg)
        
        if condition:
            print("   ✅ PASS: Upload Vulnerability detected.")

if __name__ == "__main__":
    unittest.main()

```

---

#### **4. Tool Unit Tests (`tests/unit/test_tools.py`)**

These tests use **Mocking** to verify your custom tool logic (sliding window search) without needing files on disk.

```python
import unittest
from unittest.mock import patch, mock_open
from src.tools.file_tools import SearchFilesTool

class TestSearchTool(unittest.TestCase):
    
    def test_search_context_window(self):
        """Verify the tool returns 3 lines before and after the match."""
        tool = SearchFilesTool()
        
        # Mock file content with 10 lines
        file_content = "\n".join([f"Line {i}" for i in range(1, 11)])
        # Let's verify searching for "Line 5"
        
        with patch("builtins.open", mock_open(read_data=file_content)):
            with patch("os.walk") as mock_walk:
                # Mock directory structure
                mock_walk.return_value = [(".", [], ["test.md"])]
                
                result = tool._run(query="Line 5", directory=".")
                
                # Assertions
                self.assertIn("Line 2", result, "Context should include 3 lines before (Line 2)")
                self.assertIn(">> Line 5", result, "Match should have visual marker >>")
                self.assertIn("Line 8", result, "Context should include 3 lines after (Line 8)")
                self.assertNotIn("Line 1", result, "Context should NOT include Line 1 (too far)")

if __name__ == "__main__":
    unittest.main()

```

---

### **How to Run Phase 5**

**1. Run Unit Tests (Fast, No Cost):**

```bash
python -m unittest tests/unit/test_tools.py

```

**2. Run Integration Test (Slow, Costs Tokens):**
This will generate the fixtures, run the actual AI Crew, and print a PASS/FAIL report.

```bash
python -m unittest tests/integration/test_full_audit.py

```

**3. Manual Review:**
After running step 2, open the newly created file to see the human-readable output:

```bash
cat FINAL_AUDIT_REPORT.md

```
