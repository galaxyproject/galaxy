"""
Workflow report agent for generating markdown reports from Galaxy workflows.
"""

import logging
from pathlib import Path

from galaxy.model import (
    HistoryDatasetCollectionAssociation,
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
        prompts_dir = Path(__file__).parent / "prompts"
        prompt = (prompts_dir / "workflow_report.md").read_text()

        # Import directive documentation from notebook_assistant.md (single source of truth).
        # Extract from ## Galaxy Markdown Directive Syntax up to (not including) ## Full Directive Reference.
        notebook_prompt = (prompts_dir / "notebook_assistant.md").read_text()
        start = notebook_prompt.find("## Galaxy Markdown Directive Syntax")
        end = notebook_prompt.find("## Full Directive Reference")
        if start != -1 and end != -1:
            directive_docs = notebook_prompt[start:end].strip()
            prompt = prompt.replace("{directive_docs}", directive_docs)

        return prompt

    def _collection_format(self, hdca: HistoryDatasetCollectionAssociation) -> str:
        """Return the predominant element format of a HistoryDatasetCollectionAssociation."""
        try:
            datatypes = hdca.collection.elements_datatypes
            if isinstance(datatypes, dict) and datatypes:
                return max(datatypes, key=lambda k: datatypes[k])
        except Exception:
            pass
        return "unknown"

    def _serialize_invocation(self, invocation: WorkflowInvocation, encoded_id: str) -> str:
        """Serialize a WorkflowInvocation into a structured string for the LLM prompt.

        Maps actual run state and outputs against the workflow's expected steps,
        giving the LLM enough context to produce a post-run report.
        """
        lines = []

        lines.append(f"Invocation ID: {encoded_id}")
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
                fmt = self._collection_format(assoc.dataset_collection) if assoc.dataset_collection else "unknown"
                lines.append(f"  - {label}: {collection_name} (collection, format: {fmt})")

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
                fmt = self._collection_format(assoc.dataset_collection) if assoc.dataset_collection else "unknown"
                lines.append(f"  - {label}: {collection_name} (collection, format: {fmt})")

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

    async def generate_invocation_report(
        self, workflow: Workflow, invocation: WorkflowInvocation, invocation_id: str
    ) -> AgentResponse:
        """Generate a post-run markdown report for the given workflow invocation.

        Two-phase approach:
        1. Generate a perfect workflow editor report (correct directives guaranteed).
        2. Transform that report into an invocation report by adding invocation_id to all
           directives and enriching the prose with actual run outcomes.
        """
        # Phase 1: generate the base workflow editor report
        base_report = await self.generate_workflow_report(workflow)

        # Phase 2: transform into an invocation report using the actual run data
        serialized_invocation = self._serialize_invocation(invocation, invocation_id)
        query = (
            f"Transform the following pre-run workflow report into an invocation report.\n\n"
            f"Instructions:\n"
            f"1. Add invocation_id={invocation_id} as the FIRST argument to EVERY galaxy directive. No exceptions.\n"
            f"2. Update the Results section prose to reflect the actual outputs and run outcome from the run details.\n"
            f"3. If any steps have a failed state, note it briefly in the relevant pipeline section.\n"
            f"4. Do not change, add, or remove any directives — only add invocation_id= to existing ones.\n"
            f"5. Output ONLY the modified report. No preamble or explanation.\n\n"
            f"## Pre-run workflow report\n\n{base_report.content}\n\n"
            f"## Run details\n\n{serialized_invocation}"
        )
        response = await self.process(query)

        # Accumulate token counts from both phases so callers see the total cost.
        for key in ("total_tokens", "input_tokens", "output_tokens"):
            phase1 = base_report.metadata.get(key) or 0
            phase2 = response.metadata.get(key) or 0
            if phase1 or phase2:
                response.metadata[key] = phase1 + phase2

        return response

    async def generate_workflow_report(self, workflow: Workflow) -> AgentResponse:
        """Generate a markdown report for the given workflow."""
        serialized = self._serialize_workflow(workflow)
        allowlist = self._allowed_labels(workflow)
        query = f"Generate a Galaxy workflow report for the following workflow:\n\n{serialized}\n{allowlist}"
        return await self.process(query)
