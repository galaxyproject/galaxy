"""Carry a notebook page's markdown into an extracted workflow's report.

Extraction (:func:`galaxy.workflow.extract.extract_workflow_by_ids`) hands its
``build_report`` hook an :class:`~galaxy.workflow.extract.ExtractionLabelIndex`
mapping the ids the page references to the labeled workflow steps/outputs it
built. This module turns the page's internal-id markdown into a portable
workflow report:

1. :func:`reconcile_report_labels` auto-labels/exposes any referenced item the
   user left unlabeled, so every directive can resolve. This can expose outputs
   the notebook displays but the user did not explicitly star.
2. :class:`_ReportLabelRewriter` does the pure id -> label rewrite against the
   now-complete index, reusing the directive-walk taxonomy and access checks of
   the shared markdown directive handler.

:func:`reconcile_and_build_report` runs both, and is the only entry point the
service needs. It *mutates* the extracted workflow (step labels / workflow
outputs) as a side effect of reconcile; it runs before the workflow is persisted,
so those mutations and the report are committed with it.
"""

import logging
import re
from datetime import datetime

from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.markdown_parse import (
    is_quotable_argument_value,
    VALID_ARGUMENTS,
)
from galaxy.managers.markdown_util import (
    _remap_galaxy_markdown_calls,
    _remap_galaxy_markdown_embedded_containers,
    check_galaxy_markdown,
    ENCODED_ID_PATTERN,
    GalaxyInternalMarkdownDirectiveHandler,
    referenced_content_ids,
    ReferencedContent,
)
from galaxy.managers.workflow_extraction_naming import (
    MAX_LABEL_LENGTH,
    normalize_generated_label,
    suggested_output_name,
)
from galaxy.model import (
    History,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    HistoryItem,
    Job,
    Page,
    StoredWorkflow,
    WorkflowInvocation,
    WorkflowStep,
)
from galaxy.workflow.extract import (
    DirectiveLabel,
    ExtractionLabelIndex,
    resolve_content,
)

log = logging.getLogger(__name__)

# A directive handler's result: the rewritten line and whether the line was dropped.
DirectiveResult = tuple[str, bool]

# hid= points at an item of the notebook's history, like an id argument.
_HID_ARGUMENT = re.compile(r"\b(hid)\s*=")
_QUOTED_VALUE = re.compile(r"\"[^\"]*\"|'[^']*'")
_DATASET_CELL = re.compile(r"^```[ \t]*(visualization|vitessce)[ \t]*\n.*?^```[ \t]*$\n?", re.MULTILINE | re.DOTALL)
_CELL_INSTANCE_REFERENCE = re.compile(r'"(?:dataset_id|dataset_url|__gx_dataset_id)"\s*:|"invocation_id"\s*:\s*"[^"]+"')


def reconcile_and_build_report(
    trans: ProvidesHistoryContext, page: Page, index: ExtractionLabelIndex
) -> tuple[str, list[str]]:
    """Build a workflow report markdown (and warnings) from a notebook page.

    Reconciles the index so referenced-but-unlabeled items get labels -- which
    *mutates* the extracted workflow's steps (assigning labels, exposing workflow
    outputs the user did not star) -- then rewrites the page's internal markdown
    into the workflow-relative form.
    """
    revision = page.latest_revision
    content = revision.content if revision is not None else None
    if not content:
        return "", []
    referenced = referenced_content_ids(trans, content)
    reconcile_report_labels(trans, index, referenced)
    markdown, warnings = _rewrite_page_markdown(trans, content, index, page.history_id)
    return markdown, referenced.warnings + warnings


def _rewrite_page_markdown(
    trans: ProvidesHistoryContext, internal_markdown: str, index: ExtractionLabelIndex, page_history_id: int | None
) -> tuple[str, list[str]]:
    """Rewrite a notebook page's internal markdown into a workflow report.

    Returns the rewritten (label-based) markdown and any warnings for directives
    that had to be dropped. Validates the result so a malformed rewrite fails at
    extraction time rather than at report render, as a MalformedContents rather
    than the bare ValueError the parser raises.
    """
    rewriter = _ReportLabelRewriter(index, page_history_id)
    markdown = rewriter.walk_directives(trans, internal_markdown)
    check_galaxy_markdown(markdown)
    # Only removes whole directives/embeds/cells, so the result stays valid.
    markdown, sweep_warnings = _drop_instance_references(markdown)
    return markdown, rewriter.warnings + sweep_warnings


