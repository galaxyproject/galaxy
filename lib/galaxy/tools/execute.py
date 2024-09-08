"""
Once state information has been calculated, handle actually executing tools
from various states, tracking results, and building implicit dataset
collections from matched collections.
"""

import collections
import logging
import typing
from abc import abstractmethod
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

from boltons.iterutils import remap
from packaging.version import Version

from galaxy import model
from galaxy.exceptions import ToolInputsNotOKException
from galaxy.model import ToolRequest
from galaxy.model.base import transaction
from galaxy.model.dataset_collections.matching import MatchingCollections
from galaxy.model.dataset_collections.structure import (
    get_structure,
    tool_output_to_structure,
)
from galaxy.tool_util.parameters.state import (
    JobInternalToolState,
    RequestInternalDereferencedToolState,
)
from galaxy.tool_util.parser import ToolOutputCollectionPart
from galaxy.tools.execution_helpers import (
    filter_output,
    on_text_for_names,
    ToolExecutionCache,
)
from galaxy.tools.parameters.workflow_utils import is_runtime_value
from ._types import (
    ToolRequestT,
    ToolStateJobInstancePopulatedT,
)

if typing.TYPE_CHECKING:
    from galaxy.tools import Tool

log = logging.getLogger(__name__)

SINGLE_EXECUTION_SUCCESS_MESSAGE = "Tool ${tool_id} created job ${job_id}"
BATCH_EXECUTION_MESSAGE = "Created ${job_count} job(s) for tool ${tool_id} request"


CompletedJobsT = Dict[int, Optional[model.Job]]
JobCallbackT = Callable
WorkflowResourceParametersT = Dict[str, Any]
DatasetCollectionElementsSliceT = Dict[str, model.DatasetCollectionElement]
DEFAULT_USE_CACHED_JOB = False
DEFAULT_PREFERRED_OBJECT_STORE_ID: Optional[str] = None
DEFAULT_RERUN_REMAP_JOB_ID: Optional[int] = None
DEFAULT_JOB_CALLBACK: Optional[JobCallbackT] = None
DEFAULT_DATASET_COLLECTION_ELEMENTS: Optional[DatasetCollectionElementsSliceT] = None
DEFAULT_SET_OUTPUT_HID: bool = True


class PartialJobExecution(Exception):
    def __init__(self, execution_tracker: "ExecutionTracker"):
        self.execution_tracker = execution_tracker


class MappingParameters(NamedTuple):
    # the raw request - might correspond to multiple jobs
    param_template: ToolRequestT
    # parameters corresponding to individual job
    param_combinations: List[ToolStateJobInstancePopulatedT]
    # schema driven parameters
    # model validated tool request - might correspond to multiple jobs
    validated_param_template: Optional[RequestInternalDereferencedToolState] = None
    # validated job parameters for individual jobs
    validated_param_combinations: Optional[List[JobInternalToolState]] = None

    def ensure_validated(self):
        assert self.validated_param_template is not None
        assert self.validated_param_combinations is not None


def execute_async(
    trans,
    tool: "Tool",
    mapping_params: MappingParameters,
    history: model.History,
    tool_request: ToolRequest,
    completed_jobs: Optional[CompletedJobsT] = None,
    rerun_remap_job_id: Optional[int] = None,
    preferred_object_store_id: Optional[str] = None,
    collection_info: Optional[MatchingCollections] = None,
    workflow_invocation_uuid: Optional[str] = None,
    invocation_step: Optional[model.WorkflowInvocationStep] = None,
    max_num_jobs: Optional[int] = None,
    job_callback: Optional[Callable] = None,
    workflow_resource_parameters: Optional[Dict[str, Any]] = None,
    validate_outputs: bool = False,
) -> "ExecutionTracker":
    """The tool request/async version of execute."""
    completed_jobs = completed_jobs or {}
    mapping_params.ensure_validated()
    return _execute(
        trans,
        tool,
        mapping_params,
        history,
        tool_request,
        rerun_remap_job_id,
        preferred_object_store_id,
        collection_info,
        workflow_invocation_uuid,
        invocation_step,
        max_num_jobs,
        job_callback,
        completed_jobs,
        workflow_resource_parameters,
        validate_outputs,
    )


