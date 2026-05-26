"""This module contains functionality to aid in extracting workflows from
histories.
"""

import logging
from collections.abc import Callable
from typing import (
    Any,
    cast,
    Literal,
    Optional,
)

from galaxy import (
    exceptions,
    model,
)
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.jobs import JobManager
from galaxy.model import (
    History,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    HistoryItem,
    ImplicitCollectionJobs,
    Job,
    StoredWorkflow,
    User,
    WorkflowStep,
)
from galaxy.model.base import ensure_object_added_to_session
from galaxy.tool_util.parser import ToolOutputCollectionPart
from galaxy.tools.parameters.basic import (
    DataCollectionToolParameter,
    DataToolParameter,
)
from galaxy.tools.parameters.grouping import (
    Conditional,
    Repeat,
    Section,
)
from galaxy.util import listify
from .steps import (
    attach_ordered_steps,
    order_workflow_steps_with_levels,
)

# Type alias for tool input parameter values (param name -> string value)
ToolInputs = dict[str, Any]

# Type alias for data input associations (hid, input_name) pairs linking
# history items to their corresponding tool input parameters
DataInputAssociations = list[tuple[int, str]]

log = logging.getLogger(__name__)

WARNING_SOME_DATASETS_NOT_READY = "Some datasets still queued or running were ignored"


def _skip_output_assoc_name(name: str) -> bool:
    """True for job-output-association names that aren't workflow-visible
    outputs (named-collection-part placeholders and discovered-primary-file
    rows). Both extraction paths skip these."""
    return ToolOutputCollectionPart.is_named_collection_part_name(name) or name.startswith("__new_primary_file")


def _connect(step: WorkflowStep, input_name: str, source: tuple[WorkflowStep, str]) -> None:
    """Wire ``step``'s ``input_name`` to ``source`` (output_step, output_name).
    The source is always an earlier step - a job only consumes outputs of jobs
    that ran before it. Shared by both extraction paths."""
    source_step, source_name = source
    conn = model.WorkflowStepConnection()
    conn.input_step_input = step.get_or_add_input(input_name)
    conn.output_step = source_step
    conn.output_name = source_name


def extract_workflow(
    trans: ProvidesHistoryContext,
    user: User,
    history: Optional[History] = None,
    job_ids: Optional[list[int]] = None,
    dataset_ids: Optional[list[int]] = None,
    dataset_collection_ids: Optional[list[int]] = None,
    workflow_name: Optional[str] = None,
    dataset_names: Optional[list[str]] = None,
    dataset_collection_names: Optional[list[str]] = None,
) -> StoredWorkflow:
    steps = extract_steps(
        trans,
        history=history,
        job_ids=job_ids,
        dataset_ids=dataset_ids,
        dataset_collection_ids=dataset_collection_ids,
        dataset_names=dataset_names,
        dataset_collection_names=dataset_collection_names,
    )
    return _finalize_workflow(trans, user, workflow_name, steps)


def _finalize_workflow(
    trans: ProvidesHistoryContext,
    user: User,
    workflow_name: Optional[str],
    steps: list[WorkflowStep],
) -> StoredWorkflow:
    workflow = model.Workflow()
    workflow.name = workflow_name
    workflow.steps = steps
    attach_ordered_steps(workflow)
    levorder = order_workflow_steps_with_levels(steps)
    base_pos = 10
    for i, steps_at_level in enumerate(levorder):
        for j, index in enumerate(steps_at_level):
            step = steps[index]
            step.position = dict(top=(base_pos + 120 * j), left=(base_pos + 220 * i))
    stored = model.StoredWorkflow()
    stored.user = user
    stored.name = workflow_name
    workflow.stored_workflow = stored
    stored.latest_workflow = workflow
    trans.sa_session.add(stored)
    ensure_object_added_to_session(workflow, session=trans.sa_session)
    trans.sa_session.commit()
    return stored


