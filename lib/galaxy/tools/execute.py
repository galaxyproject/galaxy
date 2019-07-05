"""
Once state information has been calculated, handle actually executing tools
from various states, tracking results, and building implicit dataset
collections from matched collections.
"""
import collections
import logging
from threading import Thread

import six
import six.moves
from six.moves.queue import Queue

from galaxy import model
from galaxy.dataset_collections.structure import get_structure, tool_output_to_structure
from galaxy.tools.actions import filter_output, on_text_for_names, ToolExecutionCache
from galaxy.tools.parser import ToolOutputCollectionPart
from galaxy.util import ExecutionTimer

log = logging.getLogger(__name__)

EXECUTION_SUCCESS_MESSAGE = "Tool [%s] created job [%s] %s"


class PartialJobExecution(Exception):

    def __init__(self, execution_tracker):
        self.execution_tracker = execution_tracker


MappingParameters = collections.namedtuple("MappingParameters", ["param_template", "param_combinations"])


def execute(trans, tool, mapping_params, history, rerun_remap_job_id=None, collection_info=None, workflow_invocation_uuid=None, invocation_step=None, max_num_jobs=None, job_callback=None, completed_jobs=None, workflow_resource_parameters=None):
    """
    Execute a tool and return object containing summary (output data, number of
    failures, etc...).
    """
    if max_num_jobs:
        assert invocation_step is not None
    if rerun_remap_job_id:
        assert invocation_step is None

    all_jobs_timer = ExecutionTimer()
    if invocation_step is None:
        execution_tracker = ToolExecutionTracker(trans, tool, mapping_params, collection_info)
    else:
        execution_tracker = WorkflowStepExecutionTracker(trans, tool, mapping_params, collection_info, invocation_step, job_callback=job_callback)
    app = trans.app
    execution_cache = ToolExecutionCache(trans)

    def execute_single_job(execution_slice, completed_job):
        job_timer = ExecutionTimer()
        params = execution_slice.param_combination
        if workflow_invocation_uuid:
            params['__workflow_invocation_uuid__'] = workflow_invocation_uuid
        elif '__workflow_invocation_uuid__' in params:
            # Only workflow invocation code gets to set this, ignore user supplied
            # values or rerun parameters.
            del params['__workflow_invocation_uuid__']
        if workflow_resource_parameters:
            params['__workflow_resource_params__'] = workflow_resource_parameters
        elif '__workflow_resource_params__' in params:
            # Only workflow invocation code gets to set this, ignore user supplied
            # values or rerun parameters.
            del params['__workflow_resource_params__']
        job, result = tool.handle_single_execution(trans, rerun_remap_job_id, execution_slice, history, execution_cache, completed_job, collection_info)
        if job:
            message = EXECUTION_SUCCESS_MESSAGE % (tool.id, job.id, job_timer)
            log.debug(message)
            execution_tracker.record_success(execution_slice, job, result)
        else:
            execution_tracker.record_error(result)

    tool_action = tool.tool_action
    if hasattr(tool_action, "check_inputs_ready"):
        for params in execution_tracker.param_combinations:
            # This will throw an exception if the tool is not ready.
            tool_action.check_inputs_ready(
                tool,
                trans,
                params,
                history,
                execution_cache=execution_cache,
                collection_info=collection_info,
            )

    execution_tracker.ensure_implicit_collections_populated(history, mapping_params.param_template)
    config = app.config
    burst_at = getattr(config, 'tool_submission_burst_at', 10)
    burst_threads = getattr(config, 'tool_submission_burst_threads', 1)

    job_count = len(execution_tracker.param_combinations)

    jobs_executed = 0
    has_remaining_jobs = False

    if (job_count < burst_at or burst_threads < 2):
        for i, execution_slice in enumerate(execution_tracker.new_execution_slices()):
            if max_num_jobs and jobs_executed >= max_num_jobs:
                has_remaining_jobs = True
                break
            else:
                execute_single_job(execution_slice, completed_jobs[i])
    else:
        # TODO: re-record success...
        q = Queue()

        def worker():
            while True:
                params = q.get()
                execute_single_job(params)
                q.task_done()

        for i in range(burst_threads):
            t = Thread(target=worker)
            t.daemon = True
            t.start()

        for i, execution_slice in enumerate(execution_tracker.new_execution_slices()):
            if max_num_jobs and jobs_executed >= max_num_jobs:
                has_remaining_jobs = True
                break
            else:
                q.put(execution_slice, completed_jobs[i])
                jobs_executed += 1

        q.join()

    if has_remaining_jobs:
        raise PartialJobExecution(execution_tracker)
    else:
        execution_tracker.finalize_dataset_collections(trans)

    log.debug("Executed %d job(s) for tool %s request: %s" % (job_count, tool.id, all_jobs_timer))
    return execution_tracker