def _instance_argument(directive: str) -> str | None:
    """Name of the first argument of ``directive`` that points at a specific Galaxy object."""
    unquoted = _QUOTED_VALUE.sub('""', directive)
    for pattern in (ENCODED_ID_PATTERN, _HID_ARGUMENT):
        if match := pattern.search(unquoted):
            return match.group(1)
    return None


def _drop_instance_references(markdown: str) -> tuple[str, list[str]]:
    """Drop, with a warning, whatever still points at a specific Galaxy object after the rewrite.

    The rewriter only resolves directives it recognizes; this sweep guarantees no
    instance reference survives into the report: fenced directives still carrying
    an id/hid argument (e.g. ``invocation_id=``-scoped lines the walk passes
    through), object-referencing inline embeds, and visualization/vitessce cells
    naming a dataset or invocation. The invocation report renders neither label
    embeds nor label visualization cells correctly yet, so those are dropped
    rather than rewritten.
    """
    warnings: list[str] = []

    def _directive(container: str, line: str) -> DirectiveResult:
        argument = _instance_argument(line)
        if argument is None:
            return (line, False)
        warnings.append(
            f"Dropped a [{container}] directive from the report: it names a specific Galaxy object "
            f"({argument}), which has no workflow-relative form."
        )
        return ("", True)

    def _embed(match: re.Match[str]) -> str:
        container = match.group("container")
        # Embeds that take arguments reference a dataset, invocation or workflow.
        if not VALID_ARGUMENTS[container] and _instance_argument(match.group()) is None:
            return match.group()
        warnings.append(
            f"Dropped an inline [{container}] reference from the report: inline object references do not "
            "resolve in workflow reports."
        )
        return ""

    def _cell(match: re.Match[str]) -> str:
        if not _CELL_INSTANCE_REFERENCE.search(match.group()):
            return match.group()
        warnings.append(
            f"Dropped a [{match.group(1)}] cell from the report: it names a specific dataset or invocation, "
            "which has no workflow-relative form."
        )
        return ""

    markdown = _remap_galaxy_markdown_calls(_directive, markdown)
    markdown = _remap_galaxy_markdown_embedded_containers(_embed, markdown)
    markdown = _DATASET_CELL.sub(_cell, markdown)
    return markdown, warnings


