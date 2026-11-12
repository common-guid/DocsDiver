import sys
import asyncio
import argparse
import os
import logging
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from sdaa.src.core.run_manifest import LEDGER, tree_hash, write_manifest
from sdaa.src.tools import file_ops
from sdaa.src.core.instrumentation import setup_instrumentation, run_observation
from sdaa.src.core.config_loader import config_loader
from sdaa.src.core.map_maker import generate_toc
from sdaa.src.core.output_validation import (
    audit_output_paths,
    audit_output_problems,
    set_aside,
    text_output_problems,
    toc_problems,
)
from sdaa.src.agents.coordinator import (
    create_coordinator_agent,
    create_coordinator_synthesizer
)
from sdaa.src.agents.workers import (
    create_permissions_agent,
    create_constraints_agent,
    create_boundaries_agent
)
from sdaa.src.utils.mock_model import MockModel
from sdaa.src.utils.openrouter_model import OpenRouterModel
from sdaa.src.core.model_factory import get_model_for_agent
from google.adk.agents import SequentialAgent
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from sdaa.src.ui.rich_chat import RichUI
from sdaa.src.utils.artifact_loader_model import ArtifactLoaderModel

def suppress_genai_non_text_warning() -> None:
    """
    Suppress the google-genai warning emitted when .text is accessed on responses
    that include non-text parts (e.g., function_call). This keeps the CLI output
    clean while preserving other warnings.
    """
    logger = logging.getLogger("google_genai.types")
    for existing_filter in logger.filters:
        if getattr(existing_filter, "_suppress_non_text_warning", False):
            return

    class _SuppressNonTextWarning(logging.Filter):
        _suppress_non_text_warning = True

        def filter(self, record: logging.LogRecord) -> bool:
            message = record.getMessage()
            return "non-text parts in the response" not in message

    logger.addFilter(_SuppressNonTextWarning())

def build_prechat_audit_agent(provider: str) -> SequentialAgent:
    artifacts_dir = config_loader.get_artifacts_dir()
    
    # helper to decide model for a worker
    def get_worker_model(agent_name: str, artifact_name: str, tool_name: str, tool_arg: str):
        artifact_path = os.path.join(artifacts_dir, artifact_name)
        
        # Reuse only a valid artifact (non-empty, not a placeholder); anything else is regenerated.
        if not text_output_problems(artifact_path):
            print(f"DEBUG: Found valid artifact for {agent_name}, skipping execution.")
            with open(artifact_path, "r", encoding="utf-8") as f:
                content = f.read()
            return ArtifactLoaderModel(content=content, tool_name=tool_name, tool_arg_name=tool_arg)

        # Otherwise use real model
        return get_model_for_agent(agent_name, provider)

    perm_model = get_worker_model(
        "permissions_agent", "permissions_agent.md", "report_permissions_matrix", "findings"
    )
    const_model = get_worker_model(
        "constraints_agent", "constraints_agent.md", "report_invariance_findings", "findings"
    )
    bound_model = get_worker_model(
        "boundaries_agent", "boundaries_agent.md", "report_boundary_analysis", "boundaries_markdown"
    )

    permissions_agent = create_permissions_agent(model=perm_model)
    constraints_agent = create_constraints_agent(model=const_model)
    boundaries_agent = create_boundaries_agent(model=bound_model)

    # create_coordinator_synthesizer now accepts provider
    coordinator_synth = create_coordinator_synthesizer(provider=provider)

    return SequentialAgent(
        name="prechat_audit",
        sub_agents=[
            permissions_agent,
            constraints_agent,
            boundaries_agent,
            coordinator_synth
        ]
    )