def extract_steps(
    trans: ProvidesHistoryContext,
    history: Optional[History] = None,
    job_ids: Optional[list[int]] = None,
    dataset_ids: Optional[list[int]] = None,
    dataset_collection_ids: Optional[list[int]] = None,
    dataset_names: Optional[list[str]] = None,
    dataset_collection_names: Optional[list[str]] = None,
) -> list[WorkflowStep]:
    # Ensure job_ids and dataset_ids are lists (possibly empty)
    job_ids = listify(job_ids)
    dataset_ids = listify(dataset_ids)
    dataset_collection_ids = listify(dataset_collection_ids)
    # Convert both sets of ids to integers
    job_ids = [int(_) for _ in job_ids]
    dataset_ids = [int(_) for _ in dataset_ids]
    dataset_collection_ids = [int(_) for _ in dataset_collection_ids]
    # Find each job, for security we (implicitly) check that they are
    # associated with a job in the current history.
    summary = WorkflowSummary(trans, history)
    jobs = summary.jobs
    steps = []
    step_labels = set()
    hid_to_output_pair = {}
    # Input dataset steps
    for i, input_hid in enumerate(dataset_ids):
        step = model.WorkflowStep()
        step.type = "data_input"
        if dataset_names:
            name = dataset_names[i]
        else:
            name = "Input Dataset"
        if name not in step_labels:
            step.label = name
            step_labels.add(name)
        step.tool_inputs = dict(name=name)
        hid_to_output_pair[input_hid] = (step, "output")
        steps.append(step)
    for i, input_hid in enumerate(dataset_collection_ids):
        step = model.WorkflowStep()
        step.type = "data_collection_input"
        if input_hid not in summary.collection_types:
            raise exceptions.RequestParameterInvalidException(f"hid {input_hid} does not appear to be a collection")
        collection_type = summary.collection_types[input_hid]
        if dataset_collection_names:
            name = dataset_collection_names[i]
        else:
            name = "Input Dataset Collection"
        if name not in step_labels:
            step.label = name
            step_labels.add(name)
        step.tool_inputs = dict(name=name, collection_type=collection_type)
        hid_to_output_pair[input_hid] = (step, "output")
        steps.append(step)
    # Tool steps
    for job_id in job_ids:
        if job_id not in summary.job_id2representative_job:
            log.warning(f"job_id {job_id} not found in job_id2representative_job {summary.job_id2representative_job}")
            raise AssertionError("Attempt to create workflow with job not connected to current history")
        job = summary.job_id2representative_job[job_id]
        tool_inputs, associations = step_inputs(trans, job)
        step = model.WorkflowStep()
        step.type = "tool"
        step.tool_id = job.tool_id
        step.tool_version = job.tool_version
        step.tool_inputs = tool_inputs
        if job.dynamic_tool_id:
            step.dynamic_tool_id = job.dynamic_tool_id
        # NOTE: We shouldn't need to do two passes here since only
        #       an earlier job can be used as an input to a later
        #       job.
        for other_hid, input_name in associations:
            if job in summary.implicit_map_jobs:
                an_implicit_output_collection = cast(HistoryDatasetCollectionAssociation, jobs[job][0][1])
                input_collection = an_implicit_output_collection.find_implicit_input_collection(input_name)
                if input_collection:
                    other_hid = input_collection.hid
                else:
                    log.info(f"Cannot find implicit input collection for {input_name}")
            if other_hid in hid_to_output_pair:
                _connect(step, input_name, hid_to_output_pair[other_hid])
        steps.append(step)
        # Store created dataset hids
        for assoc in job.output_datasets + job.output_dataset_collection_instances:
            assoc_name = assoc.name
            if _skip_output_assoc_name(assoc_name):
                continue
            if job in summary.implicit_map_jobs:
                hid: Optional[int] = None
                for implicit_pair in jobs[job]:
                    query_assoc_name, dataset_collection = implicit_pair
                    if query_assoc_name == assoc_name or assoc_name.startswith(
                        f"__new_primary_file_{query_assoc_name}|"
                    ):
                        hid = summary.hid(dataset_collection)
                if hid is None:
                    template = (
                        "Failed to find matching implicit job - job id is %s, implicit pairs are %s, assoc_name is %s."
                    )
                    message = template % (job.id, jobs[job], assoc_name)
                    log.warning(message)
                    raise Exception("Failed to extract job.")
            else:
                if hasattr(assoc, "dataset"):
                    has_hid = assoc.dataset
                else:
                    has_hid = assoc.dataset_collection_instance
                hid = summary.hid(has_hid)
            if hid in hid_to_output_pair:
                log.warning(f"duplicate hid found in extract_steps [{hid}]")
            hid_to_output_pair[hid] = (step, assoc.name)
    return steps