class _ReportLabelRewriter(GalaxyInternalMarkdownDirectiveHandler):
    """Rewrite a notebook page's internal-id directives into workflow-relative
    label directives for storage as a workflow report.

    The inverse of :func:`resolve_invocation_markdown`: a dataset/collection
    reference becomes ``input="x"`` / ``output="y"`` and a job reference becomes
    ``step="z"``, read from the ``label_index`` extraction built. Reuses the
    directive-walk taxonomy and access checks of the base handler, like
    ``_ReferencedContentCollector``; only the content/job directives carry
    behavior.

    A portable report must never embed an instance id. So a content/job directive
    that cannot resolve to a label, and any id-bearing directive with no
    workflow-relative form (links to other histories, workflows, invocations), is
    dropped with a warning rather than leaked. A link to the notebook's own
    history becomes ``history_link()``, i.e. the invocation's history. Id-less
    directives pass through; :func:`_drop_instance_references` then sweeps what
    this walk does not visit (embeds, visualization cells, unrecognized lines).
    """

    def __init__(self, label_index: ExtractionLabelIndex, page_history_id: int | None) -> None:
        self.index = label_index
        self.page_history_id = page_history_id
        self.warnings: list[str] = []

    def _rewrite(self, line: str, target: DirectiveLabel | None, description: str) -> DirectiveResult:
        if target is None:
            self.warnings.append(f"Dropped a {description} from the report: it has no workflow-relative label.")
            return ("", True)
        argument, label = target
        if not is_quotable_argument_value(label):
            self.warnings.append(
                f"Dropped a {description} from the report: its label {label!r} contains a double quote or "
                "line break, which report directives cannot express."
            )
            return ("", True)
        arg = f'{argument}="{label}"'
        return (ENCODED_ID_PATTERN.sub(lambda _match: arg, line, count=1), False)

    def _drop_unportable(self, line: str, description: str) -> DirectiveResult:
        self.warnings.append(f"Dropped a {description} from the report: it cannot be expressed relative to a workflow.")
        return ("", True)

    def _content(self, line: str, content: HistoryItem) -> DirectiveResult:
        return self._rewrite(line, self.index.content_label(content), "dataset reference")

    def handle_dataset_display(self, line: str, hda: HistoryDatasetAssociation) -> DirectiveResult:
        return self._content(line, hda)

    def handle_dataset_as_image(self, line: str, hda: HistoryDatasetAssociation) -> DirectiveResult:
        return self._content(line, hda)

    def handle_dataset_as_table(self, line: str, hda: HistoryDatasetAssociation) -> DirectiveResult:
        return self._content(line, hda)

    def handle_dataset_peek(self, line: str, hda: HistoryDatasetAssociation) -> DirectiveResult:
        return self._content(line, hda)

    def handle_dataset_embedded(self, line: str, hda: HistoryDatasetAssociation) -> DirectiveResult:
        return self._content(line, hda)

    def handle_dataset_info(self, line: str, hda: HistoryDatasetAssociation) -> DirectiveResult:
        return self._content(line, hda)

    def handle_dataset_name(self, line: str, hda: HistoryDatasetAssociation) -> DirectiveResult:
        return self._content(line, hda)

    def handle_dataset_type(self, line: str, hda: HistoryDatasetAssociation) -> DirectiveResult:
        return self._content(line, hda)

    def handle_dataset_collection_display(
        self, line: str, hdca: HistoryDatasetCollectionAssociation
    ) -> DirectiveResult:
        return self._content(line, hdca)

    def _job(self, line: str, job: Job) -> DirectiveResult:
        return self._rewrite(line, self.index.job_label(job), "job reference")

    def handle_tool_stdout(self, line: str, job: Job) -> DirectiveResult:
        return self._job(line, job)

    def handle_tool_stderr(self, line: str, job: Job) -> DirectiveResult:
        return self._job(line, job)

    def handle_job_metrics(self, line: str, job: Job) -> DirectiveResult:
        return self._job(line, job)

    def handle_job_parameters(self, line: str, job: Job) -> DirectiveResult:
        return self._job(line, job)

    def handle_history_link(self, line: str, history: History) -> DirectiveResult:
        if history.id == self.page_history_id:
            return ("history_link()\n", False)
        return self._drop_unportable(line, "history link")

    # Id-bearing directives pointing at other objects -> dropped with a warning. Their
    # argument-less forms resolve against the invocation, which would silently retarget them.
    def handle_workflow_display(
        self, line: str, stored_workflow: StoredWorkflow, workflow_version: int | None
    ) -> DirectiveResult:
        return self._drop_unportable(line, "workflow display")

    def handle_workflow_image(
        self, line: str, stored_workflow: StoredWorkflow, workflow_version: int | None
    ) -> DirectiveResult:
        return self._drop_unportable(line, "workflow image")

    def handle_workflow_license(self, line: str, stored_workflow: StoredWorkflow) -> DirectiveResult:
        return self._drop_unportable(line, "workflow license")

    def handle_invocation_time(self, line: str, invocation: WorkflowInvocation) -> DirectiveResult:
        return self._drop_unportable(line, "invocation time")

    def handle_invocation_inputs(self, line: str, invocation: WorkflowInvocation) -> DirectiveResult:
        return self._drop_unportable(line, "invocation inputs")

    def handle_invocation_outputs(self, line: str, invocation: WorkflowInvocation) -> DirectiveResult:
        return self._drop_unportable(line, "invocation outputs")

    # Id-less directives pass through unchanged (the line carries no instance id).
    def handle_generate_galaxy_version(self, line: str, galaxy_version: str) -> DirectiveResult:
        return (line, False)

    def handle_generate_time(self, line: str, date: datetime) -> DirectiveResult:
        return (line, False)

    def handle_instance_access_link(self, line: str, url: str) -> DirectiveResult:
        return (line, False)

    def handle_instance_resources_link(self, line: str, url: str) -> DirectiveResult:
        return (line, False)

    def handle_instance_help_link(self, line: str, url: str) -> DirectiveResult:
        return (line, False)

    def handle_instance_support_link(self, line: str, url: str) -> DirectiveResult:
        return (line, False)

    def handle_instance_citation_link(self, line: str, url: str) -> DirectiveResult:
        return (line, False)

    def handle_instance_citation_bibtex(self, line: str, url: str) -> DirectiveResult:
        return (line, False)

    def handle_instance_terms_link(self, line: str, url: str) -> DirectiveResult:
        return (line, False)

    def handle_instance_organization_link(self, line: str, title: str, url: str) -> DirectiveResult:
        return (line, False)

    def handle_visualization(self, line: str) -> DirectiveResult:
        return (line, False)

    def handle_error(self, container: str, line: str, error: str) -> DirectiveResult:
        self.warnings.append(f"Dropped a [{container}] directive from the report: {error}")
        return ("", True)


