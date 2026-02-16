import json
import os
import logging
import asyncio
from sdaa.src.core.config_loader import config_loader
from sdaa.src.tools.notebook import append_to_notebook, clear_notebook, read_notebook
from sdaa.src.agents.workers import (
    create_permissions_agent,
    create_constraints_agent,
    create_boundaries_agent
)
from sdaa.src.agents.coordinator import create_coordinator_synthesizer
from sdaa.src.core.model_factory import get_model_for_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService

logger = logging.getLogger(__name__)

async def run_batch_audit(provider: str, ui=None, coordinator_only: bool = False):
    """
    Orchestrates the batch processing audit workflow.
    """
    output_dir = config_loader.get_output_dir()
    toc_filename = config_loader.get("system.toc_filename", "ToC.json")
    toc_path = os.path.join(output_dir, toc_filename)

    if not os.path.exists(toc_path):
        msg = f"ToC not found at {toc_path}. Please run Map Maker first."
        if ui: ui.print_error(msg)
        else: logger.error(msg)
        return

    try:
        with open(toc_path, 'r') as f:
            toc_data = json.load(f)
    except Exception as e:
        msg = f"Error reading ToC: {e}"
        if ui: ui.print_error(msg)
        else: logger.error(msg)
        return

    files = [entry['path'] for entry in toc_data.get('files', [])]

    batch_size = config_loader.get("system.batch_size", 5)
    batches = [files[i:i + batch_size] for i in range(0, len(files), batch_size)]

    if ui: ui.print_status(f"Found {len(files)} files. Processing in {len(batches)} batches of size {batch_size}.")

    workers = [
        ("permissions", create_permissions_agent, "permissions"),
        ("constraints", create_constraints_agent, "constraints"),
        ("boundaries", create_boundaries_agent, "boundaries"),
    ]

    if not coordinator_only:
        for agent_name, factory, notebook_cat in workers:
            if ui: ui.print_status(f"Starting batch processing for {agent_name}...")

            # Clear notebook for this category to start fresh
            clear_notebook(notebook_cat)

            for i, batch in enumerate(batches):
                if ui: ui.print_status(f"  Processing batch {i+1}/{len(batches)} for {agent_name}...")

                # Get model
                model = get_model_for_agent(f"{agent_name}_agent", provider)

                # Create agent
                agent = factory(model=model)

                # Ensure notebook tool is available (already handled in factory update, but safe to verify)
                if append_to_notebook not in agent.tools:
                    agent.tools.append(append_to_notebook)

                # Construct instruction
                files_str = "\n".join([f"- {f}" for f in batch])
                batch_instruction = (
                    f"\n\n[NOTEBOOK MODE]\n"
                    f"You are processing batch {i+1} of {len(batches)}.\n"
                    f"Analyze ONLY the following files:\n{files_str}\n"
                    f"Use `read_file` to read their content.\n"
                    f"Store significant findings in the '{notebook_cat}' notebook using `append_to_notebook`.\n"
                    f"Do NOT generate a final report yet. Just acknowledge completion when done."
                )

                # Run Agent with fresh session
                session_service = InMemorySessionService()
                memory_service = InMemoryMemoryService()
                runner = Runner(
                    agent=agent,
                    session_service=session_service,
                    memory_service=memory_service,
                    app_name="sdaa"
                )

                try:
                    gen = runner.run_async(
                        user_id="batch_user",
                        session_id=f"sess_{agent_name}_{i}",
                        new_message=batch_instruction
                    )

                    if ui:
                        await ui.stream_response(gen, title=f"{agent_name} (Batch {i+1})")
                    else:
                        async for _ in gen: pass

                except Exception as e:
                    logger.error(f"Error in batch {i} for {agent_name}: {e}")
                    if ui: ui.print_error(f"Error in batch {i}: {e}")

    # Coordinator Synthesis
    if ui: ui.print_status("Running Coordinator Synthesis...")

    synth_model = get_model_for_agent("coordinator", provider)
    coordinator = create_coordinator_synthesizer(provider=provider, model=synth_model)

    # Ensure read_notebook tool is available
    if read_notebook not in coordinator.tools:
        coordinator.tools.append(read_notebook)

    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()
    runner = Runner(
        agent=coordinator,
        session_service=session_service,
        memory_service=memory_service,
        app_name="sdaa"
    )

    try:
        gen = runner.run_async(
            user_id="batch_user",
            session_id="sess_coordinator",
            new_message="Generate the final report from the notebook findings."
        )

        if ui:
            await ui.stream_response(gen, title="Coordinator Synthesis")
        else:
            async for _ in gen: pass

    except Exception as e:
        logger.error(f"Error in coordinator: {e}")
        if ui: ui.print_error(f"Error in coordinator: {e}")

    if ui: ui.print_status("Batch Audit Complete.")
