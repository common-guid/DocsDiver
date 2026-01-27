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
    output_filename = "FINAL_AUDIT_REPORT.md"

    # Convert result to string if it's a CrewOutput object
    final_content = str(result)

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(f"✅ Success! Report saved to: {os.path.abspath(output_filename)}")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
