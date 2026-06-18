"""Carry a notebook page's markdown into an extracted workflow's report.

Extraction (:func:`galaxy.workflow.extract.extract_workflow_by_ids`)
returns an :class:`~galaxy.workflow.extract.ExtractionLabelIndex` mapping the ids
the page references to the labeled workflow steps/outputs it built. This module
turns the page's internal-id markdown into a portable workflow report:

1. :func:`reconcile_report_labels` auto-labels/exposes any referenced item the
   user left unlabeled, so every directive can resolve. This can expose outputs
   the notebook displays but the user did not explicitly star.
2. :class:`_ReportLabelRewriter` does the pure id -> label rewrite against the
   now-complete index, reusing the directive-walk taxonomy and access checks of
   the shared markdown directive handler.

:func:`reconcile_and_build_report` runs both, and is the only entry point the
service needs. It *mutates* the extracted workflow (step labels / workflow
outputs) as a side effect of reconcile -- the caller persists those alongside
the report.
"""

import logging
from typing import Optional

from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.markdown_parse import validate_galaxy_markdown
from galaxy.managers.markdown_util import (
    ENCODED_ID_PATTERN,
    GalaxyInternalMarkdownDirectiveHandler,
    referenced_content_ids,
)
from galaxy.managers.workflow_extraction_naming import (
    normalize_label,
    suggested_output_name,
)
from galaxy.model import (
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    HistoryItem,
    Page,
    WorkflowStep,
)
from galaxy.workflow.extract import (
    _original_hda,
    _original_hdca,
    ExtractionLabelIndex,
)

log = logging.getLogger(__name__)


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
    markdown, warnings = _rewrite_page_markdown(trans, content, index)
    return markdown, referenced.warnings + warnings