class FakeJob:
    """
    Fake job object for datasets that have no creating_job_associations,
    they will be treated as "input" datasets.
    """

    def __init__(self, dataset: HistoryDatasetAssociation) -> None:
        self.is_fake = True
        self.id = f"fake_{dataset.id}"
        self.name = self._guess_name_from_dataset(dataset)

    def _guess_name_from_dataset(self, dataset: HistoryDatasetAssociation) -> Optional[str]:
        """Tries to guess the name of the fake job from the dataset associations."""
        if dataset.copied_from_history_dataset_association:
            return "Import from History"
        if dataset.copied_from_library_dataset_dataset_association:
            return "Import from Library"
        return None


class DatasetCollectionCreationJob:
    def __init__(self, dataset_collection: HistoryDatasetCollectionAssociation) -> None:
        self.is_fake = True
        self.id = f"fake_{dataset_collection.id}"
        self.from_jobs: Optional[list[Job]] = None
        self.name = "Dataset Collection Creation"
        self.disabled_why = "Dataset collection created in a way not compatible with workflows"

    def set_jobs(self, jobs: list[Job]) -> None:
        assert jobs is not None
        self.from_jobs = jobs


def summarize(
    trans: ProvidesHistoryContext, history: Optional[History] = None
) -> tuple[dict[Any, list[tuple[Optional[str], HistoryItem]]], set[str]]:
    """Return mapping of job description to datasets for active items in
    supplied history - needed for building workflow from a history.

    Formerly call get_job_dict in workflow web controller.
    """
    summary = WorkflowSummary(trans, history)
    return summary.jobs, summary.warnings


class BaseWorkflowSummary:
    """Shared helpers for workflow extraction summaries (HID-based and ID-based)."""

    def __init__(self, trans: ProvidesHistoryContext) -> None:
        self.trans = trans
        self.warnings: set[str] = set()

    def _check_state(self, hda: HistoryDatasetAssociation) -> Optional[HistoryDatasetAssociation]:
        # FIXME: Create "Dataset.is_finished"
        if hda.state in ("new", "running", "queued"):
            self.warnings.add(WARNING_SOME_DATASETS_NOT_READY)
            return None
        return hda