class ExecutionSlice(object):

    def __init__(self, job_index, param_combination, dataset_collection_elements=None):
        self.job_index = job_index
        self.param_combination = param_combination
        self.dataset_collection_elements = dataset_collection_elements


class ExecutionTracker(object):

    def __init__(self, trans, tool, mapping_params, collection_info):
        # Known ahead of time...
        self.trans = trans
        self.tool = tool
        self.mapping_params = mapping_params
        self.collection_info = collection_info

        self._on_text = None

        # Populated as we go...
        self.failed_jobs = 0
        self.execution_errors = []

        self.successful_jobs = []
        self.output_datasets = []
        self.output_collections = []

        self.implicit_collections = collections.OrderedDict()

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
        if self._on_text is None:
            collection_names = ["collection %d" % c.hid for c in self.collection_info.collections.values()]
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
            output_collection_name = "%s across %s" % (self.tool.name, on_text)

        return output_collection_name

    def sliced_input_collection_structure(self, input_name):
        unqualified_recurse = self.tool.profile < 18.09 and "|" not in input_name

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

        collection_type_description = self.trans.app.dataset_collections_service.collection_type_descriptions.for_collection_type(input_collection.collection.collection_type)
        subcollection_mapping_type = None
        if self.is_implicit_input(input_name):
            subcollection_mapping_type = self.collection_info.subcollection_mapping_type(input_name)

        return get_structure(input_collection, collection_type_description, leaf_subcollection_type=subcollection_mapping_type)

    def _structure_for_output(self, trans, tool_output):
        structure = self.collection_info.structure
        if hasattr(tool_output, "default_identifier_source"):
            # Switch the structure for outputs if the output specified a default_identifier_source
            collection_type_descriptions = trans.app.dataset_collections_service.collection_type_descriptions

            source_collection = self.collection_info.collections.get(tool_output.default_identifier_source)
            if source_collection:
                collection_type_description = collection_type_descriptions.for_collection_type(source_collection.collection.collection_type)
                _structure = structure.for_dataset_collection(source_collection.collection, collection_type_description=collection_type_description)
                if structure.can_match(_structure):
                    structure = _structure

        return structure

    def _mapped_output_structure(self, trans, tool_output):
        collections_manager = trans.app.dataset_collections_service
        output_structure = tool_output_to_structure(self.sliced_input_collection_structure, tool_output, collections_manager)
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
        trans = self.trans
        params.update(self.collection_info.collections)  # Replace datasets with source collections for labelling outputs.

        collection_instances = {}
        implicit_inputs = self.implicit_inputs

        implicit_collection_jobs = model.ImplicitCollectionJobs()
        for output_name, output in self.tool.outputs.items():
            if filter_output(output, self.example_params):
                continue
            output_collection_name = self.output_name(trans, history, params, output)
            effective_structure = self._mapped_output_structure(trans, output)
            collection_instance = trans.app.dataset_collections_service.precreate_dataset_collection_instance(
                trans=trans,
                parent=history,
                name=output_collection_name,
                structure=effective_structure,
                implicit_inputs=implicit_inputs,
                implicit_output_name=output_name,
            )
            collection_instance.implicit_collection_jobs = implicit_collection_jobs
            collection_instances[output_name] = collection_instance
            trans.sa_session.add(collection_instance)
        # Needed to flush the association created just above with
        # job.add_output_dataset_collection.
        trans.sa_session.flush()
        self.implicit_collections = collection_instances

    @property
    def implicit_collection_jobs(self):
        # TODO: refactor to track this properly maybe?
        if self.implicit_collections:
            return six.next(six.itervalues(self.implicit_collections)).implicit_collection_jobs
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
                implicit_collection.collection.handle_population_failed("One or more jobs failed during dataset initialization.")
                trans.sa_session.add(implicit_collection.collection)
        else:
            for i, implicit_collection in enumerate(self.implicit_collections.values()):
                if i == 0:
                    implicit_collection_jobs = implicit_collection.implicit_collection_jobs
                    implicit_collection_jobs.populated_state = "ok"
                    trans.sa_session.add(implicit_collection_jobs)
                implicit_collection.collection.finalize()
                trans.sa_session.add(implicit_collection.collection)
        trans.sa_session.flush()

    @property
    def implicit_inputs(self):
        implicit_inputs = list(self.collection_info.collections.items())
        return implicit_inputs

    def is_implicit_input(self, input_name):
        return input_name in self.collection_info.collections

    def walk_implicit_collections(self):
        return self.collection_info.structure.walk_collections(self.implicit_collections)

    def new_execution_slices(self):
        if self.collection_info is None:
            for job_index, param_combination in enumerate(self.param_combinations):
                yield ExecutionSlice(job_index, param_combination)
        else:
            for execution_slice in self.new_collection_execution_slices():
                yield execution_slice

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
            job_assoc.job_id = job.id
            self.trans.sa_session.add(job_assoc)


