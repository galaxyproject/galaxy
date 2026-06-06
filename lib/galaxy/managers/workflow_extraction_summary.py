"""Build the workflow-extraction summary for a history or a page/notebook.

The summary is the flat, whole-history list of jobs that
:func:`galaxy.workflow.extract.summarize` produces, serialized into the
``WorkflowExtractionSummary`` schema. This module owns that serialization so
both the history endpoint (plain summary) and the page endpoint (summary with a
seeded producing subgraph) share one builder.

For a page, the datasets/collections the page's markdown references are walked
backward through job provenance (:func:`_backward_job_closure`) to mark the
producing jobs as ``seeded`` and the referenced outputs as ``exposed``.
"""

import logging
from collections import deque
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    cast,
    Literal,
    Optional,
)

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from galaxy.exceptions import InsufficientPermissionsException
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.markdown_util import (
    ContentRef,
    referenced_content_ids,
)
from galaxy.managers.workflow_extraction_naming import suggested_output_name
from galaxy.model import (
    History,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    HistoryItem,
    ImplicitCollectionJobs,
    ImplicitCollectionJobsJobAssociation,
    Job,
    Page,
)
from galaxy.schema.workflows import (
    InvalidWorkflowExtractionJobReason,
    WorkflowExtractionJob,
    WorkflowExtractionOutput,
    WorkflowExtractionSummary,
)
from galaxy.workflow.extract import (
    _original_hda,
    _original_hdca,
    _skip_output_assoc_name,
    summarize,
)

log = logging.getLogger(__name__)

SEED_AS_INPUT_WARNING = (
    "Referenced by a notebook job directive, but its tool is not a workflow step "
    "(e.g. an upload or data fetch). It was seeded as a workflow input instead."
)


@dataclass
class ClosureResult:
    """Result of walking backward from a page's referenced outputs.

    Identity-space-neutral content refs plus the producing job/ICJ ids the
    summary uses to flag ``seeded`` rows. Keeping content refs here lets a
    future graph view hydrate the same highlight set from the same endpoint.
    """

    job_ids: set[int] = field(default_factory=set)
    icj_ids: set[int] = field(default_factory=set)
    referenced_output_refs: set[ContentRef] = field(default_factory=set)
    boundary_input_refs: set[ContentRef] = field(default_factory=set)
    content_refs: set[ContentRef] = field(default_factory=set)
    seed_warning_refs: set[ContentRef] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)


def _content_key(content: HistoryItem) -> ContentRef:
    """Normalize a history item to ``(kind, original_id)`` after following copies."""
    if content.history_content_type == "dataset_collection":
        return ("hdca", _original_hdca(cast(HistoryDatasetCollectionAssociation, content)).id)
    return ("hda", _original_hda(cast(HistoryDatasetAssociation, content)).id)


def _resolve_content(trans: ProvidesHistoryContext, ref: ContentRef) -> Optional[HistoryItem]:
    kind, id_ = ref
    model_class = HistoryDatasetCollectionAssociation if kind == "hdca" else HistoryDatasetAssociation
    return trans.sa_session.get(model_class, id_)


def _tool_for_job(trans: ProvidesHistoryContext, job: Job):
    try:
        return trans.app.toolbox.tool_for_job(job, user=trans.user)
    except InsufficientPermissionsException:
        return None


def _job_output_contents(job: Job) -> list[HistoryItem]:
    """All of a job's output HDAs/HDCAs (visible or not).

    Seeding re-derives the producing job from any one output's
    ``creating_job_associations``, so visibility does not affect correctness.
    """
    contents: list[HistoryItem] = []
    for out_dataset in job.output_datasets:
        if out_dataset.dataset is not None:
            contents.append(out_dataset.dataset)
    for out_collection in job.output_dataset_collection_instances:
        if out_collection.dataset_collection_instance is not None:
            contents.append(out_collection.dataset_collection_instance)
    return contents