def apply_path_overrides(parser, args):
    """Write --docs-root/--output-dir into the config, then validate the effective paths (exit 2 on error)."""
    if args.docs_root is None and args.output_dir is None:
        return
    system = config_loader.config.setdefault("system", {})
    if args.docs_root is not None:
        system["docs_root"] = os.path.abspath(os.path.expanduser(args.docs_root))
    if args.output_dir is not None:
        system["output_dir"] = os.path.abspath(os.path.expanduser(args.output_dir))

    docs = Path(os.path.abspath(config_loader.get("system.docs_root", "./docs"))).resolve()
    out = Path(os.path.abspath(os.path.expanduser(config_loader.get("system.output_dir", ".") or "."))).resolve()
    if args.docs_root is not None and not docs.is_dir():
        parser.error(f"--docs-root {args.docs_root}: does not exist or is not a directory")
    if out.exists() and not out.is_dir():
        parser.error(f"output directory {out}: exists and is not a directory")
    if out == docs or out.is_relative_to(docs):
        parser.error(f"output directory {out} is inside the docs root {docs}; the audit would read its own outputs")


async def main():
    parser = argparse.ArgumentParser(description="SDAA: Security Documentation Analysis Agent")
    parser.add_argument("-m", "--model", choices=["gemini", "openrouter", "mock"], default="openrouter", help="Model provider to use")
    parser.add_argument("--skip-map-maker", action="store_true", help="Skip Map Maker and use an existing ToC.json if present")
    parser.add_argument("--toc-only", action="store_true", help="Run Map Maker only and exit before starting the coordinator")
    parser.add_argument("--coordinator-only", action="store_true", help="Run only the coordinator using existing artifacts, bypassing workers and Map Maker")
    parser.add_argument("--no-rich", action="store_true", help="Disable Rich terminal UI and use plain text output")
    parser.add_argument("--headless", action="store_true", help="Run non-interactively: Map Maker + Pre-chat Audit, write all outputs, then exit. Exit code 0 on success, 1 on failure (missing ToC or outputs).")
    parser.add_argument("--refresh-toc", action="store_true", help="Rebuild the ToC and then the whole audit; previous outputs are kept as .prev")
    parser.add_argument("--refresh-audit", action="store_true", help="Rerun all workers and synthesis, reusing a valid ToC; previous outputs are kept as .prev")
    parser.add_argument("--docs-root", help="Directory of Markdown docs to audit for this run (overrides system.docs_root)")
    parser.add_argument("--output-dir", help="Directory for this run's ToC, artifacts and report (overrides system.output_dir)")
    parser.add_argument("--run-id", help="Run and Langfuse session ID (1-64 letters, digits, '.', '_' or '-')")
    args = parser.parse_args()

    # Contradictory flags are usage errors (exit 2), reported before any I/O.
    if args.refresh_toc and args.skip_map_maker:
        parser.error("--refresh-toc cannot be combined with --skip-map-maker")
    if args.refresh_toc and args.coordinator_only:
        parser.error("--refresh-toc cannot be combined with --coordinator-only")
    if args.refresh_audit and args.coordinator_only:
        parser.error("--refresh-audit cannot be combined with --coordinator-only")
    if args.refresh_audit and args.toc_only:
        parser.error("--refresh-audit cannot be combined with --toc-only")
    apply_path_overrides(parser, args)
    if args.run_id is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", args.run_id):
        value = args.run_id
        parser.error(f"--run-id {value!r}: use 1-64 letters, digits, '.', '_' or '-', starting with a letter or digit")
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + secrets.token_hex(3)
    LEDGER.clear()
    corpus = {"tree_hash": None, "file_count": None}
    try:
        docs_root = file_ops._get_docs_root()
        if not os.path.isdir(docs_root):
            raise NotADirectoryError(docs_root)
        digest, count = tree_hash(docs_root)
        corpus = {"tree_hash": digest, "file_count": count}
    except Exception as e:
        logging.getLogger(__name__).warning("Could not hash corpus: %s", e)

    code = 1                      # anything but a normal return is a failure
    regenerated = set()
    try:
        setup_instrumentation(session_id=run_id)
        with run_observation(run_id, {
            "provider": args.model, "docs_root": file_ops._get_docs_root(),
            "headless": args.headless, "toc_only": args.toc_only,
        }) as root:
            await _run(args, parser, run_id, regenerated)
            if root is not None:
                paths = audit_output_paths()
                root.update(output={
                    "status": "completed",
                    "report": Path(paths[-1]).read_text(encoding="utf-8")
                    if not args.toc_only and os.path.isfile(paths[-1]) else None,
                    "toc_only": args.toc_only,
                })
        code = 0
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        raise
    finally:
        if args.headless:
            try:
                output_dir = config_loader.get_output_dir()
                toc_path = os.path.join(output_dir, config_loader.get("system.toc_filename", "ToC.json"))
                output_files = {
                    os.path.basename(path): os.path.abspath(path)
                    for path in [toc_path] + audit_output_paths()
                }
                problems = toc_problems(toc_path)
                if not args.toc_only:
                    problems += audit_output_problems()
                write_manifest(
                    os.path.join(output_dir, "run_manifest.json"),
                    run_id=run_id, started_at=started_at, argv=sys.argv,
                    provider=args.model,
                    paths={"docs_root": os.path.abspath(file_ops._get_docs_root()),
                           "output_dir": os.path.abspath(output_dir)},
                    repo_root=os.path.dirname(os.path.abspath(__file__)),
                    corpus=corpus, output_files=output_files,
                    generated={os.path.abspath(path) for path in regenerated},
                    exit_code=code, problems=problems,
                )
            except Exception as e:
                print(f"run manifest not written: {e!r}", file=sys.stderr)