def execute(
    trans,
    tool: "Tool",
    mapping_params: MappingParameters,
    history: model.History,
    rerun_remap_job_id: Optional[int] = DEFAULT_RERUN_REMAP_JOB_ID,
    preferred_object_store_id: Optional[str] = DEFAULT_PREFERRED_OBJECT_STORE_ID,
    collection_info: Optional[MatchingCollections] = None,
    workflow_invocation_uuid: Optional[str] = None,
    invocation_step: Optional[model.WorkflowInvocationStep] = None,
    max_num_jobs: Optional[int] = None,
    job_callback: Optional[JobCallbackT] = DEFAULT_JOB_CALLBACK,
    completed_jobs: Optional[CompletedJobsT] = None,
    workflow_resource_parameters: Optional[WorkflowResourceParametersT] = None,
    validate_outputs: bool = False,
) -> "ExecutionTracker":
    """
    Execute a tool and return object containing summary (output data, number of
    failures, etc...).
    """
    completed_jobs = completed_jobs or {}
    return _execute(
        trans,
        tool,
        mapping_params,
        history,
        None,
        rerun_remap_job_id,
        preferred_object_store_id,
        collection_info,
        workflow_invocation_uuid,
        invocation_step,
        max_num_jobs,
        job_callback,
        completed_jobs,
        workflow_resource_parameters,
        validate_outputs,
    )