def _backward_job_closure(
    trans: ProvidesHistoryContext,
    refs: list[ContentRef],
    job_refs: list[int],
    icj_refs: list[int],
    history_id: int,
) -> ClosureResult:
    """Walk backward from each referenced output to its producing subgraph.

    Content ``refs`` are the page's displayed outputs: walked and marked exposed.
    ``job_refs`` / ``icj_refs`` are jobs a notebook references via a job directive
    (stdout/stderr/metrics/parameters); they seed their producing subgraph but
    their outputs are *not* exposed. They are folded into the same backward walk
    by enqueueing the referenced job's outputs unexposed.

    Stops at boundary inputs: datasets with no creating job, jobs whose tool is
    not workflow-compatible (upload, data fetch, ...), and cross-history
    producers. Within-history copies are followed via the original HDA/HDCA.
    Producers are resolved per-seed (no batched queries) for V1.
    """
    result = ClosureResult()
    queue: deque[HistoryItem] = deque()
    for ref in refs:
        content = _resolve_content(trans, ref)
        if content is None:
            result.warnings.append(f"A referenced output ({ref[0]} {ref[1]}) is no longer available and was skipped.")
            continue
        result.referenced_output_refs.add(_content_key(content))
        queue.append(content)

    for job_id in job_refs:
        job = trans.sa_session.get(Job, job_id)
        if job is None:
            result.warnings.append(f"A referenced job ({job_id}) is no longer available and was skipped.")
            continue
        tool = _tool_for_job(trans, job)
        # A directly job-referenced non-step (upload, data fetch, cross-history) becomes a
        # seeded input row; flag its outputs so the form can explain why. An upstream upload
        # reached only by an ordinary walk below is not flagged.
        not_a_step = tool is None or not tool.is_workflow_compatible or job.history_id != history_id
        for content in _job_output_contents(job):
            if not_a_step:
                result.seed_warning_refs.add(_content_key(content))
            queue.append(content)

    for icj_id in icj_refs:
        # Access was enforced at the collector via Phase-1's get_accessible_job before this id
        # entered icj_refs; this bare fetch is safe only under that precondition. Do not call
        # _backward_job_closure with an externally-supplied, unchecked ICJ id.
        icj = trans.sa_session.get(ImplicitCollectionJobs, icj_id)
        if icj is None:
            result.warnings.append(f"A referenced collection job ({icj_id}) is no longer available and was skipped.")
            continue
        for hdca in icj.output_dataset_collection_instances:
            queue.append(hdca)

    seen_content: set[ContentRef] = set()
    seen_jobs: set[int] = set()
    while queue:
        content = queue.popleft()
        key = _content_key(content)
        if key in seen_content:
            continue
        seen_content.add(key)
        result.content_refs.add(key)

        is_collection = key[0] == "hdca"
        original = (
            _original_hdca(cast(HistoryDatasetCollectionAssociation, content))
            if is_collection
            else _original_hda(cast(HistoryDatasetAssociation, content))
        )

        # Map-over: an implicit output collection records the collection(s) it was
        # mapped over on itself, not on the per-element jobs (whose recorded inputs
        # are individual elements). Recover those at the collection level so the
        # input collection is seeded, and remember their names so the matching
        # per-element job inputs below are not walked back into as loose datasets.
        mapped_input_names: set[str] = set()
        if is_collection:
            for implicit_input in cast(HistoryDatasetCollectionAssociation, original).implicit_input_collections:
                input_collection = implicit_input.input_dataset_collection
                if input_collection is not None:
                    if implicit_input.name is not None:
                        mapped_input_names.add(implicit_input.name)
                    queue.append(input_collection)

        creating = original.creating_job_associations
        if not creating:
            result.boundary_input_refs.add(key)
            continue

        produced_in_history = False
        for assoc in creating:
            job = assoc.job
            if job.history_id != history_id:
                # Cross-history producer: treat the content as a boundary input.
                continue
            produced_in_history = True
            if job.id in seen_jobs:
                continue
            seen_jobs.add(job.id)
            tool = _tool_for_job(trans, job)
            if tool is None or not tool.is_workflow_compatible:
                # Upload / data-fetch / missing tool: an input, not a workflow step.
                result.boundary_input_refs.add(key)
                continue
            result.job_ids.add(job.id)
            icj_assoc = job.implicit_collection_jobs_association
            if icj_assoc is not None:
                result.icj_ids.add(icj_assoc.implicit_collection_jobs_id)
            for in_dataset in job.input_datasets:
                if in_dataset.name in mapped_input_names:
                    # Folded into a mapped input collection already queued above.
                    continue
                if in_dataset.dataset is not None:
                    queue.append(in_dataset.dataset)
            for in_collection in job.input_dataset_collections:
                if in_collection.dataset_collection is not None:
                    queue.append(in_collection.dataset_collection)
        if not produced_in_history:
            result.boundary_input_refs.add(key)

    return result


