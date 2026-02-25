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
        input_steps = list(workflow.input_steps)
        if input_steps:
            lines.append("\nInputs:")
            for step in input_steps:
                label = step.effective_label or step.label or "(unlabeled)"
                lines.append(f"  - {label} (type: {step.type})")

        # Steps (non-input)
        tool_steps = [s for s in workflow.steps if not s.is_input_type]
        if tool_steps:
            lines.append("\nSteps:")
            for step in sorted(tool_steps, key=lambda s: s.order_index):
                label = step.effective_label or step.label or "(unlabeled)"
                tool = step.tool_id or step.type or "unknown"
                annotation = ""
                if step.annotations:
                    annotation = f" — {step.annotations[0].annotation}"
                lines.append(f"  {step.order_index + 1}. {label} [{tool}]{annotation}")

        # Outputs
        outputs = list(workflow.workflow_outputs)
        if outputs:
            lines.append("\nOutputs:")
            for out in outputs:
                lines.append(f"  - {out.label or out.output_name}")

        return "\n".join(lines)

    async def generate_report(self, workflow: Workflow) -> AgentResponse:
        """Generate a markdown report for the given workflow."""
        serialized = self._serialize_workflow(workflow)
        return await self.process(serialized)
