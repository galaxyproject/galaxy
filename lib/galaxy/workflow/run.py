import logging
import uuid
from collections.abc import MutableMapping
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
    Union,
)

from boltons.iterutils import get_path
from typing_extensions import Protocol

from galaxy import model
from galaxy.exceptions import MessageException
from galaxy.model import (
    WorkflowInvocation,
    WorkflowInvocationStep,
)
from galaxy.model.base import (
    ensure_object_added_to_session,
    transaction,
)
from galaxy.schema.invocation import (
    CancelReason,
    FAILURE_REASONS_EXPECTED,
    FailureReason,
    InvocationCancellationHistoryDeleted,
    InvocationFailureCollectionFailed,
    InvocationFailureDatasetFailed,
    InvocationFailureJobFailed,
    InvocationFailureOutputNotFound,
    InvocationUnexpectedFailure,
    InvocationWarningWorkflowOutputNotFound,
    WarningReason,
)
from galaxy.tools.parameters.basic import raw_to_galaxy
from galaxy.tools.parameters.workflow_utils import (
    NO_REPLACEMENT,
    NoReplacement,
)
from galaxy.tools.parameters.wrapped import nested_key_to_path
from galaxy.util import ExecutionTimer
from galaxy.workflow import modules
from galaxy.workflow.run_request import (
    workflow_request_to_run_config,
    workflow_run_config_to_request,
    WorkflowRunConfig,
)

if TYPE_CHECKING:
    from galaxy.model import (
        HistoryItem,
        Workflow,
        WorkflowOutput,
        WorkflowStep,
        WorkflowStepConnection,
    )
    from galaxy.webapps.base.webapp import GalaxyWebTransaction
    from galaxy.work.context import WorkRequestContext

log = logging.getLogger(__name__)

WorkflowOutputsType = Dict[int, Any]


# Entry point for core workflow scheduler.
def schedule(
    trans: "WorkRequestContext",
    workflow: "Workflow",
    workflow_run_config: WorkflowRunConfig,
    workflow_invocation: WorkflowInvocation,
) -> Tuple[WorkflowOutputsType, WorkflowInvocation]:
    return __invoke(trans, workflow, workflow_run_config, workflow_invocation)


def __invoke(
    trans: "WorkRequestContext",
    workflow: "Workflow",
    workflow_run_config: WorkflowRunConfig,
    workflow_invocation: Optional[WorkflowInvocation] = None,
    populate_state: bool = False,
) -> Tuple[WorkflowOutputsType, WorkflowInvocation]:
    """Run the supplied workflow in the supplied target_history."""
    if populate_state:
        modules.populate_module_and_state(
            trans,
            workflow,
            workflow_run_config.param_map,
            allow_tool_state_corrections=workflow_run_config.allow_tool_state_corrections,
        )

    invoker = WorkflowInvoker(
        trans,
        workflow,
        workflow_run_config,
        workflow_invocation=workflow_invocation,
    )
    workflow_invocation = invoker.workflow_invocation
    outputs = {}
    try:
        outputs = invoker.invoke()
    except modules.CancelWorkflowEvaluation as e:
        if workflow_invocation.cancel():
            workflow_invocation.add_message(e.why)
    except modules.FailWorkflowEvaluation as e:
        workflow_invocation.fail()
        workflow_invocation.add_message(e.why)
    except MessageException as e:
        # Convention for safe message we can show to users
        workflow_invocation.fail()
        failure = InvocationUnexpectedFailure(reason=FailureReason.unexpected_failure, details=str(e))
        workflow_invocation.add_message(failure)
    except Exception:
        # Could potentially be large and/or contain raw ids or other secrets, don't add details
        log.exception("Failed to execute scheduled workflow.")
        # Running workflow invocation in background, just mark
        # persistent workflow invocation as failed.
        failure = InvocationUnexpectedFailure(reason=FailureReason.unexpected_failure)
        workflow_invocation.fail()
        workflow_invocation.add_message(failure)

    # Be sure to update state of workflow_invocation.
    trans.sa_session.add(workflow_invocation)
    with transaction(trans.sa_session):
        trans.sa_session.commit()

    return outputs, workflow_invocation


