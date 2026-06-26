"""
Workflow report agent for generating markdown reports from Galaxy workflows.
"""

import logging
from pathlib import Path
from typing import Any

from galaxy.model import Workflow
from .base import (
    AgentResponse,
    SimpleGalaxyAgent,
)

log = logging.getLogger(__name__)


class WorkflowReportAgent(SimpleGalaxyAgent):
    """
    Agent that generates a markdown report template for a Galaxy workflow.
    """

    agent_type = "workflow_report"

    def get_system_prompt(self) -> str:
        prompts_dir = Path(__file__).parent / "prompts"
        prompt = (prompts_dir / "workflow_report.md").read_text()

        # Inject directive descriptions from page_assistant.md (single source of truth).
        # Extract from ## Directive Descriptions up to (not including) ## Directive Examples
        # to get the tables only — the examples use history_dataset_id= syntax which
        # does not apply in workflow report templates.
        page_prompt = (prompts_dir / "page_assistant.md").read_text()
        start = page_prompt.find("## Directive Descriptions")
        end = page_prompt.find("## Directive Examples")
        if start != -1 and end != -1:
            directive_docs = page_prompt[start:end].strip()
            prompt = prompt.replace("{directive_docs}", directive_docs)

        return prompt

    def _get_agent_config(self, key: str, default: Any = None) -> Any:
        if key == "max_query_length":
            # Workflow serializations are structured data that legitimately exceed the
            # default chat query length. Raise the ceiling while still respecting any
            # explicit admin override in inference_services config.
            # NOTE: all other validation (prompt injection checks) still runs normally —
            # workflow fields like readme and annotations are user-controlled.
            default = 50000
        return super()._get_agent_config(key, default)

    def _serialize_workflow(self, workflow: Workflow) -> str:
        """Serialize a Workflow into a compact structured string for the LLM prompt.

        Extracts exactly the fields needed for report generation: input labels/types,
        labeled tool steps (for job_parameters), and workflow output labels with their
        originating step info (for output= directives and type inference).
        """
        lines = []

        lines.append(f"Workflow name: {workflow.name}")

        if workflow.readme:
            lines.append(f"\nReadme:\n{workflow.readme}")

        # Inputs — include type so the LLM can pick the right directive
        # (data_collection_input → history_dataset_as_image for image collections,
        #  data_input → depends on content, but invocation_inputs() always works)
        input_steps = [s for s in workflow.input_steps if s.label or s.effective_label]
        if input_steps:
            lines.append("\nInputs:")
            for step in input_steps:
                label = step.effective_label or step.label
                annotation = step.annotations[0].annotation if step.annotations else ""
                lines.append(f"  - {label!r} (type: {step.type}): {annotation}")

        # Labeled tool steps — the only ones referenceable via step= directives
        tool_steps = [
            s for s in workflow.steps if not s.is_input_type and s.type == "tool" and (s.label or s.effective_label)
        ]
        if tool_steps:
            lines.append("\nTool steps with labels (usable in job_parameters/job_metrics):")
            for step in sorted(tool_steps, key=lambda s: s.order_index):
                label = step.effective_label or step.label
                annotation = f" — {step.annotations[0].annotation}" if step.annotations else ""
                lines.append(f"  {step.order_index + 1}. {label!r} [tool_id: {step.tool_id}]{annotation}")

        # Workflow outputs — include the originating step label and tool_id so the LLM
        # can infer the likely output type (image, tabular, HTML) for directive selection
        if outputs := list(workflow.workflow_outputs):
            lines.append("\nWorkflow outputs (usable in output= directives):")
            for out in outputs:
                out_label = out.label or out.output_name
                step = out.workflow_step
                if step:
                    step_label = step.effective_label or step.label or f"step {step.order_index + 1}"
                    tool_id = step.tool_id or ""
                    lines.append(
                        f"  - {out_label!r} [from step {step.order_index + 1}: {step_label!r}, tool_id: {tool_id}]"
                    )
                else:
                    lines.append(f"  - {out_label!r}")

        return "\n".join(lines)

    async def generate_workflow_report(self, workflow: Workflow) -> AgentResponse:
        """Generate a markdown report template for the given workflow."""
        serialized = self._serialize_workflow(workflow)
        query = (
            "Generate a Galaxy workflow report template for the following workflow.\n\n"
            "Output ONLY the Galaxy markdown report — no preamble, notes, or explanation.\n\n"
            f"{serialized}"
        )
        return await self.process(query)
