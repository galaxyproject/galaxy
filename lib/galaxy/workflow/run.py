import logging
import uuid
from typing import (
    List,
    Union,
)

from galaxy import model
from galaxy.util import ExecutionTimer
from galaxy.workflow import modules
from galaxy.workflow.run_request import (
    workflow_request_to_run_config,
    workflow_run_config_to_request,
    WorkflowRunConfig,
)

log = logging.getLogger(__name__)


# Entry point for core workflow scheduler.
def schedule(trans, workflow, workflow_run_config, workflow_invocation):
    return __invoke(trans, workflow, workflow_run_config, workflow_invocation)


def __invoke(trans, workflow, workflow_run_config, workflow_invocation=None, populate_state=False):
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
    try:
        outputs = invoker.invoke()
    except modules.CancelWorkflowEvaluation:
        if workflow_invocation:
            if workflow_invocation.cancel():
                trans.sa_session.add(workflow_invocation)
        outputs = []
    except Exception:
        log.exception("Failed to execute scheduled workflow.")
        if workflow_invocation:
            # Running workflow invocation in background, just mark
            # persistent workflow invocation as failed.
            workflow_invocation.fail()
            trans.sa_session.add(workflow_invocation)
        else:
            # Running new transient workflow invocation in legacy
            # controller action - propage the exception up.
            raise
        outputs = []

    if workflow_invocation:
        # Be sure to update state of workflow_invocation.
        trans.sa_session.flush()

    return outputs, invoker.workflow_invocation


def queue_invoke(trans, workflow, workflow_run_config, request_params=None, populate_state=True, flush=True):
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
    return trans.app.workflow_scheduling_manager.queue(workflow_invocation, request_params, flush=flush)


class WorkflowInvoker:
    def __init__(self, trans, workflow, workflow_run_config, workflow_invocation=None, progress=None):
        self.trans = trans
        self.workflow = workflow
        if progress is not None:
            assert workflow_invocation is None
            workflow_invocation = progress.workflow_invocation

        if workflow_invocation is None:
            invocation_uuid = uuid.uuid1()

            workflow_invocation = model.WorkflowInvocation()
            workflow_invocation.workflow = self.workflow

            # In one way or another, following attributes will become persistent
            # so they are available during delayed/revisited workflow scheduling.
            workflow_invocation.uuid = invocation_uuid
            workflow_invocation.history = workflow_run_config.target_history

            self.workflow_invocation = workflow_invocation
        else:
            self.workflow_invocation = workflow_invocation

        self.workflow_invocation.copy_inputs_to_history = workflow_run_config.copy_inputs_to_history
        self.workflow_invocation.use_cached_job = workflow_run_config.use_cached_job
        self.workflow_invocation.replacement_dict = workflow_run_config.replacement_dict

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
            )
        self.progress = progress

    def invoke(self):
        workflow_invocation = self.workflow_invocation
        config = self.trans.app.config
        maximum_duration = getattr(config, "maximum_workflow_invocation_duration", -1)
        if maximum_duration > 0 and workflow_invocation.seconds_since_created > maximum_duration:
            log.debug(
                f"Workflow invocation [{workflow_invocation.id}] exceeded maximum number of seconds allowed for scheduling [{maximum_duration}], failing."
            )
            workflow_invocation.state = model.WorkflowInvocation.states.FAILED
            # All jobs ran successfully, so we can save now
            self.trans.sa_session.add(workflow_invocation)

            # Not flushing in here, because web controller may create multiple
            # invocations.
            return self.progress.outputs

        if workflow_invocation.history.deleted:
            log.info("Cancelled workflow evaluation due to deleted history")
            raise modules.CancelWorkflowEvaluation()

        remaining_steps = self.progress.remaining_steps()
        delayed_steps = False
        max_jobs_per_iteration_reached = False
        for (step, workflow_invocation_step) in remaining_steps:
            max_jobs_to_schedule = self.progress.maximum_jobs_to_schedule_or_none
            if max_jobs_to_schedule is not None and max_jobs_to_schedule <= 0:
                max_jobs_per_iteration_reached = True
                break
            step_delayed = False
            step_timer = ExecutionTimer()
            try:
                self.__check_implicitly_dependent_steps(step)

                if not workflow_invocation_step:
                    workflow_invocation_step = model.WorkflowInvocationStep()
                    workflow_invocation_step.workflow_invocation = workflow_invocation
                    workflow_invocation_step.workflow_step = step
                    workflow_invocation_step.state = "new"

                    workflow_invocation.steps.append(workflow_invocation_step)

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
            except Exception:
                log.exception(
                    "Failed to schedule %s, problem occurred on %s.",
                    self.workflow_invocation.workflow.log_str(),
                    step.log_str(),
                )
                raise

            if not step_delayed:
                log.debug(f"Workflow step {step.id} of invocation {workflow_invocation.id} invoked {step_timer}")

        if delayed_steps or max_jobs_per_iteration_reached:
            state = model.WorkflowInvocation.states.READY
        else:
            state = model.WorkflowInvocation.states.SCHEDULED
        workflow_invocation.state = state

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
                self.__check_implicitly_dependent_step(output_id)

    def __check_implicitly_dependent_step(self, output_id):
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
                raise modules.CancelWorkflowEvaluation()

    def _invoke_step(self, invocation_step):
        incomplete_or_none = invocation_step.workflow_step.module.execute(
            self.trans, self.progress, invocation_step, use_cached_job=self.workflow_invocation.use_cached_job
        )
        return incomplete_or_none


