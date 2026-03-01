"""
Workflow report agent for generating markdown reports from Galaxy workflows.
"""

import logging
from pathlib import Path

from galaxy.model import Workflow
from .base import (
    AgentResponse,
    GalaxyAgentDependencies,
    SimpleGalaxyAgent,
)

log = logging.getLogger(__name__)


class WorkflowReportAgent(SimpleGalaxyAgent):
    """
    Agent that generates a markdown report for a Galaxy workflow.
    """

    agent_type = "workflow_report"

    def get_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent / "prompts" / "workflow_report.md"
        return prompt_path.read_text()

    def _serialize_workflow(self, workflow: Workflow) -> str:
        """Serialize a Workflow into a structured string for the LLM prompt."""
        lines = []

        lines.append(f"Workflow name: {workflow.name}")

        if workflow.readme:
            lines.append(f"\nReadme:\n{workflow.readme}")

        # Inputs
        input_steps = [s for s in workflow.input_steps if s.label or s.effective_label]
        if input_steps:
            lines.append("\nInputs:")
            for step in input_steps:
                label = step.effective_label or step.label
                annotation = step.annotations[0].annotation if step.annotations else ""
                lines.append(f"  - {label} ({step.type}): {annotation}")

        # Steps (non-input) — only labeled tool steps are included since they are the
        # only ones that can be referenced by step= directives in the report
        tool_steps = [
            s for s in workflow.steps if not s.is_input_type and s.type == "tool" and (s.label or s.effective_label)
        ]
        if tool_steps:
            lines.append("\nSteps (tool steps with labels only — use these for job_parameters/job_metrics):")
            for step in sorted(tool_steps, key=lambda s: s.order_index):
                label = step.effective_label or step.label
                annotation = ""
                if step.annotations:
                    annotation = f" — {step.annotations[0].annotation}"
                lines.append(f"  {step.order_index + 1}. {label} [tool_id: {step.tool_id}]{annotation}")

        # Outputs
        outputs = list(workflow.workflow_outputs)
        if outputs:
            lines.append("\nOutputs:")
            for out in outputs:
                lines.append(f"  - {out.label or out.output_name}")

        return "\n".join(lines)

    def _allowed_labels(self, workflow: Workflow) -> str:
        """Build an explicit allowlist of labels usable in Galaxy directives."""
        input_steps = [s for s in workflow.input_steps if s.label or s.effective_label]
        tool_steps = [
            s for s in workflow.steps if not s.is_input_type and s.type == "tool" and (s.label or s.effective_label)
        ]
        outputs = list(workflow.workflow_outputs)

        input_labels = [s.effective_label or s.label for s in input_steps]
        step_labels = [s.effective_label or s.label for s in tool_steps]
        output_labels = [out.label or out.output_name for out in outputs]

        lines = [
            "\nSTRICT LABEL ALLOWLIST — you must ONLY use the exact labels below in directives.",
            "Do not invent, guess, or paraphrase any label. If a list is empty, omit that directive type entirely.",
            f"  Allowed input= values:  {input_labels}",
            f"  Allowed step= values:   {step_labels}",
            f"  Allowed output= values: {output_labels}",
        ]
        return "\n".join(lines)

    async def generate_report(self, workflow: Workflow) -> AgentResponse:
        """Generate a markdown report for the given workflow."""
        serialized = self._serialize_workflow(workflow)
        allowlist = self._allowed_labels(workflow)
        query = f"Generate a Galaxy workflow report for the following workflow:\n\n{serialized}\n{allowlist}"
        return await self.process(query)