def queue_invoke(
    trans: "GalaxyWebTransaction",
    workflow: "Workflow",
    workflow_run_config: WorkflowRunConfig,
    request_params: Optional[Dict[str, Any]] = None,
    populate_state: bool = True,
    flush: bool = True,
) -> WorkflowInvocation:
    request_params = request_params or {}
    if populate_state:
        modules.populate_module_and_state(
            trans,
            workflow,
            workflow_run_config.param_map,
            allow_tool_state_corrections=workflow_run_config.allow_tool_state_corrections,
        )
    workflow_invocation = workflow_run_config_to_request(trans, workflow_run_config, workflow)
    workflow_invocation.workflow = workflow
    initial_state = model.WorkflowInvocation.states.NEW
    if workflow_run_config.requires_materialization:
        initial_state = model.WorkflowInvocation.states.REQUIRES_MATERIALIZATION
    return trans.app.workflow_scheduling_manager.queue(
        workflow_invocation, request_params, flush=flush, initial_state=initial_state
    )


class WorkflowInvoker:
    progress: "WorkflowProgress"

    def __init__(
        self,
        trans: "WorkRequestContext",
        workflow: "Workflow",
        workflow_run_config: WorkflowRunConfig,
        workflow_invocation: Optional[WorkflowInvocation] = None,
        progress: Optional["WorkflowProgress"] = None,
    ) -> None:
        self.trans = trans
        self.workflow = workflow
        self.workflow_invocation: WorkflowInvocation
        if progress is not None:
            assert workflow_invocation is None
            workflow_invocation = progress.workflow_invocation

        if workflow_invocation is None:
            invocation_uuid = uuid.uuid1()

            workflow_invocation = WorkflowInvocation()
            workflow_invocation.workflow = self.workflow

            # In one way or another, following attributes will become persistent
            # so they are available during delayed/revisited workflow scheduling.
            workflow_invocation.uuid = invocation_uuid
            workflow_invocation.history = workflow_run_config.target_history

        self.workflow_invocation = workflow_invocation

        module_injector = modules.WorkflowModuleInjector(trans)
        if progress is None:
            progress = WorkflowProgress(
                self.workflow_invocation,
                workflow_run_config.inputs,
                module_injector,
                param_map=workflow_run_config.param_map,
                jobs_per_scheduling_iteration=getattr(
                    trans.app.config, "maximum_workflow_jobs_per_scheduling_iteration", -1
                ),
                copy_inputs_to_history=workflow_run_config.copy_inputs_to_history,
                use_cached_job=workflow_run_config.use_cached_job,
                replacement_dict=workflow_run_config.replacement_dict,
            )
        self.progress = progress

    def invoke(self) -> Dict[int, Any]:
        workflow_invocation = self.workflow_invocation
        config = self.trans.app.config
        maximum_duration = getattr(config, "maximum_workflow_invocation_duration", -1)
        if maximum_duration > 0 and workflow_invocation.seconds_since_created > maximum_duration:
            log.debug(
                f"Workflow invocation [{workflow_invocation.id}] exceeded maximum number of seconds allowed for scheduling [{maximum_duration}], failing."
            )
            workflow_invocation.set_state(model.WorkflowInvocation.states.FAILED)
            # All jobs ran successfully, so we can save now
            self.trans.sa_session.add(workflow_invocation)

            # Not flushing in here, because web controller may create multiple
            # invocations.
            return self.progress.outputs

        if workflow_invocation.history.deleted:
            raise modules.CancelWorkflowEvaluation(
                why=InvocationCancellationHistoryDeleted(
                    reason=CancelReason.history_deleted, history_id=workflow_invocation.history_id
                )
            )

        remaining_steps = self.progress.remaining_steps()
        delayed_steps = False
        max_jobs_per_iteration_reached = False
        for step, workflow_invocation_step in remaining_steps:
            max_jobs_to_schedule = self.progress.maximum_jobs_to_schedule_or_none
            if max_jobs_to_schedule is not None and max_jobs_to_schedule <= 0:
                max_jobs_per_iteration_reached = True
                break
            step_delayed = False
            step_timer = ExecutionTimer()
            try:
                self.__check_implicitly_dependent_steps(step)

                if not workflow_invocation_step:
                    workflow_invocation_step = WorkflowInvocationStep()
                    assert workflow_invocation_step
                    workflow_invocation_step.workflow_invocation = workflow_invocation
                    ensure_object_added_to_session(workflow_invocation_step, object_in_session=workflow_invocation)
                    workflow_invocation_step.workflow_step = step
                    workflow_invocation_step.state = "new"

                    workflow_invocation.steps.append(workflow_invocation_step)

                assert workflow_invocation_step
                incomplete_or_none = self._invoke_step(workflow_invocation_step)
                if incomplete_or_none is False:
                    step_delayed = delayed_steps = True
                    workflow_invocation_step.state = "ready"
                    self.progress.mark_step_outputs_delayed(step, why="Not all jobs scheduled for state.")
                else:
                    workflow_invocation_step.state = "scheduled"
            except modules.DelayedWorkflowEvaluation as de:
                step_delayed = delayed_steps = True
                self.progress.mark_step_outputs_delayed(step, why=de.why)
            except Exception as e:
                log_function = log.exception
                if isinstance(e, modules.FailWorkflowEvaluation) and e.why.reason in FAILURE_REASONS_EXPECTED:
                    log_function = log.info
                log_function(
                    "Failed to schedule %s for %s, problem occurred on %s.",
                    self.workflow_invocation.log_str(),
                    self.workflow_invocation.workflow.log_str(),
                    step.log_str(),
                )
                if isinstance(e, MessageException):
                    # This is the highest level at which we can inject the step id
                    # to provide some more context to the exception.
                    raise modules.FailWorkflowEvaluation(
                        why=InvocationUnexpectedFailure(
                            reason=FailureReason.unexpected_failure, details=str(e), workflow_step_id=step.id
                        )
                    )
                raise

            if not step_delayed:
                log.debug(f"Workflow step {step.id} of invocation {workflow_invocation.id} invoked {step_timer}")

        if delayed_steps or max_jobs_per_iteration_reached:
            state = model.WorkflowInvocation.states.READY
        else:
            state = model.WorkflowInvocation.states.SCHEDULED
        workflow_invocation.set_state(state)

        # All jobs ran successfully, so we can save now
        self.trans.sa_session.add(workflow_invocation)

        # Not flushing in here, because web controller may create multiple
        # invocations.
        return self.progress.outputs

    def __check_implicitly_dependent_steps(self, step):
        """Method will delay the workflow evaluation if implicitly dependent
        steps (steps dependent but not through an input->output way) are not
        yet complete.
        """
        for input_connection in step.input_connections:
            if input_connection.non_data_connection:
                output_id = input_connection.output_step.id
                self.__check_implicitly_dependent_step(output_id, step.id)

    def __check_implicitly_dependent_step(self, output_id: int, step_id: int):
        step_invocation = self.workflow_invocation.step_invocation_for_step_id(output_id)

        # No steps created yet - have to delay evaluation.
        if not step_invocation:
            delayed_why = f"depends on step [{output_id}] but that step has not been invoked yet"
            raise modules.DelayedWorkflowEvaluation(why=delayed_why)

        if step_invocation.state != "scheduled":
            delayed_why = f"depends on step [{output_id}] job has not finished scheduling yet"
            raise modules.DelayedWorkflowEvaluation(delayed_why)

        # TODO: Handle implicit dependency on stuff like pause steps.
        for job in step_invocation.jobs:
            # At least one job in incomplete.
            if not job.finished:
                delayed_why = (
                    f"depends on step [{output_id}] but one or more jobs created from that step have not finished yet"
                )
                raise modules.DelayedWorkflowEvaluation(why=delayed_why)

            if job.state != job.states.OK:
                raise modules.FailWorkflowEvaluation(
                    why=InvocationFailureJobFailed(
                        reason=FailureReason.job_failed,
                        job_id=job.id,
                        workflow_step_id=step_id,
                        dependent_workflow_step_id=output_id,
                    )
                )

    def _invoke_step(self, invocation_step: WorkflowInvocationStep) -> Optional[bool]:
        incomplete_or_none = invocation_step.workflow_step.module.execute(
            self.trans,
            self.progress,
            invocation_step,
            use_cached_job=self.progress.use_cached_job,
        )
        return incomplete_or_none