def _rewrite_page_markdown(
    trans: ProvidesHistoryContext, internal_markdown: str, index: ExtractionLabelIndex
) -> tuple[str, list[str]]:
    """Rewrite a notebook page's internal markdown into a workflow report.

    Returns the rewritten (label-based) markdown and any warnings for directives
    that had to be dropped. Validates the result so a malformed rewrite fails at
    extraction time rather than at report render.
    """
    rewriter = _ReportLabelRewriter(index)
    markdown = rewriter._walk_directives(trans, internal_markdown)
    validate_galaxy_markdown(markdown)
    return markdown, rewriter.warnings


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
    workflow-relative form (history/workflow/invocation links), is dropped with a
    warning rather than leaked. Id-less directives (instance links, generated
    values, visualizations) pass through unchanged.
    """

    def __init__(self, label_index):
        self.index = label_index
        self.warnings: list[str] = []

    def _rewrite(self, line, arg, description):
        if arg is None:
            self.warnings.append(f"Dropped a {description} from the report: it has no workflow-relative label.")
            return ("", True)
        return (ENCODED_ID_PATTERN.sub(lambda _match: arg, line, count=1), False)

    def _drop_unportable(self, line, description):
        self.warnings.append(f"Dropped a {description} from the report: it cannot be expressed relative to a workflow.")
        return ("", True)

    def _content(self, line, content_kind, content):
        return self._rewrite(line, self.index.content_label_arg(content_kind, content), "dataset reference")

    def handle_dataset_display(self, line, hda):
        return self._content(line, "hda", hda)

    def handle_dataset_as_image(self, line, hda):
        return self._content(line, "hda", hda)

    def handle_dataset_as_table(self, line, hda):
        return self._content(line, "hda", hda)

    def handle_dataset_peek(self, line, hda):
        return self._content(line, "hda", hda)

    def handle_dataset_embedded(self, line, hda):
        return self._content(line, "hda", hda)

    def handle_dataset_info(self, line, hda):
        return self._content(line, "hda", hda)

    def handle_dataset_name(self, line, hda):
        return self._content(line, "hda", hda)

    def handle_dataset_type(self, line, hda):
        return self._content(line, "hda", hda)

    def handle_dataset_collection_display(self, line, hdca):
        return self._content(line, "hdca", hdca)

    def _job(self, line, job):
        return self._rewrite(line, self.index.job_label_arg(job), "job reference")

    def handle_tool_stdout(self, line, job):
        return self._job(line, job)

    def handle_tool_stderr(self, line, job):
        return self._job(line, job)

    def handle_job_metrics(self, line, job):
        return self._job(line, job)

    def handle_job_parameters(self, line, job):
        return self._job(line, job)

    # Id-bearing directives with no workflow-relative form -> dropped with a warning.
    def handle_history_link(self, line, history):
        return self._drop_unportable(line, "history link")

    def handle_workflow_display(self, line, stored_workflow, workflow_version: Optional[int]):
        return self._drop_unportable(line, "workflow display")

    def handle_workflow_image(self, line, stored_workflow, workflow_version: Optional[int]):
        return self._drop_unportable(line, "workflow image")

    def handle_workflow_license(self, line, stored_workflow):
        return self._drop_unportable(line, "workflow license")

    def handle_invocation_time(self, line, invocation):
        return self._drop_unportable(line, "invocation time")

    def handle_invocation_inputs(self, line, invocation):
        return self._drop_unportable(line, "invocation inputs")

    def handle_invocation_outputs(self, line, invocation):
        return self._drop_unportable(line, "invocation outputs")

    # Id-less directives pass through unchanged (the line carries no instance id).
    def handle_generate_galaxy_version(self, line, galaxy_version):
        return (line, False)

    def handle_generate_time(self, line, date):
        return (line, False)

    def handle_instance_access_link(self, line, url):
        return (line, False)

    def handle_instance_resources_link(self, line, url):
        return (line, False)

    def handle_instance_help_link(self, line, url):
        return (line, False)

    def handle_instance_support_link(self, line, url):
        return (line, False)

    def handle_instance_citation_link(self, line, url):
        return (line, False)

    def handle_instance_citation_bibtex(self, line, url):
        return (line, False)

    def handle_instance_terms_link(self, line, url):
        return (line, False)

    def handle_instance_organization_link(self, line, title, url):
        return (line, False)

    def handle_visualization(self, line):
        return (line, False)

    def handle_error(self, container, line, error):
        self.warnings.append(f"Dropped a [{container}] directive from the report: {error}")
        return ("", True)


def reconcile_report_labels(trans: ProvidesHistoryContext, index: ExtractionLabelIndex, referenced) -> None:
    """Ensure every item the page references resolves to a label.

    A referenced tool output the user did not star is exposed as a workflow
    output; a referenced input or step the user did not name is labeled. Labels
    are generated from the same ``suggested_name`` chain the summary surfaces and
    deduped against the shared step/output label namespace. Items outside the
    extracted subgraph are left alone - the pure rewriter drops them with a
    warning so no instance id can leak into the report.
    """
    used = _used_labels(index)

    for kind, content_id in referenced.refs:
        content = _resolve_content(trans, kind, content_id)
        if content is None:
            continue
        original_id = _original_id(kind, content)
        pair = index.step_for_content(kind, original_id)
        if pair is None:
            continue
        step, output_name = pair
        if step.type in ("data_input", "data_collection_input"):
            if not step.label:
                step.label = _generate_label(_suggested(trans, kind, content), used)
        else:
            workflow_output = step.workflow_output_for(output_name)
            if workflow_output is None or not workflow_output.label:
                label = _generate_label(_suggested(trans, kind, content) or output_name, used)
                step.create_or_update_workflow_output(output_name=output_name, label=label, uuid=None)

    for job_id in referenced.job_refs:
        _label_step(index.job_to_step.get(job_id), used)
    for icj_id in referenced.icj_refs:
        _label_step(index.icj_to_step.get(icj_id), used)


def _label_step(step: Optional[WorkflowStep], used: set) -> None:
    if step is None or step.label:
        return
    step.label = _generate_label(_tool_base_name(step), used)


def _used_labels(index: ExtractionLabelIndex) -> set:
    steps: set = {step for step, _ in index.content_to_step.values()}
    steps.update(index.job_to_step.values())
    steps.update(index.icj_to_step.values())
    used: set = set()
    for step in steps:
        if step.label:
            used.add(step.label)
        for workflow_output in step.workflow_outputs:
            if workflow_output.label:
                used.add(workflow_output.label)
    return used


def _suggested(trans: ProvidesHistoryContext, kind: str, content: HistoryItem) -> Optional[str]:
    suggested = suggested_output_name(trans, content.id, "hda" if kind == "hda" else "hdca")
    return suggested.name if suggested else None


def _generate_label(base: Optional[str], used: set) -> str:
    label = normalize_label(base) or "label"
    candidate = label
    suffix = 2
    while candidate in used:
        candidate = f"{label}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _tool_base_name(step: WorkflowStep) -> str:
    tool_id = step.tool_id or "step"
    segments = tool_id.split("/")
    return segments[-2] if len(segments) >= 2 else tool_id


def _resolve_content(trans: ProvidesHistoryContext, kind: str, content_id: int) -> Optional[HistoryItem]:
    model_class = HistoryDatasetCollectionAssociation if kind == "hdca" else HistoryDatasetAssociation
    return trans.sa_session.get(model_class, content_id)


def _original_id(kind: str, content: HistoryItem) -> int:
    if isinstance(content, HistoryDatasetCollectionAssociation):
        return _original_hdca(content).id
    return _original_hda(content).id
