"""Serialize the workflow-extraction summary of a history, optionally seeded from a notebook page's references."""

import logging
from collections import deque
from collections.abc import (
    Iterable,
    Mapping,
    MutableSequence,
)
from dataclasses import (
    dataclass,
    field,
)
from types import MappingProxyType
from typing import (
    cast,
    Literal,
    TYPE_CHECKING,
)

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.markdown_util import referenced_content_ids
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
    ContentRef,
    InvalidWorkflowExtractionJobReason,
    WorkflowExtractionJob,
    WorkflowExtractionOutput,
    WorkflowExtractionSummary,
)
from galaxy.workflow.extract import (
    DatasetCollectionCreationJob,
    FakeJob,
    get_original_hda,
    get_original_hdca,
    original_content_ref,
    resolve_content,
    skip_output_assoc_name,
    summarize,
    tool_for_job,
)

if TYPE_CHECKING:
    from galaxy.tools import Tool

log = logging.getLogger(__name__)

# The job-like keys and dataset lists of :func:`galaxy.workflow.extract.summarize`.
SummaryJob = Job | FakeJob | DatasetCollectionCreationJob
SummaryDatasets = list[tuple[str | None, HistoryItem]]

SEED_AS_INPUT_WARNING = (
    "Referenced by a notebook job directive, but that job is not a workflow step here "
    "(an upload or data fetch, an unavailable tool, or a job from another history whose "
    "inputs are not in this one). It was seeded as a workflow input instead."
)


@dataclass(frozen=True)
class HistoryBoundary:
    """A notebook history and its contents keyed by original-id ref, which decide what counts as produced here."""

    history_id: int
    local_copies: Mapping[ContentRef, HistoryItem]

    @classmethod
    def of(cls, history: History) -> "HistoryBoundary":
        """Keys every content, including the hidden collection elements and non-ready
        datasets the extraction summary leaves out; an undeleted copy is preferred."""
        local_copies: dict[ContentRef, HistoryItem] = {}
        for content in history.all_contents:
            ref = original_content_ref(content)
            if ref not in local_copies or (local_copies[ref].deleted and not content.deleted):
                local_copies[ref] = content
        return cls(history.id, MappingProxyType(local_copies))

    def produced_elsewhere(self, job: Job) -> bool:
        """Whether ``job`` ran in another history and its inputs were not all copied here.

        Such a job is a boundary: its outputs here are workflow inputs. A copied (e.g.
        imported) history keeps its producers as steps because their inputs came along.
        """
        if job.history_id == self.history_id:
            return False
        input_keys = {original_content_ref(content) for content in _job_input_contents(job)}
        return not input_keys or not input_keys <= self.local_copies.keys()


@dataclass
class ClosureResult:
    """Producing jobs/ICJs and original-id content refs reached from a page's references."""

    boundary: HistoryBoundary
    job_ids: set[int] = field(default_factory=set)
    icj_ids: set[int] = field(default_factory=set)
    referenced_output_refs: set[ContentRef] = field(default_factory=set)
    boundary_input_refs: set[ContentRef] = field(default_factory=set)
    content_refs: set[ContentRef] = field(default_factory=set)
    seed_warning_refs: set[ContentRef] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)


def _job_output_contents(job: Job) -> list[HistoryItem]:
    """All of a job's output HDAs/HDCAs, visible or not."""
    contents: list[HistoryItem] = []
    for out_dataset in job.output_datasets:
        if out_dataset.dataset is not None:
            contents.append(out_dataset.dataset)
    for out_collection in job.output_dataset_collection_instances:
        if out_collection.dataset_collection_instance is not None:
            contents.append(out_collection.dataset_collection_instance)
    return contents


def _enqueue_mapped_input_collections(
    output_collection: HistoryDatasetCollectionAssociation, queue: MutableSequence[HistoryItem]
) -> set[str]:
    """Enqueue the input collection(s) a map-over output was mapped over.

    A map output records the collection it was mapped over on itself, not on its
    per-element jobs (whose recorded inputs are individual elements). Enqueue the
    input collection so it is seeded, and return the implicit-input names so the
    matching per-element job inputs are not walked back into as loose datasets.
    """
    names: set[str] = set()
    for implicit_input in output_collection.implicit_input_collections:
        input_collection = implicit_input.input_dataset_collection
        if input_collection is not None:
            if implicit_input.name is not None:
                names.add(implicit_input.name)
            queue.append(input_collection)
    return names