STEP_OUTPUT_DELAYED = object()


class WorkflowProgress:
    def __init__(
        self, workflow_invocation, inputs_by_step_id, module_injector, param_map, jobs_per_scheduling_iteration=-1
    ):
        self.outputs = {}
        self.module_injector = module_injector
        self.workflow_invocation = workflow_invocation
        self.inputs_by_step_id = inputs_by_step_id
        self.param_map = param_map
        self.jobs_per_scheduling_iteration = jobs_per_scheduling_iteration
        self.jobs_scheduled_this_iteration = 0

    @property
    def maximum_jobs_to_schedule_or_none(self):
        if self.jobs_per_scheduling_iteration > 0:
            return self.jobs_per_scheduling_iteration - self.jobs_scheduled_this_iteration
        else:
            return None

    def record_executed_job_count(self, job_count):
        self.jobs_scheduled_this_iteration += job_count

    def remaining_steps(self):
        # Previously computed and persisted step states.
        step_states = self.workflow_invocation.step_states_by_step_id()
        steps = self.workflow_invocation.workflow.steps

        # TODO: Wouldn't a generator be much better here so we don't have to reason about
        # steps we are no where near ready to schedule?
        remaining_steps = []
        step_invocations_by_id = self.workflow_invocation.step_invocations_by_step_id()
        for step in steps:
            step_id = step.id
            if not hasattr(step, "module"):
                self.module_injector.inject(step, step_args=self.param_map.get(step.id, {}))
                if step_id not in step_states:
                    template = "Workflow invocation [%s] has no step state for step id [%s]. States ids are %s."
                    message = template % (self.workflow_invocation.id, step_id, list(step_states.keys()))
                    raise Exception(message)
                runtime_state = step_states[step_id].value
                step.state = step.module.decode_runtime_state(runtime_state)

            invocation_step = step_invocations_by_id.get(step_id, None)
            if invocation_step and invocation_step.state == "scheduled":
                self._recover_mapping(invocation_step)
            else:
                remaining_steps.append((step, invocation_step))
        return remaining_steps

    def replacement_for_input(self, step, input_dict):
        replacement: Union[
            modules.NoReplacement,
            model.DatasetCollectionInstance,
            List[model.DatasetCollectionInstance],
        ] = modules.NO_REPLACEMENT
        prefixed_name = input_dict["name"]
        multiple = input_dict["multiple"]
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
                is_data = input_dict["input_type"] in ["dataset", "dataset_collection"]
                replacement = self.replacement_for_connection(connection[0], is_data=is_data)

        return replacement

    def replacement_for_connection(self, connection, is_data=True):
        output_step_id = connection.output_step.id
        if output_step_id not in self.outputs:
            message = f"No outputs found for step id {output_step_id}, outputs are {self.outputs}"
            raise Exception(message)
        step_outputs = self.outputs[output_step_id]
        if step_outputs is STEP_OUTPUT_DELAYED:
            delayed_why = f"dependent step [{output_step_id}] delayed, so this step must be delayed"
            raise modules.DelayedWorkflowEvaluation(why=delayed_why)
        output_name = connection.output_name
        try:
            replacement = step_outputs[output_name]
        except KeyError:
            # Must resolve.
            template = "Workflow evaluation problem - failed to find output_name %s in step_outputs %s"
            message = template % (output_name, step_outputs)
            raise Exception(message)
        if isinstance(replacement, model.HistoryDatasetCollectionAssociation):
            if not replacement.collection.populated:
                if not replacement.waiting_for_elements:
                    # If we are not waiting for elements, there was some
                    # problem creating the collection. Collection will never
                    # be populated.
                    # TODO: consider distinguish between cancelled and failed?
                    raise modules.CancelWorkflowEvaluation()

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
                    raise modules.CancelWorkflowEvaluation()
            else:
                if not replacement.collection.populated:
                    raise modules.DelayedWorkflowEvaluation()
                pending = False
                for dataset_instance in replacement.dataset_instances:
                    if dataset_instance.is_pending:
                        pending = True
                    elif not dataset_instance.is_ok:
                        raise modules.CancelWorkflowEvaluation()
                if pending:
                    raise modules.DelayedWorkflowEvaluation()

        return replacement

    def get_replacement_workflow_output(self, workflow_output):
        step = workflow_output.workflow_step
        output_name = workflow_output.output_name
        step_outputs = self.outputs[step.id]
        if step_outputs is STEP_OUTPUT_DELAYED:
            delayed_why = f"depends on workflow output [{output_name}] but that output has not been created yet"
            raise modules.DelayedWorkflowEvaluation(why=delayed_why)
        else:
            return step_outputs[output_name]

    def set_outputs_for_input(self, invocation_step, outputs=None, already_persisted=False):
        step = invocation_step.workflow_step

        if outputs is None:
            outputs = {}

        if self.inputs_by_step_id:
            step_id = step.id
            if step_id not in self.inputs_by_step_id and "output" not in outputs:
                default_value = step.input_default_value
                if default_value or step.input_optional:
                    outputs["output"] = default_value
                else:
                    raise ValueError(f"{step.log_str()} not found in inputs_step_id {self.inputs_by_step_id}")
            elif step_id in self.inputs_by_step_id:
                outputs["output"] = self.inputs_by_step_id[step_id]

        self.set_step_outputs(invocation_step, outputs, already_persisted=already_persisted)

    def set_step_outputs(self, invocation_step, outputs, already_persisted=False):
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
                    if not workflow_outputs_by_name.get(output_name) and not output_object == modules.NO_REPLACEMENT:
                        workflow_output = model.WorkflowOutput(step, output_name=output_name)
                        step.workflow_outputs.append(workflow_output)
            for workflow_output in step.workflow_outputs:
                output_name = workflow_output.output_name
                if output_name not in outputs:
                    message = f"Failed to find expected workflow output [{output_name}] in step outputs [{outputs}]"
                    # raise KeyError(message)
                    # Pre-18.01 we would have never even detected this output wasn't configured
                    # and even in 18.01 we don't have a way to tell the user something bad is
                    # happening so I guess we just log a debug message and continue sadly for now.
                    # Once https://github.com/galaxyproject/galaxy/issues/5142 is complete we could
                    # at least tell the user what happened, give them a warning.
                    log.debug(message)
                    continue
                output = outputs[output_name]
                self._record_workflow_output(
                    step,
                    workflow_output,
                    output=output,
                )

    def _record_workflow_output(self, step, workflow_output, output):
        self.workflow_invocation.add_output(workflow_output, step, output)

    def mark_step_outputs_delayed(self, step, why=None):
        if why:
            message = f"Marking step {step.id} outputs of invocation {self.workflow_invocation.id} delayed ({why})"
            log.debug(message)
        self.outputs[step.id] = STEP_OUTPUT_DELAYED

    def _subworkflow_invocation(self, step):
        workflow_invocation = self.workflow_invocation
        subworkflow_invocation = workflow_invocation.get_subworkflow_invocation_for_step(step)
        if subworkflow_invocation is None:
            raise Exception(f"Failed to find persisted workflow invocation for step [{step.id}]")
        return subworkflow_invocation

    def subworkflow_invoker(self, trans, step, use_cached_job=False):
        subworkflow_invocation = self._subworkflow_invocation(step)
        workflow_run_config = workflow_request_to_run_config(trans, subworkflow_invocation)
        subworkflow_progress = self.subworkflow_progress(subworkflow_invocation, step, workflow_run_config.param_map)
        subworkflow_invocation = subworkflow_progress.workflow_invocation
        return WorkflowInvoker(
            trans,
            workflow=subworkflow_invocation.workflow,
            workflow_run_config=workflow_run_config,
            progress=subworkflow_progress,
        )

    def subworkflow_progress(self, subworkflow_invocation, step, param_map):
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
                raise Exception("Could not find connections for all subworkflow inputs.")

        return WorkflowProgress(subworkflow_invocation, subworkflow_inputs, self.module_injector, param_map=param_map)

    def _recover_mapping(self, step_invocation):
        try:
            step_invocation.workflow_step.module.recover_mapping(step_invocation, self)
        except modules.DelayedWorkflowEvaluation as de:
            self.mark_step_outputs_delayed(step_invocation.workflow_step, de.why)


__all__ = ("queue_invoke", "WorkflowRunConfig")