def reconcile_report_labels(
    trans: ProvidesHistoryContext, index: ExtractionLabelIndex, referenced: ReferencedContent
) -> None:
    """Ensure every item the page references resolves to a label.

    A referenced tool output the user did not star is exposed as a workflow
    output; a referenced input or step the user did not name is labeled. Labels
    are generated from the same ``suggested_name`` chain the summary surfaces and
    deduped against the shared step/output label namespace. Items outside the
    extracted subgraph are left alone - the pure rewriter drops them with a
    warning so no instance id can leak into the report.
    """
    used = _used_labels(index)

    for ref in referenced.refs:
        content = resolve_content(trans, ref)
        if content is None:
            continue
        pair = index.step_for_content(content)
        if pair is None:
            continue
        step, output_name = pair
        if step.type in ("data_input", "data_collection_input"):
            if not step.label:
                step.label = _generate_label(_suggested(trans, content), used)
        else:
            workflow_output = step.workflow_output_for(output_name)
            if workflow_output is None or not workflow_output.label:
                label = _generate_label(_suggested(trans, content) or output_name, used)
                step.create_or_update_workflow_output(output_name=output_name, label=label, uuid=None)

    for job_id in referenced.job_refs:
        _label_step(index.job_to_step.get(job_id), used)
    for icj_id in referenced.icj_refs:
        _label_step(index.icj_to_step.get(icj_id), used)


def _label_step(step: WorkflowStep | None, used: set[str]) -> None:
    if step is None or step.label:
        return
    step.label = _generate_label(_tool_base_name(step), used)


def _used_labels(index: ExtractionLabelIndex) -> set[str]:
    steps: set[WorkflowStep] = {step for step, _ in index.content_to_step.values()}
    steps.update(index.job_to_step.values())
    steps.update(index.icj_to_step.values())
    used: set[str] = set()
    for step in steps:
        if step.label:
            used.add(step.label)
        for workflow_output in step.workflow_outputs:
            if workflow_output.label:
                used.add(workflow_output.label)
    return used


def _suggested(trans: ProvidesHistoryContext, content: HistoryItem) -> str | None:
    suggested = suggested_output_name(trans, content)
    return suggested.name if suggested else None


def _generate_label(base: str | None, used: set[str]) -> str:
    label = normalize_generated_label(base) or "label"
    candidate = label
    suffix = 2
    while candidate in used:
        suffix_str = f"_{suffix}"
        candidate = label[: MAX_LABEL_LENGTH - len(suffix_str)] + suffix_str
        suffix += 1
    used.add(candidate)
    return candidate


def _tool_base_name(step: WorkflowStep) -> str:
    tool_id = step.tool_id or "step"
    segments = tool_id.split("/")
    return segments[-2] if len(segments) >= 2 else tool_id