def _job_input_contents(job: Job, mapped_input_names: Iterable[str] = ()) -> list[HistoryItem]:
    """A job's input HDAs/HDCAs; a map step's per-element inputs are folded into the
    collection(s) it was mapped over (as are any inputs named in ``mapped_input_names``)."""
    contents: list[HistoryItem] = []
    names = set(mapped_input_names)
    icj_assoc = job.implicit_collection_jobs_association
    icj = icj_assoc.implicit_collection_jobs if icj_assoc is not None else None
    if icj is not None:
        for output_hdca in icj.output_dataset_collection_instances:
            names |= _enqueue_mapped_input_collections(output_hdca, contents)
    for in_dataset in job.input_datasets:
        if in_dataset.name not in names and in_dataset.dataset is not None:
            contents.append(in_dataset.dataset)
    for in_collection in job.input_dataset_collections:
        if in_collection.dataset_collection is not None:
            contents.append(in_collection.dataset_collection)
    return contents


def _backward_job_closure(
    trans: ProvidesHistoryContext,
    refs: list[ContentRef],
    job_refs: list[int],
    icj_refs: list[int],
    boundary: HistoryBoundary,
) -> ClosureResult:
    """Walk backward from referenced outputs and jobs to their producing subgraph.

    Content ``refs`` are exposed; ``job_refs``/``icj_refs`` seed their subgraph without exposing outputs.
    Stops at boundary inputs: content with no creating job, jobs whose tool is not workflow-compatible,
    and producers ``boundary`` places in another history.
    """
    result = ClosureResult(boundary)
    queue: deque[HistoryItem] = deque()
    for ref in refs:
        content = resolve_content(trans, ref)
        if content is None:
            result.warnings.append(f"A referenced output ({ref[0]} {ref[1]}) is no longer available and was skipped.")
            continue
        result.referenced_output_refs.add(original_content_ref(content))
        queue.append(content)

    for job_id in job_refs:
        job = trans.sa_session.get(Job, job_id)
        if job is None:
            result.warnings.append(f"A referenced job ({job_id}) is no longer available and was skipped.")
            continue
        tool = tool_for_job(trans, job)
        # A directly job-referenced non-step (upload, data fetch, cross-history) becomes a
        # seeded input row; flag its outputs so the form can explain why. An upstream upload
        # reached only by an ordinary walk below is not flagged.
        not_a_step = tool is None or not tool.is_workflow_compatible or boundary.produced_elsewhere(job)
        for content in _job_output_contents(job):
            if not_a_step:
                result.seed_warning_refs.add(original_content_ref(content))
            queue.append(content)

    for icj_id in icj_refs:
        # ICJ ids here were access-checked at collection time (get_accessible_job on the
        # representative job); this bare fetch is safe only for such pre-checked ids. Never pass
        # externally-supplied ICJ ids to _backward_job_closure.
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
        key = original_content_ref(content)
        if key in seen_content:
            continue
        seen_content.add(key)
        result.content_refs.add(key)

        is_collection = key[0] == "hdca"
        original = (
            get_original_hdca(cast(HistoryDatasetCollectionAssociation, content))
            if is_collection
            else get_original_hda(cast(HistoryDatasetAssociation, content))
        )

        creating = original.creating_job_associations
        if not creating:
            result.boundary_input_refs.add(key)
            continue
        if is_collection:
            # A map output has one association per element job; the first represents them all.
            creating = creating[:1]

        produced_in_history = False
        for assoc in creating:
            job = assoc.job
            if boundary.produced_elsewhere(job):
                continue
            produced_in_history = True
            if job.id in seen_jobs:
                continue
            seen_jobs.add(job.id)
            icj_assoc = job.implicit_collection_jobs_association
            if icj_assoc is not None and icj_assoc.implicit_collection_jobs_id in result.icj_ids:
                # Another element job of an already-walked map step.
                continue
            tool = tool_for_job(trans, job)
            if tool is None or not tool.is_workflow_compatible:
                # Upload / data-fetch / missing tool: an input, not a workflow step.
                result.boundary_input_refs.add(key)
                continue
            result.job_ids.add(job.id)
            if icj_assoc is not None:
                result.icj_ids.add(icj_assoc.implicit_collection_jobs_id)
            # Map-over recovery, only for a producer walked as a step: when the walk reaches an
            # implicit output collection, seed the collection it was mapped over (recorded on the
            # output, not on the per-element jobs). _job_input_contents does the same for a walk
            # that arrived via a loose element of the output.
            mapped_input_names: set[str] = set()
            if is_collection:
                mapped_input_names = _enqueue_mapped_input_collections(
                    cast(HistoryDatasetCollectionAssociation, original), queue
                )
            queue.extend(_job_input_contents(job, mapped_input_names))
        if not produced_in_history:
            result.boundary_input_refs.add(key)

    return result