async def _run(args, parser, run_id, regenerated):

    ui = RichUI(no_rich=args.no_rich)
    suppress_genai_non_text_warning()

    ui.print_banner("SDAA: Security Documentation Analysis Agent")
    ui.print_status(f"Using provider: {args.model}")

    # 1. Map Maker
    toc_filename = config_loader.get("system.toc_filename", "ToC.json")
    output_dir = config_loader.get_output_dir()
    toc_path = os.path.join(output_dir, toc_filename)

    if args.refresh_toc:
        # Invalidate the index and everything built from it, durably (even with --toc-only).
        ui.print_status("[Phase 1] --refresh-toc: moving the ToC and audit outputs aside (.prev).")
        set_aside([toc_path] + audit_output_paths())

    if args.skip_map_maker or args.coordinator_only:
        flag = "--skip-map-maker" if args.skip_map_maker else "--coordinator-only"
        ui.print_status(f"\n[Phase 1] Skipping Map Maker due to {flag}. Expecting a valid ToC at {toc_path}.")
    else:
        existing_problems = toc_problems(toc_path)
        if not existing_problems:
            ui.print_status(f"\n[Phase 1] Skipping Map Maker because a valid ToC was found at {toc_path}.")
        else:
            if os.path.exists(toc_path):
                ui.print_status(
                    f"\n[Phase 1] Existing ToC is invalid ({existing_problems[0]}); regenerating. "
                    f"The previous file is kept as {toc_path}.prev."
                )
            ui.print_status("\n[Phase 1] Initializing Map Maker...")
            # Move the old ToC aside so generate_toc's exists-guard cannot skip it and a
            # failed run leaves the ToC missing rather than stale.
            set_aside([toc_path])
            try:
                # Instantiate model specifically for map_maker
                map_maker_model = get_model_for_agent("map_maker", args.model)
                await generate_toc(model=map_maker_model)
                regenerated.add(toc_path)
            except Exception as e:
                # A missing or partial index is fatal in every mode.
                ui.print_error(f"generating ToC: {e}")
                sys.exit(1)
            ui.print_status(f"ToC generation complete. Wrote ToC to {toc_path}.")
            if any(not text_output_problems(p) for p in audit_output_paths()):
                ui.print_status(
                    "WARNING: audit outputs predate the new ToC; use --refresh-audit to regenerate them."
                )

    toc_errors = toc_problems(toc_path)
    if toc_errors:
        ui.print_error("ToC is not usable:\n  " + "\n  ".join(toc_errors))
        sys.exit(1)

    if args.toc_only:
        ui.print_status("[Phase 1] --toc-only specified; exiting after Map Maker.")
        return

    # 2. Initialize Agent
    ui.print_status("\n[Phase 2] Initializing Coordinator...")
    # Pass provider to create_coordinator_agent
    coordinator = create_coordinator_agent(provider=args.model)

    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()

    # Initialize Runner
    runner = Runner(
        agent=coordinator,
        app_name="sdaa",
        session_service=session_service,
        memory_service=memory_service
    )
    session_id = run_id
    user_id = "user_001"

    # Create Session explicitly
    try:
        session = await session_service.get_session(
            app_name="sdaa",
            user_id=user_id,
            session_id=session_id
        )
        if not session:
            session = await session_service.create_session(
                app_name="sdaa",
                user_id=user_id,
                session_id=session_id
            )
        # print(f"Session created: {session.id}")

    except Exception as e:
        ui.print_error(f"creating session: {e}")

    # Ensure output directories exist
    config_loader.get_reports_dir()
    config_loader.get_artifacts_dir()
    output_paths = audit_output_paths()
    worker_paths, report_path = output_paths[:-1], output_paths[-1]
    if args.refresh_audit:
        ui.print_status("[Phase 2.5] --refresh-audit: moving worker artifacts and the report aside (.prev).")
        set_aside(output_paths)

    if args.coordinator_only:
        # Coordinator-only reuses the worker artifacts; it never manufactures missing ones.
        unusable = [p for path in worker_paths for p in text_output_problems(path)]
        if unusable:
            ui.print_error(
                "--coordinator-only needs three valid worker artifacts:\n  " + "\n  ".join(unusable)
                + "\nRun without --coordinator-only to generate them."
            )
            sys.exit(1)

    stale = [path for path in output_paths if text_output_problems(path)]
    generated = set()
    if stale or args.coordinator_only:
        # Synthesis always regenerates the report; set it aside with any invalid output so a run
        # that fails to rewrite it ends with the report missing, not stale.
        generated = set(stale) | {report_path}
        regenerated.update(generated)
        set_aside(sorted(generated))
        ui.print_status(
            "\n[Phase 2.5] Running Pre-chat Audit..."
        )
        prechat_agent = build_prechat_audit_agent(provider=args.model)
        prechat_runner = Runner(
            agent=prechat_agent,
            app_name="sdaa",
            session_service=session_service,
            memory_service=memory_service
        )
        try:
            await ui.stream_response(
                prechat_runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=types.Content(parts=[types.Part.from_text(text="Audit the application")])
                ),
                title="Pre-chat Audit"
            )
            ui.print_status("Pre-chat audit complete.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            ui.print_error(f"\n{e}")
            if args.headless:
                sys.exit(1)
    else:
        ui.print_status("\n[Phase 2.5] Skipping Pre-chat Audit (all outputs valid).")

    ui.print_status(
        "Audit outputs: " + ", ".join(
            f"{os.path.basename(p)} ({'generated' if p in generated else 'reused'})" for p in output_paths
        )
    )
    problems = audit_output_problems()
    if args.headless:
        # Non-interactive mode: success means every output is present AND valid.
        if problems:
            ui.print_error("Headless run incomplete:\n  " + "\n  ".join(problems))
            sys.exit(1)
        ui.print_status("\n[Phase 3] Headless run complete. All outputs valid.")
        return
    if problems:
        ui.print_status("WARNING: some audit outputs are not valid:\n  " + "\n  ".join(problems))

    ui.print_status("\n[Phase 3] Agent Ready. (Type 'exit' to quit)")

    while True:
        try:
            user_input = ui.ask_user("\nUser> ")
            if user_input.lower() in ('exit', 'quit'):
                break

            await ui.stream_response(
                runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=types.Content(parts=[types.Part.from_text(text=user_input)])
                ),
                title="Coordinator"
            )

        except KeyboardInterrupt:
            break
        except Exception as e:
            ui.print_error(f"\n{e}")
            break

if __name__ == "__main__":
    asyncio.run(main())