def _execute(
    trans,
    tool: "Tool",
    mapping_params: MappingParameters,
    history: model.History,
    tool_request: Optional[model.ToolRequest],
    rerun_remap_job_id: Optional[int],
    preferred_object_store_id: Optional[str],
    collection_info: Optional[MatchingCollections],
    workflow_invocation_uuid: Optional[str],
    invocation_step: Optional[model.WorkflowInvocationStep],
    max_num_jobs: Optional[int],
    job_callback: Optional[Callable],
    completed_jobs: Dict[int, Optional[model.Job]],
    workflow_resource_parameters: Optional[Dict[str, Any]],
    validate_outputs: bool,
) -> "ExecutionTracker":
    if max_num_jobs is not None:
        assert invocation_step is not None
    if rerun_remap_job_id:
        assert invocation_step is None

    all_jobs_timer = tool.app.execution_timer_factory.get_timer(
        "internals.galaxy.tools.execute.job_batch", BATCH_EXECUTION_MESSAGE
    )

    if invocation_step is None:
        execution_tracker: ExecutionTracker = ToolExecutionTracker(
            trans, tool, mapping_params, collection_info, completed_jobs=completed_jobs
        )
    else:
        execution_tracker = WorkflowStepExecutionTracker(
            trans, tool, mapping_params, collection_info, invocation_step, completed_jobs=completed_jobs
        )
    execution_cache = ToolExecutionCache(trans)

    def execute_single_job(execution_slice: "ExecutionSlice", completed_job: Optional[model.Job], skip: bool = False):
        job_timer = tool.app.execution_timer_factory.get_timer(
            "internals.galaxy.tools.execute.job_single", SINGLE_EXECUTION_SUCCESS_MESSAGE
        )
        params = execution_slice.param_combination
        request_state = mapping_params.param_template
        if "__data_manager_mode" in request_state:
            params["__data_manager_mode"] = request_state["__data_manager_mode"]
        if workflow_invocation_uuid:
            params["__workflow_invocation_uuid__"] = workflow_invocation_uuid
        elif "__workflow_invocation_uuid__" in params:
            # Only workflow invocation code gets to set this, ignore user supplied
            # values or rerun parameters.
            del params["__workflow_invocation_uuid__"]
        if workflow_resource_parameters:
            params["__workflow_resource_params__"] = workflow_resource_parameters
        elif "__workflow_resource_params__" in params:
            # Only workflow invocation code gets to set this, ignore user supplied
            # values or rerun parameters.
            del params["__workflow_resource_params__"]
        if validate_outputs:
            params["__validate_outputs__"] = True
        job, result = tool.handle_single_execution(
            trans,
            rerun_remap_job_id,
            execution_slice,
            history,
            execution_cache,
            completed_job,
            collection_info,
            job_callback,
            preferred_object_store_id,
            flush_job=False,
            skip=skip,
        )
        if job:
            if tool_request:
                job.tool_request = tool_request
            log.debug(job_timer.to_str(tool_id=tool.id, job_id=job.id))
            execution_tracker.record_success(execution_slice, job, result)
            # associate dataset instances with the job that creates them
            if result:
                instance_types = (model.HistoryDatasetAssociation, model.LibraryDatasetDatasetAssociation)
                datasets = [pair[1] for pair in result if type(pair[1]) in instance_types]
                if datasets:
                    job_datasets[job] = datasets
        else:
            execution_tracker.record_error(result)

    tool_action = tool.tool_action
    if check_inputs_ready := getattr(tool_action, "check_inputs_ready", None):
        for params in execution_tracker.param_combinations:
            # This will throw an exception if the tool is not ready.
            try:
                check_inputs_ready(
                    tool,
                    trans,
                    params,
                    history,
                    execution_cache=execution_cache,
                    collection_info=collection_info,
                )
            except ToolInputsNotOKException as e:
                execution_tracker.record_error(e)

    execution_tracker.ensure_implicit_collections_populated(history, mapping_params.param_template)
    job_count = len(execution_tracker.param_combinations)

    jobs_executed = 0
    has_remaining_jobs = False
    execution_slice = None
    job_datasets: Dict[str, List[model.DatasetInstance]] = {}  # job: list of dataset instances created by job

    for i, execution_slice in enumerate(execution_tracker.new_execution_slices()):
        if max_num_jobs is not None and jobs_executed >= max_num_jobs:
            has_remaining_jobs = True
            break
        else:
            slice_params = execution_slice.param_combination
            if isinstance(slice_params, JobInternalToolState):
                slice_params = slice_params.input_state

            skip = slice_params.pop("__when_value__", None) is False
            execute_single_job(execution_slice, completed_jobs[i], skip=skip)
            history = execution_slice.history or history
            jobs_executed += 1

    if execution_slice:
        history.add_pending_items()
    # Make sure collections, implicit jobs etc are flushed even if there are no precreated output datasets
    with transaction(trans.sa_session):
        trans.sa_session.commit()

    tool_id = tool.id
    for job2 in execution_tracker.successful_jobs:
        # Put the job in the queue if tracking in memory
        if tool_id == "__DATA_FETCH__" and tool.app.config.is_fetch_with_celery_enabled():
            job_id = job2.id
            from galaxy.celery.tasks import (
                fetch_data,
                finish_job,
                set_job_metadata,
                setup_fetch_data,
            )

            raw_tool_source = tool.tool_source.to_string()
            #  task_user_id parameter is used to do task user rate limiting. It is only passed
            #  to first task in chain because it is only necessary to rate limit the first
            #  task in a chain.
            async_result = (
                setup_fetch_data.s(
                    job_id, raw_tool_source=raw_tool_source, task_user_id=getattr(trans.user, "id", None)
                )
                | fetch_data.s(job_id=job_id)
                | set_job_metadata.s(
                    extended_metadata_collection="extended" in tool.app.config.metadata_strategy,
                    job_id=job_id,
                ).set(link_error=finish_job.si(job_id=job_id, raw_tool_source=raw_tool_source))
                | finish_job.si(job_id=job_id, raw_tool_source=raw_tool_source)
            )()
            job2.set_runner_external_id(async_result.task_id)
            continue
        tool.app.job_manager.enqueue(job2, tool=tool, flush=False)
        trans.log_event(f"Added job to the job queue, id: {str(job2.id)}", tool_id=tool_id)
    with transaction(trans.sa_session):
        trans.sa_session.commit()

    if has_remaining_jobs:
        raise PartialJobExecution(execution_tracker)
    else:
        execution_tracker.finalize_dataset_collections(trans)

    log.debug(all_jobs_timer.to_str(job_count=job_count, tool_id=tool.id))
    return execution_tracker