def _icj_assoc_by_job_id(
    trans: ProvidesHistoryContext, jobs: Iterable[SummaryJob]
) -> dict[int, ImplicitCollectionJobsJobAssociation]:
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
    output_name: str | None = None,
    *,
    exposed: bool = False,
    referenced_by_report: bool = False,
) -> WorkflowExtractionOutput:
    suggested = suggested_output_name(trans, content) if output_name is not None else None
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
            "referenced_by_report": referenced_by_report,
        }
    )


def _input_step_type(outputs: list[WorkflowExtractionOutput]) -> Literal["input_dataset", "input_collection"]:
    if outputs and outputs[0].history_content_type == "dataset_collection":
        return "input_collection"
    return "input_dataset"


def _workflow_output_name(content: HistoryItem, output_name: str | None) -> str | None:
    if output_name and skip_output_assoc_name(output_name):
        return None
    if content.history_content_type == "dataset_collection":
        return getattr(content, "implicit_output_name", None) or output_name
    return output_name


def _input_extraction_row(
    trans: ProvidesHistoryContext,
    datasets: SummaryDatasets,
    *,
    seeded: bool,
    tool_name: str | None,
    seed_warning: str | None = None,
) -> WorkflowExtractionJob:
    """A non-step input row: a FakeJob/DatasetCollectionCreationJob, a job whose
    tool is not workflow-compatible (upload, data fetch), a boundary cross-history
    producer, or a synthesized boundary input."""
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


def _input_seeding(datasets: SummaryDatasets, closure: ClosureResult | None) -> tuple[bool, str | None]:
    """``(seeded, seed_warning)`` for an input row holding ``datasets``."""
    if closure is None:
        return False, None
    content_keys = {original_content_ref(data) for _, data in datasets}
    seed_warning = SEED_AS_INPUT_WARNING if content_keys & closure.seed_warning_refs else None
    return bool(content_keys & closure.content_refs), seed_warning


def _report_referenced_outputs(datasets: SummaryDatasets, referenced: set[ContentRef]) -> set[int]:
    """Indices of ``datasets`` the report uses: one per referenced original, preferring it over in-history copies."""
    chosen: dict[ContentRef, int] = {}
    for index, (_, data) in enumerate(datasets):
        ref = original_content_ref(data)
        if ref in referenced and (ref not in chosen or data.id == ref[1]):
            chosen[ref] = index
    return set(chosen.values())