def _icj_assoc_by_job_id(trans: ProvidesHistoryContext, jobs) -> dict:
    representative_job_ids = [job.id for job in jobs if isinstance(job, Job)]
    if not representative_job_ids:
        return {}
    stmt = (
        select(ImplicitCollectionJobsJobAssociation)
        .options(
            selectinload(ImplicitCollectionJobsJobAssociation.implicit_collection_jobs).selectinload(
                ImplicitCollectionJobs.jobs
            )
        )
        .where(ImplicitCollectionJobsJobAssociation.job_id.in_(representative_job_ids))
    )
    return {icj_assoc.job_id: icj_assoc for icj_assoc in trans.sa_session.scalars(stmt).unique().all()}


def _serialize_output(
    trans: ProvidesHistoryContext,
    content: HistoryItem,
    output_name: Optional[str] = None,
    *,
    exposed: bool = False,
) -> WorkflowExtractionOutput:
    suggested = None
    if output_name is not None:
        content_kind: Literal["hda", "hdca"] = "hdca" if content.history_content_type == "dataset_collection" else "hda"
        suggested = suggested_output_name(trans, content.id, content_kind)
    return WorkflowExtractionOutput.model_validate(
        {
            "id": content.id,
            "hid": content.hid,
            "name": content.name,
            "state": content.state,
            "deleted": content.deleted,
            "history_content_type": content.history_content_type,
            "output_name": output_name,
            "suggested_name": suggested.name if suggested else None,
            "suggested_name_source": suggested.source if suggested else None,
            "exposed": exposed,
        }
    )


def _input_step_type(outputs: list[WorkflowExtractionOutput]) -> Literal["input_dataset", "input_collection"]:
    if outputs and outputs[0].history_content_type == "dataset_collection":
        return "input_collection"
    return "input_dataset"


def _workflow_output_name(content: HistoryItem, output_name: Optional[str]) -> Optional[str]:
    if output_name and _skip_output_assoc_name(output_name):
        return None
    if content.history_content_type == "dataset_collection":
        return getattr(content, "implicit_output_name", None) or output_name
    return output_name


def _input_extraction_row(
    trans: ProvidesHistoryContext,
    job,
    datasets: list,
    *,
    seeded: bool,
    tool_name: Optional[str],
    seed_warning: Optional[str] = None,
) -> WorkflowExtractionJob:
    """A non-step input row: a FakeJob/DatasetCollectionCreationJob, or a job
    whose tool is not workflow-compatible (upload, data fetch)."""
    outputs = [_serialize_output(trans, data) for _, data in datasets]
    checked = any(not data.deleted for _, data in datasets)
    return WorkflowExtractionJob(
        id=None,
        step_type=_input_step_type(outputs),
        tool_name=tool_name,
        tool_id=None,
        tool_version=None,
        checked=checked,
        seeded=seeded,
        tool_version_warning=None,
        seed_warning=seed_warning,
        outputs=outputs,
        invalid=None,
    )


def _extraction_row(
    trans: ProvidesHistoryContext,
    job,
    datasets: list,
    icj_assoc_by_job_id: dict,
    closure: Optional[ClosureResult],
) -> WorkflowExtractionJob:
    referenced = closure.referenced_output_refs if closure else set()
    content_keys = {_content_key(data) for _, data in datasets}
    input_seeded = bool(closure and (content_keys & closure.content_refs))
    seed_warning = SEED_AS_INPUT_WARNING if closure and (content_keys & closure.seed_warning_refs) else None

    if getattr(job, "is_fake", False):
        # FakeJob / DatasetCollectionCreationJob: input with no creating tool.
        return _input_extraction_row(
            trans,
            job,
            datasets,
            seeded=input_seeded,
            tool_name=getattr(job, "name", None),
            seed_warning=seed_warning,
        )

    custom_tools_inaccessible = False
    try:
        tool = trans.app.toolbox.tool_for_job(job, user=trans.user)
    except InsufficientPermissionsException:
        tool = None
        custom_tools_inaccessible = True

    tool_outputs = [
        _serialize_output(
            trans, data, _workflow_output_name(data, output_name), exposed=_content_key(data) in referenced
        )
        for output_name, data in datasets
    ]

    if tool is None:
        invalid_reason = (
            InvalidWorkflowExtractionJobReason.CUSTOM_TOOL_INACCESSIBLE
            if custom_tools_inaccessible
            else InvalidWorkflowExtractionJobReason.TOOL_MISSING_OR_INACCESSIBLE
        )
        return WorkflowExtractionJob(
            id=job.id,
            step_type="tool",
            tool_name=None,
            tool_id=job.tool_id,
            tool_version=job.tool_version,
            checked=False,
            # The closure classifies a missing/inaccessible producer as a boundary input, so its job
            # id never enters job_ids; an invalid row is never seeded (and could not be extracted).
            seeded=False,
            tool_version_warning=None,
            outputs=tool_outputs,
            invalid=invalid_reason,
        )

    if not tool.is_workflow_compatible:
        # Not a workflow step (e.g. upload, data fetch) — treat as input.
        return _input_extraction_row(
            trans, job, datasets, seeded=input_seeded, tool_name=tool.name, seed_warning=seed_warning
        )

    tool_version_warning = (
        (
            f'Dataset was created with tool version "{job.tool_version}", '
            f'but workflow extraction will use version "{tool.version}".'
        )
        if tool.version != job.tool_version
        else None
    )
    icj_assoc = icj_assoc_by_job_id.get(job.id)
    implicit_collection_jobs = icj_assoc.implicit_collection_jobs if icj_assoc is not None else None
    icj_id = icj_assoc.implicit_collection_jobs_id if icj_assoc is not None else None
    checked = any(not data.deleted for _, data in datasets)
    seeded = bool(closure and (job.id in closure.job_ids or (icj_id is not None and icj_id in closure.icj_ids)))
    return WorkflowExtractionJob(
        id=job.id,
        step_type="tool",
        tool_name=tool.name,
        tool_id=job.tool_id,
        tool_version=job.tool_version,
        checked=checked,
        seeded=seeded,
        tool_version_warning=tool_version_warning,
        outputs=tool_outputs,
        invalid=None,
        implicit_collection_jobs_id=icj_id,
        implicit_collection_jobs_size=(
            len(implicit_collection_jobs.jobs) if implicit_collection_jobs is not None else None
        ),
    )


