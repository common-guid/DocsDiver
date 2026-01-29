import os
import sys
import argparse
from pathlib import Path
from crewai import Crew, Process
from src.utils.toc_generator import ToCGenerator
from src.agents.agents import AuditAgents
from src.agents.tasks import AuditTasks
from src.config.app_config import get_artifacts_dir, get_docs_dir, get_toc_path

def parse_args():
    parser = argparse.ArgumentParser(description="DocsDiver-Crew CLI")
    parser.add_argument(
        "--dir",
        type=str,
        default=None,
        help="Path to the documentation directory (overrides config.yaml docs_dir)"
    )
    return parser.parse_args()

def validate_environment(target_dir: Path):
    """Fail fast if keys or dirs are missing."""
    # 1. Check Directory
    if not target_dir.exists():
        print(f"❌ Error: Directory '{target_dir}' does not exist.")
        sys.exit(1)

    # 2. Check Keys (Add others if needed)
    required_keys = ["OPENROUTER_API_KEY", "GEMINI_API_KEY"]
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
    docs_dir = get_docs_dir(args.dir)
    toc_path = get_toc_path()
    artifacts_dir = get_artifacts_dir()

    print(f"\n🚀 Starting DocsDiver on: {docs_dir}\n" + "="*40)
    validate_environment(docs_dir)

    # --- Phase 2: Librarian ---
    if toc_path.is_file():
        print("\n## 1. Skipping Librarian (ToC already exists)...")
    else:
        print("\n## 1. Running Librarian (ToC Generator)...")
        toc_gen = ToCGenerator(root_dir=str(docs_dir), output_path=str(toc_path))
        toc_gen.generate()

    # Load ToC
    try:
        with open(toc_path, "r", encoding="utf-8") as f:
            toc_content = f.read()
    except FileNotFoundError:
        print("❌ Error: ToC file was not found at the configured path.")
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
        planning_llm=supervisor.llm,
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
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    output_filename = artifacts_dir / "FINAL_AUDIT_REPORT.md"

    # Convert result to string if it's a CrewOutput object
    final_content = str(result)

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(f"✅ Success! Report saved to: {os.path.abspath(output_filename)}")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