class ExecutionSlice:
    job_index: int
    param_combination: ToolStateJobInstancePopulatedT
    dataset_collection_elements: Optional[DatasetCollectionElementsSliceT]
    history: Optional[model.History]

    def __init__(
        self,
        job_index: int,
        param_combination: ToolStateJobInstancePopulatedT,
        dataset_collection_elements: Optional[DatasetCollectionElementsSliceT] = DEFAULT_DATASET_COLLECTION_ELEMENTS,
    ):
        self.job_index = job_index
        self.param_combination = param_combination
        self.dataset_collection_elements = dataset_collection_elements
        self.history = None


ExecutionErrorsT = Union[str, Exception]


class ExecutionTracker:
    execution_errors: List[ExecutionErrorsT]
    successful_jobs: List[model.Job]
    output_datasets: List[Tuple[str, model.HistoryDatasetAssociation]]
    output_collections: List[Tuple[str, model.HistoryDatasetCollectionAssociation]]
    implicit_collections: Dict[str, model.HistoryDatasetCollectionAssociation]

    def __init__(
        self,
        trans,
        tool: "Tool",
        mapping_params: MappingParameters,
        collection_info: Optional[MatchingCollections],
        completed_jobs: Optional[CompletedJobsT] = None,
    ):
        # Known ahead of time...
        self.trans = trans
        self.tool = tool
        self.mapping_params = mapping_params
        self.collection_info = collection_info
        self.completed_jobs = completed_jobs

        self._on_text = None

        # Populated as we go...
        self.failed_jobs = 0
        self.execution_errors = []

        self.successful_jobs = []
        self.output_datasets = []
        self.output_collections = []

        self.implicit_collections = {}

    @property
    def param_combinations(self):
        return self.mapping_params.param_combinations

    @property
    def example_params(self):
        if self.mapping_params.param_combinations:
            return self.mapping_params.param_combinations[0]
        else:
            # TODO: This isn't quite right - what we want is something like param_template wrapped,
            # need a test case with an output filter applied to an empty list, still this is
            # an improvement over not allowing mapping of empty lists.
            return self.mapping_params.param_template

    @property
    def job_count(self):
        return len(self.param_combinations)

    def record_error(self, error):
        self.failed_jobs += 1
        message = "There was a failure executing a job for tool [%s] - %s"
        log.warning(message, self.tool.id, error)
        self.execution_errors.append(error)

    @property
    def on_text(self):
        collection_info = self.collection_info
        if self._on_text is None and collection_info is not None:
            collection_names = ["collection %d" % c.hid for c in collection_info.collections.values()]
            self._on_text = on_text_for_names(collection_names)

        return self._on_text

    def output_name(self, trans, history, params, output):
        on_text = self.on_text

        try:
            output_collection_name = self.tool.tool_action.get_output_name(
                output,
                dataset=None,
                tool=self.tool,
                on_text=on_text,
                trans=trans,
                history=history,
                params=params,
                incoming=None,
                job_params=None,
            )
        except Exception:
            output_collection_name = f"{self.tool.name} across {on_text}"

        return output_collection_name

    def sliced_input_collection_structure(self, input_name):
        unqualified_recurse = Version(str(self.tool.profile)) < Version("18.09") and "|" not in input_name

        def find_collection(input_dict, input_name):
            for key, value in input_dict.items():
                if key == input_name:
                    return value
                if isinstance(value, dict):
                    if "|" in input_name:
                        prefix, rest_input_name = input_name.split("|", 1)
                        if key == prefix:
                            return find_collection(value, rest_input_name)
                    elif unqualified_recurse:
                        # Looking for "input1" instead of "cond|input1" for instance.
                        # See discussion on https://github.com/galaxyproject/galaxy/issues/6157.
                        unqualified_match = find_collection(value, input_name)
                        if unqualified_match:
                            return unqualified_match

        input_collection = find_collection(self.example_params, input_name)
        if input_collection is None:
            raise Exception("Failed to find referenced collection in inputs.")

        if not hasattr(input_collection, "collection"):
            raise Exception("Referenced input parameter is not a collection.")

        collection_type_description = (
            self.trans.app.dataset_collection_manager.collection_type_descriptions.for_collection_type(
                input_collection.collection.collection_type
            )
        )
        subcollection_mapping_type = None
        if self.is_implicit_input(input_name):
            collection_info = self.collection_info
            assert collection_info
            subcollection_mapping_type = collection_info.subcollection_mapping_type(input_name)

        return get_structure(
            input_collection, collection_type_description, leaf_subcollection_type=subcollection_mapping_type
        )

    def _structure_for_output(self, trans, tool_output):
        collection_info = self.collection_info
        assert collection_info
        structure = collection_info.structure
        if hasattr(tool_output, "default_identifier_source"):
            # Switch the structure for outputs if the output specified a default_identifier_source
            collection_type_descriptions = trans.app.dataset_collection_manager.collection_type_descriptions

            source_collection = collection_info.collections.get(tool_output.default_identifier_source)
            if source_collection:
                collection_type_description = collection_type_descriptions.for_collection_type(
                    source_collection.collection.collection_type
                )
                _structure = structure.for_dataset_collection(
                    source_collection.collection, collection_type_description=collection_type_description
                )
                if structure.can_match(_structure):
                    structure = _structure

        return structure

    def _mapped_output_structure(self, trans, tool_output):
        collections_manager = trans.app.dataset_collection_manager
        output_structure = tool_output_to_structure(
            self.sliced_input_collection_structure, tool_output, collections_manager
        )
        # self.collection_info.structure - the mapping structure with default_identifier_source
        # used to determine the identifiers to use.
        mapping_structure = self._structure_for_output(trans, tool_output)
        # Output structure may not be known, but input structure must be,
        # otherwise this step of the workflow shouldn't have been scheduled
        # or the tool should not have been executable on this input.
        mapped_output_structure = mapping_structure.multiply(output_structure)
        return mapped_output_structure

    def ensure_implicit_collections_populated(self, history, params):
        if not self.collection_info:
            return

        history = history or self.tool.get_default_history_by_trans(self.trans)
        # params = param_combinations[0] if param_combinations else mapping_params.param_template
        self.precreate_output_collections(history, params)

    def precreate_output_collections(self, history, params):
        # params is just one sample tool param execution with parallelized
        # collection replaced with a specific dataset. Need to replace this
        # with the collection and wrap everything up so can evaluate output
        # label.
        collection_info = self.collection_info
        assert collection_info
        trans = self.trans
        params.update(collection_info.collections)  # Replace datasets with source collections for labelling outputs.

        collection_instances = {}
        implicit_inputs = self.implicit_inputs

        implicit_collection_jobs = model.ImplicitCollectionJobs()

        # trying to guess these filters at the collection levell is tricky because
        # the filter condition could vary from element to element. Just do best we
        # we can for now.
        example_params = self.example_params.copy()

        # walk through and optional replace runtime values with None, assume they
        # would have been replaced by now if they were going to be set.
        def replace_optional_runtime_values(path, key, value):
            if is_runtime_value(value):
                return key, None
            return key, value

        example_params = remap(example_params, visit=replace_optional_runtime_values)

        for output_name, output in self.tool.outputs.items():
            if filter_output(self.tool, output, example_params):
                continue
            output_collection_name = self.output_name(trans, history, params, output)
            effective_structure = self._mapped_output_structure(trans, output)
            collection_instance = trans.app.dataset_collection_manager.precreate_dataset_collection_instance(
                trans=trans,
                parent=history,
                name=output_collection_name,
                structure=effective_structure,
                implicit_inputs=implicit_inputs,
                implicit_output_name=output_name,
                completed_collection=self.completed_jobs,
            )
            collection_instance.implicit_collection_jobs = implicit_collection_jobs
            collection_instances[output_name] = collection_instance
            trans.sa_session.add(collection_instance)
        # Needed to flush the association created just above with
        # job.add_output_dataset_collection.
        with transaction(trans.sa_session):
            trans.sa_session.commit()
        self.implicit_collections = collection_instances

    @property
    def implicit_collection_jobs(self):
        # TODO: refactor to track this properly maybe?
        if self.implicit_collections:
            return next(iter(self.implicit_collections.values())).implicit_collection_jobs
        else:
            return None

    def finalize_dataset_collections(self, trans):
        # TODO: this probably needs to be reworked some, we should have the collection methods
        # return a list of changed objects to add to the session and flush and we should only
        # be finalizing collections to a depth of self.collection_info.structure. So for instance
        # if you are mapping a list over a tool that dynamically generates lists - we won't actually
        # know the structure of the inner list until after its job is complete.
        if self.failed_jobs > 0:
            for i, implicit_collection in enumerate(self.implicit_collections.values()):
                if i == 0:
                    implicit_collection_jobs = implicit_collection.implicit_collection_jobs
                    implicit_collection_jobs.populated_state = "failed"
                    trans.sa_session.add(implicit_collection_jobs)
                implicit_collection.collection.handle_population_failed(
                    "One or more jobs failed during dataset initialization."
                )
                trans.sa_session.add(implicit_collection.collection)
        else:
            completed_collections = {}
            if (
                self.completed_jobs
                and self.completed_jobs[0]
                and self.implicit_collection_jobs
                and len(self.completed_jobs) == len(self.successful_jobs)
            ):
                # If the same number of implicit collection jobs went into
                # creating the collection and those jobs are all cached
                # the HDCA has effectively been copied.
                # We mark this here so that the job cache query in subsequent
                # jobs considers this to be a valid cached input.
                completed_job_ids = {job.id for job in self.completed_jobs.values() if job}
                if all(job.copied_from_job_id in completed_job_ids for job in self.implicit_collection_jobs.job_list):
                    completed_collections = {
                        jtodca.name: jtodca.dataset_collection_instance
                        for jtodca in self.completed_jobs[0].output_dataset_collection_instances
                    }
            implicit_collection = None
            for i, implicit_collection in enumerate(self.implicit_collections.values()):
                if i == 0:
                    implicit_collection_jobs = implicit_collection.implicit_collection_jobs
                    implicit_collection_jobs.populated_state = "ok"
                    trans.sa_session.add(implicit_collection_jobs)
                collection_info = self.collection_info
                assert collection_info
                implicit_collection.collection.finalize(
                    collection_type_description=collection_info.structure.collection_type_description
                )

                # Mark implicit HDCA as copied
                implicit_output_name = implicit_collection.implicit_output_name
                completed_implicit_collection = (
                    implicit_collection and implicit_output_name and completed_collections.get(implicit_output_name)
                )
                if completed_implicit_collection:
                    implicit_collection.copied_from_history_dataset_collection_association_id = (
                        completed_implicit_collection.id
                    )

                trans.sa_session.add(implicit_collection.collection)

        with transaction(trans.sa_session):
            trans.sa_session.commit()

    @property
    def implicit_inputs(self):
        collection_info = self.collection_info
        assert collection_info
        implicit_inputs = list(collection_info.collections.items())
        return implicit_inputs

    def is_implicit_input(self, input_name):
        collection_info = self.collection_info
        assert collection_info
        return input_name in collection_info.collections

    def walk_implicit_collections(self):
        collection_info = self.collection_info
        assert collection_info
        return collection_info.structure.walk_collections(self.implicit_collections)

    def new_execution_slices(self):
        if self.collection_info is None:
            for job_index, param_combination in enumerate(self.param_combinations):
                yield ExecutionSlice(job_index, param_combination)
        else:
            yield from self.new_collection_execution_slices()

    def record_success(self, execution_slice, job, outputs):
        # TODO: successful_jobs need to be inserted in the correct place...
        self.successful_jobs.append(job)
        self.output_datasets.extend(outputs)
        for job_output in job.output_dataset_collection_instances:
            self.output_collections.append((job_output.name, job_output.dataset_collection_instance))
        if self.implicit_collections:
            implicit_collection_jobs = None
            for output_name, collection_instance in self.implicit_collections.items():
                job.add_output_dataset_collection(output_name, collection_instance)
                if implicit_collection_jobs is None:
                    implicit_collection_jobs = collection_instance.implicit_collection_jobs

            job_assoc = model.ImplicitCollectionJobsJobAssociation()
            job_assoc.order_index = execution_slice.job_index
            job_assoc.implicit_collection_jobs = implicit_collection_jobs
            job_assoc.job = job
            self.trans.sa_session.add(job_assoc)

    @abstractmethod
    def new_collection_execution_slices(self):
        pass