class WorkflowSummary(BaseWorkflowSummary):
    def __init__(self, trans: ProvidesHistoryContext, history: Optional[History]) -> None:
        super().__init__(trans)
        if not history:
            history = trans.history
        assert history is not None
        self.history: History = history
        self.jobs: dict[Any, list[tuple[Optional[str], HistoryItem]]] = {}
        self.job_id2representative_job: dict[int, Job] = {}  # map a non-fake job id to its representative job
        self.implicit_map_jobs: list[Job] = []
        self.collection_types: dict[int, str] = {}

        self.hda_hid_in_history: dict[int, int] = {}
        self.hdca_hid_in_history: dict[int, int] = {}

        self.__summarize()

    def hid(self, content: HistoryItem) -> int:
        if content.history_content_type == "dataset_collection":
            if content.id in self.hdca_hid_in_history:
                return self.hdca_hid_in_history[content.id]
            elif content.history == self.history:
                assert content.hid is not None, f"HDCA {content.id} in history has no hid"
                return content.hid
            else:
                log.warning("extraction issue, using hdca hid from outside current history and unmapped")
                assert content.hid is not None, f"HDCA {content.id} from external history has no hid"
                return content.hid
        else:
            if content.id in self.hda_hid_in_history:
                return self.hda_hid_in_history[content.id]
            elif content.history == self.history:
                assert content.hid is not None, f"HDA {content.id} in history has no hid"
                return content.hid
            else:
                log.warning("extraction issue, using hda hid from outside current history and unmapped")
                assert content.hid is not None, f"HDA {content.id} from external history has no hid"
                return content.hid

    def __summarize(self) -> None:
        # Make a first pass handle all singleton jobs, input dataset and dataset collections
        # just grab the implicitly mapped jobs and handle in second pass. Second pass is
        # needed because cannot allow selection of individual datasets from an implicit
        # mapping during extraction - you get the collection or nothing.
        for content in self.history.visible_contents:
            self.__summarize_content(content)

    def __summarize_content(self, content: HistoryItem) -> None:
        # Update internal state for history content (either an HDA or
        # an HDCA).
        if content.history_content_type == "dataset_collection":
            self.__summarize_dataset_collection(cast(HistoryDatasetCollectionAssociation, content))
        else:
            self.__summarize_dataset(cast(HistoryDatasetAssociation, content))

    def __summarize_dataset_collection(self, dataset_collection: HistoryDatasetCollectionAssociation) -> None:
        hid_in_history = dataset_collection.hid
        assert hid_in_history is not None, f"HDCA {dataset_collection.id} has no hid"
        dataset_collection = _original_hdca(dataset_collection)
        self.hdca_hid_in_history[dataset_collection.id] = hid_in_history

        hid = dataset_collection.hid
        assert hid is not None, f"Original HDCA {dataset_collection.id} has no hid"
        self.collection_types[hid] = dataset_collection.collection.collection_type
        if cja := dataset_collection.creating_job_associations:
            # Use the "first" job to represent all mapped jobs.
            representative_assoc = cja[0]
            representative_job = representative_assoc.job
            if (
                representative_job not in self.jobs
                or self.jobs[representative_job][0][1].history_content_type == "dataset"
            ):
                self.jobs[representative_job] = [(representative_assoc.name, dataset_collection)]
                if dataset_collection.implicit_output_name:
                    self.implicit_map_jobs.append(representative_job)
            else:
                self.jobs[representative_job].append((representative_assoc.name, dataset_collection))
            for cja_assoc in cja:
                cja_job = cja_assoc.job
                self.job_id2representative_job[cja_job.id] = representative_job
        # Fallback for implicit output collections lacking creating_job_associations
        # (e.g. reached via Sentry GALAXY-MAIN-121W / issue #22359). Trace via a leaf
        # HDA's creating job instead.
        elif dataset_collection.implicit_output_name:
            # TODO: Optimize db call
            element = dataset_collection.collection.first_dataset_element
            dataset_instance = element.hda if element else None
            if not dataset_instance:
                # Got no dataset instance to walk back up to creating job
                # (empty collection, or leaf element is not an HDA - e.g. LDDA).
                # TODO track this via tool request model
                self.jobs[DatasetCollectionCreationJob(dataset_collection)] = [(None, dataset_collection)]
                return
            if not self._check_state(dataset_instance):
                # Just checking the state of one instance, don't need more but
                # makes me wonder if even need this check at all?
                return

            original_hda = _original_hda(dataset_instance)
            if not original_hda.creating_job_associations:
                log.warning(
                    "An implicitly create output dataset collection doesn't have a creating_job_association, should not happen!"
                )
                self.jobs[DatasetCollectionCreationJob(dataset_collection)] = [(None, dataset_collection)]

            for assoc in original_hda.creating_job_associations:
                job = assoc.job
                if job not in self.jobs or self.jobs[job][0][1].history_content_type == "dataset":
                    self.jobs[job] = [(assoc.name, dataset_collection)]
                    self.job_id2representative_job[job.id] = job
                    self.implicit_map_jobs.append(job)
                else:
                    self.jobs[job].append((assoc.name, dataset_collection))
        else:
            self.jobs[DatasetCollectionCreationJob(dataset_collection)] = [(None, dataset_collection)]

    def __summarize_dataset(self, dataset: HistoryDatasetAssociation) -> None:
        if not self._check_state(dataset):
            return

        hid_in_history = dataset.hid
        assert hid_in_history is not None
        original_hda = _original_hda(dataset)
        self.hda_hid_in_history[original_hda.id] = hid_in_history

        if not original_hda.creating_job_associations:
            self.jobs[FakeJob(dataset)] = [(None, dataset)]

        for assoc in original_hda.creating_job_associations:
            job = assoc.job
            if job in self.jobs:
                self.jobs[job].append((assoc.name, dataset))
            else:
                self.jobs[job] = [(assoc.name, dataset)]
                self.job_id2representative_job[job.id] = job


def step_inputs(trans: ProvidesHistoryContext, job: Job) -> tuple[ToolInputs, DataInputAssociations]:
    tool = trans.app.toolbox.tool_for_job(job, user=trans.user)
    assert tool is not None, f"Tool {job.tool_id} (version {job.tool_version}) not found"
    param_values = tool.get_param_values(
        job, ignore_errors=True
    )  # If a tool was updated and e.g. had a text value changed to an integer, we don't want a traceback here
    associations = __cleanup_param_values(tool.inputs, param_values)
    tool_inputs = tool.params_to_strings(param_values, trans.app)
    return tool_inputs, associations