def _synthesize_cross_history_inputs(
    trans: ProvidesHistoryContext,
    represented_keys: set[ContentRef],
    closure: ClosureResult,
) -> list[WorkflowExtractionJob]:
    """Boundary inputs the whole-history summary did not already surface as rows
    (e.g. cross-history datasets) become synthetic input rows so they are not
    silently dropped from the seeded set.

    ``represented_keys`` is in the same original-id space as
    ``closure.boundary_input_refs`` (both via :func:`_content_key`)."""
    synthesized: list[WorkflowExtractionJob] = []
    for ref in sorted(closure.boundary_input_refs):
        if ref in represented_keys:
            continue
        content = _resolve_content(trans, ref)
        if content is None:
            continue
        seed_warning = SEED_AS_INPUT_WARNING if ref in closure.seed_warning_refs else None
        synthesized.append(
            _input_extraction_row(
                trans, content, [(None, content)], seeded=True, tool_name=None, seed_warning=seed_warning
            )
        )
    return synthesized


def build_extraction_summary(
    trans: ProvidesHistoryContext, history: History, *, closure: Optional[ClosureResult] = None
) -> WorkflowExtractionSummary:
    """Serialize the whole-history extraction summary.

    With ``closure`` (page path), rows in the producing subgraph are flagged
    ``seeded`` and referenced outputs ``exposed``; cross-history boundary inputs
    not already present are synthesized as input rows.
    """
    jobs, warnings = summarize(trans, history)
    icj_assoc_by_job_id = _icj_assoc_by_job_id(trans, jobs)

    jobs_list = [_extraction_row(trans, job, datasets, icj_assoc_by_job_id, closure) for job, datasets in jobs.items()]
    all_warnings = list(warnings)
    if closure is not None:
        represented_keys = {_content_key(data) for datasets in jobs.values() for _, data in datasets}
        jobs_list.extend(_synthesize_cross_history_inputs(trans, represented_keys, closure))
        all_warnings.extend(closure.warnings)

    return WorkflowExtractionSummary.model_validate(
        {
            "history_id": history.id,
            "warnings": all_warnings,
            "jobs": jobs_list,
        }
    )


def summary_from_page(trans: ProvidesHistoryContext, page: Page) -> WorkflowExtractionSummary:
    """Extraction summary for a notebook page, seeded from the outputs it references."""
    history = page.history
    assert history is not None, "summary_from_page requires a history-attached page"
    revision = page.latest_revision
    content = revision.content if revision is not None else None
    referenced = referenced_content_ids(trans, content or "")
    closure = _backward_job_closure(trans, referenced.refs, referenced.job_refs, referenced.icj_refs, history.id)
    closure.warnings = referenced.warnings + closure.warnings
    return build_extraction_summary(trans, history, closure=closure)