# Seperate these because workflows need to track their jobs belong to the invocation
# in the database immediately and they can be recovered.
class ToolExecutionTracker(ExecutionTracker):
    def __init__(
        self,
        trans,
        tool: "Tool",
        mapping_params: MappingParameters,
        collection_info: Optional[MatchingCollections],
        completed_jobs: Optional[CompletedJobsT] = None,
    ):
        super().__init__(trans, tool, mapping_params, collection_info, completed_jobs=completed_jobs)

        # New to track these things for tool output API response in the tool case,
        # in the workflow case we just write stuff to the database and forget about
        # it.
        self.outputs_by_output_name: Dict[str, List[Union[model.DatasetInstance, model.DatasetCollection]]] = (
            collections.defaultdict(list)
        )

    def record_success(self, execution_slice, job, outputs):
        super().record_success(execution_slice, job, outputs)
        for output_name, output_dataset in outputs:
            if ToolOutputCollectionPart.is_named_collection_part_name(output_name):
                # Skip known collection outputs, these will be covered by
                # output collections.
                continue
            self.outputs_by_output_name[output_name].append(output_dataset)
        for job_output in job.output_dataset_collections:
            self.outputs_by_output_name[job_output.name].append(job_output.dataset_collection)

    def new_collection_execution_slices(self):
        for job_index, (param_combination, (dataset_collection_elements, _when_value)) in enumerate(
            zip(self.param_combinations, self.walk_implicit_collections())
        ):
            completed_job = self.completed_jobs and self.completed_jobs[job_index]
            if not completed_job:
                for dataset_collection_element in dataset_collection_elements.values():
                    assert dataset_collection_element.element_object is None

            yield ExecutionSlice(job_index, param_combination, dataset_collection_elements)