def _walk_data_param_tree(
    inputs: ToolInputs,
    values: ToolInputs,
    leaf_handler: Callable[[Any, Any, str], None],
) -> None:
    """Walk a tool input tree, invoking ``leaf_handler`` once per
    Data/DataCollection leaf with ``(input, value, full_key)``.

    Clears the leaf's value in place and removes the deprecated metadata
    cruft (``<key>_*`` siblings of the formal input keys) the framework
    pushes into the root values dict. The cruft cleanup is shared because
    both extraction variants need it; only the per-leaf association
    emission differs.
    """
    if "dbkey" in values:
        del values["dbkey"]
    root_values = values
    root_input_keys = inputs.keys()

    def walk(prefix: str, inputs: ToolInputs, values: ToolInputs) -> None:
        for key, input in inputs.items():
            if isinstance(input, (DataToolParameter, DataCollectionToolParameter)):
                leaf_handler(input, values[key], prefix + key)
                values[key] = None
                # FIXME: Nested data params leak deprecated metadata into the
                # root values dict; scrub anything starting with `<key>_` that
                # isn't itself a formal input.
                cruft_prefix = f"{prefix + key}_"
                for k in list(root_values.keys()):
                    if k not in root_input_keys and k.startswith(cruft_prefix):
                        del root_values[k]
            elif isinstance(input, Repeat):
                if key in values:
                    group_values = values[key]
                    for i, rep_values in enumerate(group_values):
                        rep_index = rep_values["__index__"]
                        walk(f"{prefix}{key}_{rep_index}|", input.inputs, group_values[i])
            elif isinstance(input, Conditional):
                # __job_resource is a runtime-only group; strip and stop —
                # workflow encoding shouldn't carry resource selections.
                if input.name == "__job_resource":
                    if input.name in values:
                        del values[input.name]
                    return
                if input.name in values:
                    group_values = values[input.name]
                    current_case = group_values["__current_case__"]
                    walk(f"{prefix}{key}|", input.cases[current_case].inputs, group_values)
            elif isinstance(input, Section):
                if input.name in values:
                    walk(f"{prefix}{key}|", input.inputs, values[input.name])

    walk("", inputs, values)


def __cleanup_param_values(inputs: ToolInputs, values: ToolInputs) -> DataInputAssociations:
    """HID-keyed Data-leaf scrub: emit ``(hid, key)`` associations."""
    associations: DataInputAssociations = []

    def emit(input, value, key):
        for item in listify(value):
            if isinstance(item, model.DatasetCollectionElement):
                item = item.first_dataset_instance()
            if item:  # false for a non-set optional dataset
                associations.append((item.hid, key))

    _walk_data_param_tree(inputs, values, emit)
    return associations


def extract_workflow_by_ids(
    trans: ProvidesHistoryContext,
    user: User,
    workflow_name: str,
    job_manager: JobManager,
    job_ids: Optional[list[int]] = None,
    implicit_collection_jobs_ids: Optional[list[int]] = None,
    hda_ids: Optional[list[int]] = None,
    hdca_ids: Optional[list[int]] = None,
    dataset_names: Optional[list[str]] = None,
    dataset_collection_names: Optional[list[str]] = None,
) -> StoredWorkflow:
    """ID-based variant of :func:`extract_workflow`."""
    steps = extract_steps_by_ids(
        trans,
        job_manager=job_manager,
        job_ids=job_ids,
        implicit_collection_jobs_ids=implicit_collection_jobs_ids,
        hda_ids=hda_ids,
        hdca_ids=hdca_ids,
        dataset_names=dataset_names,
        dataset_collection_names=dataset_collection_names,
    )
    return _finalize_workflow(trans, user, workflow_name, steps)


IdKey = tuple[Literal["dataset", "collection"], int]
IdAssociations = list[tuple[IdKey, str]]


