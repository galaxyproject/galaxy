"""
Workflow report agent for generating markdown reports from Galaxy workflows.
"""

import logging
from pathlib import Path

from galaxy.model import (
    Workflow,
    WorkflowInvocation,
)
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

    def _serialize_invocation(self, invocation: WorkflowInvocation) -> str:
        """Serialize a WorkflowInvocation into a structured string for the LLM prompt.

        Maps actual run state and outputs against the workflow's expected steps,
        giving the LLM enough context to produce a post-run report.
        """
        lines = []

        lines.append(f"Invocation state: {invocation.state}")
        if invocation.history:
            lines.append(f"History: {invocation.history.name}")

        # Inputs used in this run
        input_datasets = list(invocation.input_datasets)
        input_collections = list(invocation.input_dataset_collections)
        if input_datasets or input_collections:
            lines.append("\nInputs used:")
            for assoc in input_datasets:
                label = assoc.workflow_step.label if assoc.workflow_step else assoc.name
                dataset_name = assoc.dataset.name if assoc.dataset else "(unknown)"
                lines.append(f"  - {label}: {dataset_name}")
            for assoc in input_collections:
                label = assoc.workflow_step.label if assoc.workflow_step else assoc.name
                collection_name = assoc.dataset_collection.name if assoc.dataset_collection else "(unknown)"
                lines.append(f"  - {label}: {collection_name} (collection)")

        # Per-step run state — only labeled tool steps (matching the directive allowlist)
        tool_invocation_steps = [
            s
            for s in invocation.steps
            if s.workflow_step
            and not s.workflow_step.is_input_type
            and s.workflow_step.type == "tool"
            and s.workflow_step.label
        ]
        if tool_invocation_steps:
            lines.append("\nStep execution states:")
            for step in sorted(tool_invocation_steps, key=lambda s: s.workflow_step.order_index):
                label = step.workflow_step.label
                lines.append(f"  - {label}: {step.state or 'unknown'}")

        # Workflow-level outputs produced (these map to output= directives)
        output_datasets = list(invocation.output_datasets)
        output_collections = list(invocation.output_dataset_collections)
        if output_datasets or output_collections:
            lines.append("\nOutputs produced:")
            for assoc in output_datasets:
                label = assoc.workflow_output.label or assoc.workflow_output.output_name
                dataset_name = assoc.dataset.name if assoc.dataset else "(unknown)"
                lines.append(f"  - {label}: {dataset_name}")
            for assoc in output_collections:
                label = assoc.workflow_output.label or assoc.workflow_output.output_name
                collection_name = assoc.dataset_collection.name if assoc.dataset_collection else "(unknown)"
                lines.append(f"  - {label}: {collection_name} (collection)")

        return "\n".join(lines)

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

    async def generate_invocation_report(self, workflow: Workflow, invocation: WorkflowInvocation) -> AgentResponse:
        """Generate a post-run markdown report for the given workflow invocation."""
        serialized_workflow = self._serialize_workflow(workflow)
        serialized_invocation = self._serialize_invocation(invocation)
        allowlist = self._allowed_labels(workflow)
        query = (
            f"Generate a Galaxy invocation report for the following workflow run:\n\n"
            f"## Workflow definition\n{serialized_workflow}\n\n"
            f"## Run details\n{serialized_invocation}\n"
            f"{allowlist}"
        )
        return await self.process(query)

    async def generate_workflow_report(self, workflow: Workflow) -> AgentResponse:
        """Generate a markdown report for the given workflow."""
        serialized = self._serialize_workflow(workflow)
        allowlist = self._allowed_labels(workflow)
        query = f"Generate a Galaxy workflow report for the following workflow:\n\n{serialized}\n{allowlist}"
        return await self.process(query)