class WorkflowStepExecutionTracker(ExecutionTracker):
    def __init__(
        self,
        trans,
        tool: "Tool",
        mapping_params: MappingParameters,
        collection_info: Optional[MatchingCollections],
        invocation_step: model.WorkflowInvocationStep,
        completed_jobs: Optional[CompletedJobsT] = None,
    ):
        super().__init__(trans, tool, mapping_params, collection_info, completed_jobs=completed_jobs)
        self.invocation_step = invocation_step

    def record_success(self, execution_slice, job, outputs):
        super().record_success(execution_slice, job, outputs)
        if not self.collection_info:
            for output_name, output in outputs:
                self.invocation_step.add_output(output_name, output)
            self.invocation_step.job = job

    def new_collection_execution_slices(self):
        for job_index, (param_combination, (dataset_collection_elements, _when_value)) in enumerate(
            zip(self.param_combinations, self.walk_implicit_collections())
        ):
            completed_job = self.completed_jobs and self.completed_jobs[job_index]
            if not completed_job:
                found_result = False
                for dataset_collection_element in dataset_collection_elements.values():
                    if dataset_collection_element.element_object is not None:
                        found_result = True
                        break
                if found_result:
                    continue

            yield ExecutionSlice(job_index, param_combination, dataset_collection_elements)

    def ensure_implicit_collections_populated(self, history, params):
        if not self.collection_info:
            return

        history = history or self.tool.get_default_history_by_trans(self.trans)
        if self.invocation_step.is_new:
            self.precreate_output_collections(history, params)
            for output_name, implicit_collection in self.implicit_collections.items():
                self.invocation_step.add_output(output_name, implicit_collection)
        else:
            collections = {}
            for output_assoc in self.invocation_step.output_dataset_collections:
                implicit_collection = output_assoc.dataset_collection
                assert hasattr(implicit_collection, "history_content_type")  # make sure it is an HDCA and not a DC
                collections[output_assoc.output_name] = output_assoc.dataset_collection
            self.implicit_collections = collections
        self.invocation_step.implicit_collection_jobs = self.implicit_collection_jobs


__all__ = ("execute",)