def extract_steps_by_ids(
    trans: ProvidesHistoryContext,
    job_manager: Optional[JobManager] = None,
    job_ids: Optional[list[int]] = None,
    implicit_collection_jobs_ids: Optional[list[int]] = None,
    hda_ids: Optional[list[int]] = None,
    hdca_ids: Optional[list[int]] = None,
    dataset_names: Optional[list[str]] = None,
    dataset_collection_names: Optional[list[str]] = None,
) -> list[WorkflowStep]:
    """ID-based variant of :func:`extract_steps`.

    Inputs are decoded DB ids; each is fetched and access-checked against the
    current user via the appropriate manager. Connections are keyed by
    ``(content_type, db_id)`` of the resolved *original* HDA/HDCA so that
    copied datasets and cross-history items map deterministically.

    Mapped (map-over) steps are passed as ``implicit_collection_jobs_ids``;
    each ICJ becomes a single workflow step whose inputs are wired to the
    pre-map input HDCA(s) via ``ImplicitlyCreatedDatasetCollectionInput``.

    ``job_manager`` may be omitted only when ``job_ids`` is empty (kept
    Optional for unit-test ergonomics).
    """
    job_ids = list(job_ids or [])
    implicit_collection_jobs_ids = list(implicit_collection_jobs_ids or [])
    hda_ids = list(hda_ids or [])
    hdca_ids = list(hdca_ids or [])

    user = getattr(trans, "user", None)
    sa_session = trans.sa_session
    hda_manager = trans.app.hda_manager
    dataset_collection_manager = trans.app.dataset_collection_manager

    steps: list[WorkflowStep] = []
    step_labels: set[str] = set()
    id_to_output_pair: dict[IdKey, tuple[WorkflowStep, str]] = {}

    for i, hda_id in enumerate(hda_ids):
        hda = hda_manager.get_accessible(hda_id, user)
        step = model.WorkflowStep()
        step.type = "data_input"
        name = dataset_names[i] if dataset_names else "Input Dataset"
        if name not in step_labels:
            step.label = name
            step_labels.add(name)
        step.tool_inputs = dict(name=name)
        steps.append(step)
        original = _original_hda(hda)
        id_to_output_pair[("dataset", original.id)] = (step, "output")

    for i, hdca_id in enumerate(hdca_ids):
        hdca = dataset_collection_manager.get_dataset_collection_instance(trans, "history", hdca_id)
        step = model.WorkflowStep()
        step.type = "data_collection_input"
        name = dataset_collection_names[i] if dataset_collection_names else "Input Dataset Collection"
        if name not in step_labels:
            step.label = name
            step_labels.add(name)
        step.tool_inputs = dict(name=name, collection_type=hdca.collection.collection_type)
        steps.append(step)
        original_hdca = _original_hdca(hdca)
        id_to_output_pair[("collection", original_hdca.id)] = (step, "output")

    # Build the list of work items: each tuple is (representative_job,
    # output_hdcas). For plain jobs output_hdcas is empty; for ICJs it
    # contains the ICJ's output HDCAs (used both for access checks and to
    # drive input/output wiring without inferring map/over from job state).
    # Service-layer validator ensures no job in job_ids has an ICJ
    # association, so this branch handles only true plain jobs.
    work_items: list[tuple[Job, list[HistoryDatasetCollectionAssociation]]] = []

    for job_id in job_ids:
        assert job_manager is not None, "job_manager required when job_ids supplied"
        job = job_manager.get_accessible_job(trans, job_id)
        work_items.append((job, []))

    # FIXME: representative-job param read is the only remaining HID-style
    # inference here. Swap step_inputs_by_id for a Job.tool_state /
    # ToolRequest.request_state reader once that exists; see
    # docs/research/Problem - YAML Tool Post-Hoc State Divergence.md.
    for icj_id in implicit_collection_jobs_ids:
        # Service-layer validator already checked existence, populated_state,
        # output-HDCA presence, and per-HDCA accessibility.
        icj = sa_session.get(ImplicitCollectionJobs, icj_id)
        assert icj is not None, f"ImplicitCollectionJobs {icj_id} not found"
        work_items.append((icj.representative_job, icj.output_dataset_collection_instances))

    # Job.id is monotonically assigned at submission, so sorting by it
    # produces dependency order: a downstream job always has a larger id
    # than the jobs whose outputs it consumes.
    work_items.sort(key=lambda item: item[0].id)

    for job, output_hdcas in work_items:
        tool_inputs, associations = step_inputs_by_id(trans, job)
        step = model.WorkflowStep()
        step.type = "tool"
        step.tool_id = job.tool_id
        step.tool_version = job.tool_version
        step.tool_inputs = tool_inputs

        mapped_inputs: dict[str, HistoryDatasetCollectionAssociation] = {}
        if output_hdcas:
            for icol in output_hdcas[0].implicit_input_collections:
                if icol.name and icol.input_dataset_collection is not None:
                    mapped_inputs[icol.name] = _original_hdca(icol.input_dataset_collection)

        for key, input_name in associations:
            if input_name in mapped_inputs:
                key = ("collection", mapped_inputs[input_name].id)
            if key in id_to_output_pair:
                _connect(step, input_name, id_to_output_pair[key])
        steps.append(step)

        if output_hdcas:
            seen_names: dict[str, HistoryDatasetCollectionAssociation] = {}
            for output_hdca in output_hdcas:
                output_name = output_hdca.implicit_output_name
                if output_name and output_name not in seen_names:
                    seen_names[output_name] = output_hdca
            for output_name, output_hdca in seen_names.items():
                original_output = _original_hdca(output_hdca)
                id_to_output_pair[("collection", original_output.id)] = (step, output_name)
        else:
            for hda_assoc in job.output_datasets:
                hda_assoc_name = hda_assoc.name
                if _skip_output_assoc_name(hda_assoc_name):
                    continue
                original_hda = _original_hda(hda_assoc.dataset)
                id_to_output_pair[("dataset", original_hda.id)] = (step, hda_assoc_name)
            for hdca_assoc in job.output_dataset_collection_instances:
                original_hdca = _original_hdca(hdca_assoc.dataset_collection_instance)
                id_to_output_pair[("collection", original_hdca.id)] = (step, hdca_assoc.name)

    return steps