STEP_OUTPUT_DELAYED = object()


class ModuleInjector(Protocol):
    trans: "WorkRequestContext"

    def inject(self, step, step_args=None, steps=None, **kwargs):
        pass

    def inject_all(self, workflow: "Workflow", param_map=None, ignore_tool_missing_exception=True, **kwargs):
        pass

    def compute_runtime_state(self, step, step_args=None):
        pass


class WorkflowProgress:
    def __init__(
        self,
        workflow_invocation: WorkflowInvocation,
        inputs_by_step_id: Dict[int, Any],
        module_injector: ModuleInjector,
        param_map: Dict[int, Dict[str, Any]],
        jobs_per_scheduling_iteration: int = -1,
        copy_inputs_to_history: bool = False,
        use_cached_job: bool = False,
        replacement_dict: Optional[Dict[str, str]] = None,
        subworkflow_collection_info=None,
        when_values=None,
    ) -> None:
        self.outputs: Dict[int, Any] = {}
        self.module_injector = module_injector
        self.workflow_invocation = workflow_invocation
        self.inputs_by_step_id = inputs_by_step_id
        self.param_map = param_map
        self.jobs_per_scheduling_iteration = jobs_per_scheduling_iteration
        self.jobs_scheduled_this_iteration = 0
        self.copy_inputs_to_history = copy_inputs_to_history
        self.use_cached_job = use_cached_job
        self.replacement_dict = replacement_dict or {}
        self.runtime_replacements: Dict[str, str] = {}
        self.subworkflow_collection_info = subworkflow_collection_info
        self.subworkflow_structure = subworkflow_collection_info.structure if subworkflow_collection_info else None
        self.when_values = when_values

    @property
    def maximum_jobs_to_schedule_or_none(self) -> Optional[int]:
        if self.jobs_per_scheduling_iteration > 0:
            return self.jobs_per_scheduling_iteration - self.jobs_scheduled_this_iteration
        else:
            return None

    def record_executed_job_count(self, job_count: int) -> None:
        self.jobs_scheduled_this_iteration += job_count

    def remaining_steps(
        self,
    ) -> List[Tuple["WorkflowStep", Optional[WorkflowInvocationStep]]]:
        # Previously computed and persisted step states.
        step_states = self.workflow_invocation.step_states_by_step_id()
        steps = self.workflow_invocation.workflow.steps

        # TODO: Wouldn't a generator be much better here so we don't have to reason about
        # steps we are no where near ready to schedule?
        remaining_steps = []
        step_invocations_by_id = self.workflow_invocation.step_invocations_by_step_id()
        self.module_injector.inject_all(self.workflow_invocation.workflow, param_map=self.param_map)
        for step in steps:
            step_id = step.id
            step_args = self.param_map.get(step_id, {})
            self.module_injector.compute_runtime_state(step, step_args=step_args)
            if step_id not in step_states:
                # Can this ever happen?
                public_message = f"Workflow invocation has no step state for step {step.order_index + 1}"
                log.error(f"{public_message}. State is known for these step ids: {list(step_states.keys())}.")
                raise MessageException(public_message)
            runtime_state = step_states[step_id].value
            assert step.module
            step.state = step.module.decode_runtime_state(step, runtime_state)

            invocation_step = step_invocations_by_id.get(step_id, None)
            if invocation_step and invocation_step.state == "scheduled":
                self._recover_mapping(invocation_step)
            else:
                remaining_steps.append((step, invocation_step))
        return remaining_steps

    def replacement_for_input(self, trans, step: "WorkflowStep", input_dict: Dict[str, Any]):
        replacement: Union[
            NoReplacement,
            model.DatasetCollectionInstance,
            List[model.DatasetCollectionInstance],
            HistoryItem,
        ] = NO_REPLACEMENT
        prefixed_name = input_dict["name"]
        multiple = input_dict["multiple"]
        is_data = input_dict["input_type"] in ["dataset", "dataset_collection"]
        if prefixed_name in step.input_connections_by_name:
            connection = step.input_connections_by_name[prefixed_name]
            if input_dict["input_type"] == "dataset" and multiple:
                temp = [self.replacement_for_connection(c) for c in connection]
                # If replacement is just one dataset collection, replace tool
                # input_dict with dataset collection - tool framework will extract
                # datasets properly.
                if len(temp) == 1:
                    if isinstance(temp[0], model.HistoryDatasetCollectionAssociation):
                        replacement = temp[0]
                    else:
                        replacement = temp
                else:
                    replacement = temp
            else:
                replacement = self.replacement_for_connection(connection[0], is_data=is_data)
        elif step.state and (state_input := get_path(step.state.inputs, nested_key_to_path(prefixed_name), None)):
            # workflow submitted with step parameters populates state directly
            # via populate_module_and_state
            replacement = state_input
        else:
            for step_input in step.inputs:
                if step_input.name == prefixed_name and step_input.default_value_set:
                    if is_data:
                        replacement = raw_to_galaxy(trans.app, trans.history, step_input.default_value)
        return replacement

    def replacement_for_connection(self, connection: "WorkflowStepConnection", is_data: bool = True):
        output_step_id = connection.output_step.id
        output_name = connection.output_name
        if output_step_id not in self.outputs:
            raise modules.FailWorkflowEvaluation(
                why=InvocationFailureOutputNotFound(
                    reason=FailureReason.output_not_found,
                    workflow_step_id=connection.input_step_id,
                    output_name=output_name,
                    dependent_workflow_step_id=output_step_id,
                )
            )
        step_outputs = self.outputs[output_step_id]
        if step_outputs is STEP_OUTPUT_DELAYED:
            delayed_why = f"dependent step [{output_step_id}] delayed, so this step must be delayed"
            raise modules.DelayedWorkflowEvaluation(why=delayed_why)
        try:
            replacement = step_outputs[output_name]
        except KeyError:
            raise modules.FailWorkflowEvaluation(
                why=InvocationFailureOutputNotFound(
                    reason=FailureReason.output_not_found,
                    workflow_step_id=connection.input_step_id,
                    output_name=output_name,
                    dependent_workflow_step_id=output_step_id,
                )
            )
        if isinstance(replacement, MutableMapping) and replacement.get("__class__") == "NoReplacement":
            return NO_REPLACEMENT
        if isinstance(replacement, model.HistoryDatasetCollectionAssociation):
            if not replacement.collection.populated:
                if not replacement.waiting_for_elements:
                    # If we are not waiting for elements, there was some
                    # problem creating the collection. Collection will never
                    # be populated.
                    raise modules.FailWorkflowEvaluation(
                        why=InvocationFailureCollectionFailed(
                            reason=FailureReason.collection_failed,
                            hdca_id=replacement.id,
                            workflow_step_id=connection.input_step_id,
                            dependent_workflow_step_id=output_step_id,
                        )
                    )

                delayed_why = f"dependent collection [{replacement.id}] not yet populated with datasets"
                raise modules.DelayedWorkflowEvaluation(why=delayed_why)

        if isinstance(replacement, model.DatasetCollection):
            raise NotImplementedError
        if not is_data and isinstance(
            replacement, (model.HistoryDatasetAssociation, model.HistoryDatasetCollectionAssociation)
        ):
            if isinstance(replacement, model.HistoryDatasetAssociation):
                if replacement.is_pending:
                    raise modules.DelayedWorkflowEvaluation()
                if not replacement.is_ok:
                    raise modules.FailWorkflowEvaluation(
                        why=InvocationFailureDatasetFailed(
                            reason=FailureReason.dataset_failed,
                            hda_id=replacement.id,
                            workflow_step_id=connection.input_step_id,
                            dependent_workflow_step_id=output_step_id,
                        )
                    )
            else:
                if not replacement.collection.populated:
                    raise modules.DelayedWorkflowEvaluation()
                pending = False
                for dataset_instance in replacement.dataset_instances:
                    if dataset_instance.is_pending:
                        pending = True
                    elif not dataset_instance.is_ok:
                        raise modules.FailWorkflowEvaluation(
                            why=InvocationFailureDatasetFailed(
                                reason=FailureReason.dataset_failed,
                                hda_id=replacement.id,
                                workflow_step_id=connection.input_step_id,
                                dependent_workflow_step_id=output_step_id,
                            )
                        )
                if pending:
                    raise modules.DelayedWorkflowEvaluation()

        return replacement

    def get_replacement_workflow_output(self, workflow_output: "WorkflowOutput"):
        step = workflow_output.workflow_step
        output_name = workflow_output.output_name
        step_outputs = self.outputs[step.id]
        if step_outputs is STEP_OUTPUT_DELAYED:
            delayed_why = f"depends on workflow output [{output_name}] but that output has not been created yet"
            raise modules.DelayedWorkflowEvaluation(why=delayed_why)
        else:
            return step_outputs[output_name]

    def set_outputs_for_input(
        self,
        invocation_step: WorkflowInvocationStep,
        outputs: Optional[Dict[str, Any]] = None,
        already_persisted: bool = False,
    ) -> None:
        step = invocation_step.workflow_step

        if outputs is None:
            outputs = {}

        if self.inputs_by_step_id:
            step_id = step.id
            if step_id not in self.inputs_by_step_id and "output" not in outputs:
                default_value = step.get_input_default_value(NO_REPLACEMENT)
                outputs["output"] = default_value
            elif step_id in self.inputs_by_step_id:
                if self.inputs_by_step_id[step_id] is not None or "output" not in outputs:
                    outputs["output"] = self.inputs_by_step_id[step_id]

        if step.label and step.type == "parameter_input" and "output" in outputs:
            self.runtime_replacements[step.label] = str(outputs["output"])
        self.set_step_outputs(invocation_step, outputs, already_persisted=already_persisted)

    def effective_replacement_dict(self):
        replacement_dict = {}
        for key, value in self.replacement_dict.items():
            replacement_dict[key] = value
        for key, value in self.runtime_replacements.items():
            if key not in replacement_dict:
                replacement_dict[key] = value
        return replacement_dict

    def set_step_outputs(
        self, invocation_step: WorkflowInvocationStep, outputs: Dict[str, Any], already_persisted: bool = False
    ) -> None:
        step = invocation_step.workflow_step
        if invocation_step.output_value:
            outputs[invocation_step.output_value.workflow_output.output_name] = invocation_step.output_value.value
        self.outputs[step.id] = outputs
        if not already_persisted:
            workflow_outputs_by_name = {wo.output_name: wo for wo in step.workflow_outputs}
            for output_name, output_object in outputs.items():
                if hasattr(output_object, "history_content_type"):
                    invocation_step.add_output(output_name, output_object)
                else:
                    # Add this non-data, non workflow-output output to the workflow outputs.
                    # This is required for recovering the output in the next scheduling iteration,
                    # and should be replaced with a WorkflowInvocationStepOutputValue ASAP.
                    if not workflow_outputs_by_name.get(output_name) and output_object is not NO_REPLACEMENT:
                        workflow_output = model.WorkflowOutput(step, output_name=output_name)
                        step.workflow_outputs.append(workflow_output)
            for workflow_output in step.workflow_outputs:
                assert workflow_output.output_name
                output_name = workflow_output.output_name
                if output_name not in outputs:
                    invocation_step.workflow_invocation.add_message(
                        InvocationWarningWorkflowOutputNotFound(
                            reason=WarningReason.workflow_output_not_found,
                            workflow_step_id=step.id,
                            output_name=output_name,
                        )
                    )
                    message = f"Failed to find expected workflow output [{output_name}] in step outputs [{outputs}]"
                    log.debug(message)
                    continue
                output = outputs[output_name]
                self._record_workflow_output(
                    step,
                    workflow_output,
                    output=output,
                )

    def _record_workflow_output(self, step: "WorkflowStep", workflow_output: "WorkflowOutput", output: Any) -> None:
        if output is NO_REPLACEMENT:
            output = {"__class__": "NoReplacement"}
        self.workflow_invocation.add_output(workflow_output, step, output)

    def mark_step_outputs_delayed(self, step: "WorkflowStep", why: Optional[str] = None) -> None:
        if why:
            message = f"Marking step {step.id} outputs of invocation {self.workflow_invocation.id} delayed ({why})"
            log.debug(message)
        self.outputs[step.id] = STEP_OUTPUT_DELAYED

    def _subworkflow_invocation(self, step: "WorkflowStep") -> WorkflowInvocation:
        workflow_invocation = self.workflow_invocation
        subworkflow_invocation = workflow_invocation.get_subworkflow_invocation_for_step(step)
        if subworkflow_invocation is None:
            assert step.order_index
            raise MessageException(f"Failed to find persisted subworkflow invocation for step [{step.order_index + 1}]")
        return subworkflow_invocation

    def subworkflow_invoker(
        self,
        trans: "WorkRequestContext",
        step: "WorkflowStep",
        use_cached_job: bool = False,
        subworkflow_collection_info=None,
        when_values=None,
    ) -> WorkflowInvoker:
        subworkflow_invocation = self._subworkflow_invocation(step)
        subworkflow_invocation.handler = self.workflow_invocation.handler
        subworkflow_invocation.scheduler = self.workflow_invocation.scheduler
        workflow_run_config = workflow_request_to_run_config(subworkflow_invocation, use_cached_job)
        subworkflow_progress = self.subworkflow_progress(
            subworkflow_invocation,
            step,
            workflow_run_config.param_map,
            subworkflow_collection_info=subworkflow_collection_info,
            when_values=when_values,
        )
        subworkflow_invocation = subworkflow_progress.workflow_invocation
        return WorkflowInvoker(
            trans,
            workflow=subworkflow_invocation.workflow,
            workflow_run_config=workflow_run_config,
            progress=subworkflow_progress,
        )

    def subworkflow_progress(
        self,
        subworkflow_invocation: WorkflowInvocation,
        step: "WorkflowStep",
        param_map: Dict,
        subworkflow_collection_info=None,
        when_values=None,
    ) -> "WorkflowProgress":
        subworkflow = subworkflow_invocation.workflow
        subworkflow_inputs = {}
        for input_subworkflow_step in subworkflow.input_steps:
            connection_found = False
            subworkflow_step_id = input_subworkflow_step.id
            for input_connection in step.input_connections:
                if input_connection.input_subworkflow_step_id == subworkflow_step_id:
                    is_data = input_connection.output_step.type != "parameter_input"
                    replacement = self.replacement_for_connection(
                        input_connection,
                        is_data=is_data,
                    )
                    subworkflow_inputs[subworkflow_step_id] = replacement
                    connection_found = True
                    break

            if not connection_found and not input_subworkflow_step.input_optional:
                raise modules.FailWorkflowEvaluation(
                    InvocationFailureOutputNotFound(
                        reason=FailureReason.output_not_found,
                        workflow_step_id=step.id,
                        output_name=input_connection.output_name,
                        dependent_workflow_step_id=input_connection.output_step.id,
                    )
                )

        return WorkflowProgress(
            subworkflow_invocation,
            subworkflow_inputs,
            self.module_injector,
            param_map=param_map,
            use_cached_job=self.use_cached_job,
            replacement_dict=self.replacement_dict,
            subworkflow_collection_info=subworkflow_collection_info,
            when_values=when_values,
        )

    def raw_to_galaxy(self, value: dict):
        return raw_to_galaxy(self.module_injector.trans.app, self.module_injector.trans.history, value)

    def _recover_mapping(self, step_invocation: WorkflowInvocationStep) -> None:
        try:
            step_invocation.workflow_step.module.recover_mapping(step_invocation, self)
        except modules.DelayedWorkflowEvaluation as de:
            self.mark_step_outputs_delayed(step_invocation.workflow_step, de.why)


__all__ = ("queue_invoke", "WorkflowRunConfig")