def _tool_row(
    trans: ProvidesHistoryContext,
    job: Job,
    tool: "Tool | None",
    datasets: SummaryDatasets,
    icj_assoc_by_job_id: dict[int, ImplicitCollectionJobsJobAssociation],
    closure: ClosureResult | None,
) -> WorkflowExtractionJob:
    """A workflow step row, or an invalid one when ``tool`` is missing or inaccessible."""
    referenced = _report_referenced_outputs(datasets, closure.referenced_output_refs if closure else set())
    tool_outputs = [
        _serialize_output(
            trans,
            data,
            _workflow_output_name(data, output_name),
            exposed=index in referenced,
            referenced_by_report=index in referenced,
        )
        for index, (output_name, data) in enumerate(datasets)
    ]

    if tool is None:
        invalid_reason = (
            InvalidWorkflowExtractionJobReason.CUSTOM_TOOL_INACCESSIBLE
            if job.dynamic_tool is not None
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


def _synthesize_boundary_inputs(
    trans: ProvidesHistoryContext,
    represented_keys: set[ContentRef],
    closure: ClosureResult,
) -> list[WorkflowExtractionJob]:
    """Seeded input rows for boundary inputs not already in ``represented_keys`` (both original-id refs).

    A row lists the history's own copy when there is one: the original may sit in a history
    the user can no longer access.
    """
    synthesized: list[WorkflowExtractionJob] = []
    for ref in sorted(closure.boundary_input_refs):
        if ref in represented_keys:
            continue
        content = closure.boundary.local_copies.get(ref)
        if content is None:
            content = resolve_content(trans, ref)
        if content is None:
            continue
        seed_warning = SEED_AS_INPUT_WARNING if ref in closure.seed_warning_refs else None
        synthesized.append(
            _input_extraction_row(trans, [(None, content)], seeded=True, tool_name=None, seed_warning=seed_warning)
        )
    return synthesized


def _input_producer_name(
    job: SummaryJob, tool: "Tool | None", closure: ClosureResult | None
) -> tuple[bool, str | None]:
    """Whether ``job``'s outputs here are workflow inputs rather than step outputs, and the
    producer name their input row shows: a FakeJob/DatasetCollectionCreationJob, a tool that is
    not workflow-compatible (upload, data fetch), or a producer in another history."""
    if not isinstance(job, Job):
        return True, getattr(job, "name", None)
    if closure is not None and closure.boundary.produced_elsewhere(job):
        return True, tool.name if tool else None
    if tool is not None and not tool.is_workflow_compatible:
        return True, tool.name
    return False, None


def _collections_by_original(history: History) -> dict[ContentRef, SummaryDatasets]:
    """``history``'s collections keyed by their original's ref.

    ``summarize`` records a copied collection as its original, which may sit in a history
    the user can no longer access; input rows list these in-history collections instead.
    """
    collections: dict[ContentRef, SummaryDatasets] = {}
    for hdca in history.contents_iter(types=["dataset_collection"]):
        collections.setdefault(original_content_ref(hdca), []).append((None, hdca))
    return collections


def _summary_rows(
    trans: ProvidesHistoryContext,
    history: History,
    jobs: dict[SummaryJob, SummaryDatasets],
    closure: ClosureResult | None,
) -> list[tuple[WorkflowExtractionJob, SummaryDatasets]]:
    """One row per step job, and one input row per original that non-step jobs left here,
    listing its in-history copies: extraction makes all copies of one original a single input.
    Each row is paired with the datasets it holds."""
    icj_assoc_by_job_id = _icj_assoc_by_job_id(trans, jobs)
    collections_here = _collections_by_original(history)
    # Input rows are filled in once all their copies are known; None marks their place.
    pending: list[tuple[WorkflowExtractionJob | None, SummaryDatasets, str | None]] = []
    inputs: dict[ContentRef, SummaryDatasets] = {}
    for job, datasets in jobs.items():
        tool = tool_for_job(trans, job) if isinstance(job, Job) else None
        is_input, producer_name = _input_producer_name(job, tool, closure)
        if not is_input:
            pending.append(
                (_tool_row(trans, cast(Job, job), tool, datasets, icj_assoc_by_job_id, closure), datasets, None)
            )
            continue
        for item in datasets:
            ref = original_content_ref(item[1])
            copies = inputs.get(ref)
            if copies is None:
                copies = inputs[ref] = []
                pending.append((None, copies, producer_name))
            for copy in collections_here.get(ref, [item]):
                if all(data.id != copy[1].id for _, data in copies):
                    copies.append(copy)
    rows: list[tuple[WorkflowExtractionJob, SummaryDatasets]] = []
    for row, datasets, producer_name in pending:
        if row is None:
            seeded, seed_warning = _input_seeding(datasets, closure)
            row = _input_extraction_row(
                trans, datasets, seeded=seeded, tool_name=producer_name, seed_warning=seed_warning
            )
        rows.append((row, datasets))
    return rows


def _serialize_summary(
    trans: ProvidesHistoryContext,
    history: History,
    jobs: dict[SummaryJob, SummaryDatasets],
    warnings: Iterable[str],
    closure: ClosureResult | None = None,
) -> WorkflowExtractionSummary:
    """With ``closure`` (page path), rows in the producing subgraph are flagged
    ``seeded`` and referenced outputs ``exposed``; boundary inputs not already
    present as input or seeded rows are synthesized as input rows."""
    rows = _summary_rows(trans, history, jobs, closure)
    jobs_list = [row for row, _ in rows]
    all_warnings = list(warnings)
    if closure is not None:
        # An unseeded tool row (e.g. an invalid one) does not feed the seeded subgraph.
        represented_keys = {
            original_content_ref(data)
            for row, datasets in rows
            if row.seeded or row.step_type != "tool"
            for _, data in datasets
        }
        jobs_list.extend(_synthesize_boundary_inputs(trans, represented_keys, closure))
        all_warnings.extend(closure.warnings)

    return WorkflowExtractionSummary.model_validate(
        {
            "history_id": history.id,
            "warnings": all_warnings,
            "jobs": jobs_list,
        }
    )


def build_extraction_summary(trans: ProvidesHistoryContext, history: History) -> WorkflowExtractionSummary:
    """Serialize the whole-history extraction summary."""
    jobs, warnings = summarize(trans, history)
    return _serialize_summary(trans, history, jobs, warnings)


def summary_from_page(trans: ProvidesHistoryContext, page: Page, history: History) -> WorkflowExtractionSummary:
    """Extraction summary for a notebook page's ``history``, seeded from the outputs the page references."""
    revision = page.latest_revision
    content = revision.content if revision is not None else None
    referenced = referenced_content_ids(trans, content or "")
    jobs, warnings = summarize(trans, history)
    closure = _backward_job_closure(
        trans, referenced.refs, referenced.job_refs, referenced.icj_refs, HistoryBoundary.of(history)
    )
    closure.warnings = referenced.warnings + closure.warnings
    return _serialize_summary(trans, history, jobs, warnings, closure)