def step_inputs_by_id(trans: ProvidesHistoryContext, job: Job) -> tuple[ToolInputs, IdAssociations]:
    """ID-based variant of :func:`step_inputs`.

    Returns associations keyed by ``(content_type, db_id)`` tuples (against
    the *original* HDA/HDCA after walking ``copied_from_*``). Collection
    and DCE inputs come from ``Job.input_dataset_collections`` /
    ``Job.input_dataset_collection_elements`` directly rather than from the
    param-value walk, which avoids the HID path's flattening of HDCAs to
    leaf HDAs and prevents duplicate emission for DCE-as-data-param.
    """
    tool = trans.app.toolbox.get_tool(job.tool_id, tool_version=job.tool_version)
    assert tool is not None, f"Tool {job.tool_id} (version {job.tool_version}) not found"
    param_values = tool.get_param_values(job, ignore_errors=True)
    associations: IdAssociations = __cleanup_param_values_by_id(tool.inputs, param_values)
    for assoc in job.input_dataset_collections:
        original_hdca = _original_hdca(assoc.dataset_collection)
        associations.append((("collection", original_hdca.id), assoc.name))
    for elem_assoc in job.input_dataset_collection_elements:
        dce = elem_assoc.dataset_collection_element
        leaf = dce.hda or dce.first_dataset_instance()
        if not isinstance(leaf, HistoryDatasetAssociation):
            continue
        original_hda = _original_hda(leaf)
        associations.append((("dataset", original_hda.id), elem_assoc.name))
    tool_inputs = tool.params_to_strings(param_values, trans.app)
    return tool_inputs, associations


def _original_hda(hda: HistoryDatasetAssociation) -> HistoryDatasetAssociation:
    while hda.copied_from_history_dataset_association:
        hda = hda.copied_from_history_dataset_association
    return hda


def _original_hdca(hdca: HistoryDatasetCollectionAssociation) -> HistoryDatasetCollectionAssociation:
    while hdca.copied_from_history_dataset_collection_association:
        hdca = hdca.copied_from_history_dataset_collection_association
    return hdca


def __cleanup_param_values_by_id(inputs: ToolInputs, values: ToolInputs) -> IdAssociations:
    """ID-keyed Data-leaf scrub.

    HDA leaves emit ``("dataset", _original_hda(hda).id)``. DCE values and
    ``DataCollectionToolParameter`` leaves are scrubbed but emit nothing —
    collection / DCE inputs are appended in :func:`step_inputs_by_id` from
    typed DB rows so HDCAs aren't lost to ``first_dataset_instance()``
    flattening and DCEs aren't double-emitted alongside their typed
    ``input_dataset_collection_elements`` row.
    """
    associations: IdAssociations = []

    def emit(input, value, key):
        if isinstance(input, DataCollectionToolParameter):
            return
        for item in listify(value):
            if isinstance(item, model.DatasetCollectionElement):
                # Covered by job.input_dataset_collection_elements; skip to
                # avoid duplicate connections.
                continue
            if isinstance(item, HistoryDatasetAssociation):
                original = _original_hda(item)
                associations.append((("dataset", original.id), key))

    _walk_data_param_tree(inputs, values, emit)
    return associations


__all__ = (
    "summarize",
    "extract_workflow",
    "extract_workflow_by_ids",
    "extract_steps_by_ids",
)