# Seperate these because workflows need to track their jobs belong to the invocation
# in the database immediately and they can be recovered.
class ToolExecutionTracker(ExecutionTracker):

    def __init__(self, trans, tool, mapping_params, collection_info):
        super(ToolExecutionTracker, self).__init__(trans, tool, mapping_params, collection_info)

        # New to track these things for tool output API response in the tool case,
        # in the workflow case we just write stuff to the database and forget about
        # it.
        self.outputs_by_output_name = collections.defaultdict(list)

    def record_success(self, execution_slice, job, outputs):
        super(ToolExecutionTracker, self).record_success(execution_slice, job, outputs)
        for output_name, output_dataset in outputs:
            if ToolOutputCollectionPart.is_named_collection_part_name(output_name):
                # Skip known collection outputs, these will be covered by
                # output collections.
                continue
            self.outputs_by_output_name[output_name].append(output_dataset)
        for job_output in job.output_dataset_collections:
            self.outputs_by_output_name[job_output.name].append(job_output.dataset_collection)

    def new_collection_execution_slices(self):
        for job_index, (param_combination, dataset_collection_elements) in enumerate(six.moves.zip(self.param_combinations, self.walk_implicit_collections())):
            for dataset_collection_element in dataset_collection_elements.values():
                assert dataset_collection_element.element_object is None

            yield ExecutionSlice(job_index, param_combination, dataset_collection_elements)


class WorkflowStepExecutionTracker(ExecutionTracker):

    def __init__(self, trans, tool, mapping_params, collection_info, invocation_step, job_callback):
        super(WorkflowStepExecutionTracker, self).__init__(trans, tool, mapping_params, collection_info)
        self.invocation_step = invocation_step
        self.job_callback = job_callback

    def record_success(self, execution_slice, job, outputs):
        super(WorkflowStepExecutionTracker, self).record_success(execution_slice, job, outputs)
        if self.collection_info:
            self.invocation_step.implicit_collection_jobs = self.implicit_collection_jobs
        else:
            self.invocation_step.job = job
        self.job_callback(job)

    def new_collection_execution_slices(self):
        for job_index, (param_combination, dataset_collection_elements) in enumerate(six.moves.zip(self.param_combinations, self.walk_implicit_collections())):
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
        else:
            collections = {}
            for output_assoc in self.invocation_step.output_dataset_collections:
                implicit_collection = output_assoc.dataset_collection
                assert hasattr(implicit_collection, "history_content_type")  # make sure it is an HDCA and not a DC
                collections[output_assoc.output_name] = output_assoc.dataset_collection
            self.implicit_collections = collections


__all__ = ('execute', )
