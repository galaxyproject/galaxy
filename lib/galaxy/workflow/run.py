import logging
import uuid

from galaxy import model, util
from galaxy.util import ExecutionTimer
from galaxy.util.odict import odict
from galaxy.workflow import modules
from galaxy.workflow.run_request import (workflow_run_config_to_request,
    WorkflowRunConfig)

log = logging.getLogger( __name__ )


# Entry point for direct invoke via controllers. Deprecated to some degree.
def invoke( trans, workflow, workflow_run_config, workflow_invocation=None, populate_state=False ):
    if force_queue( trans, workflow ):
        invocation = queue_invoke( trans, workflow, workflow_run_config, populate_state=populate_state )
        return [], invocation
    else:
        return __invoke( trans, workflow, workflow_run_config, workflow_invocation, populate_state )


# Entry point for core workflow scheduler.
def schedule( trans, workflow, workflow_run_config, workflow_invocation ):
    return __invoke( trans, workflow, workflow_run_config, workflow_invocation )


BASIC_WORKFLOW_STEP_TYPES = [ None, "tool", "data_input", "data_collection_input" ]


def force_queue( trans, workflow ):
    # Default behavior is still to just schedule workflows completley right
    # away. This can be modified here in various ways.

    # TODO: check for implicit connections - these should also force backgrounding
    #       this would fix running Dan's data manager workflows via UI.
    # TODO: ensure state if populated before calling force_queue from old API
    #       workflow endpoint so the has_module check below is unneeded and these
    #       interesting workflows will work with the older endpoint.
    config = trans.app.config
    force_for_collection = config.force_beta_workflow_scheduled_for_collections
    force_min_steps = config.force_beta_workflow_scheduled_min_steps

    step_count = len( workflow.steps )
    if step_count > force_min_steps:
        log.info("Workflow has many steps %d, backgrounding execution" % step_count)
        return True
    for step in workflow.steps:
        # State and module haven't been populated if workflow submitted via
        # the API. API requests for "interesting" workflows should use newer
        # endpoint that skips this check entirely - POST /api/workflows/<id>/invocations
        has_module = hasattr(step, "module")
        if step.type not in BASIC_WORKFLOW_STEP_TYPES:
            log.info("Found non-basic workflow step type - backgrounding execution")
            # Force all new beta modules types to be use force queueing of
            # workflow.
            return True
        if step.type == "data_collection_input" and force_for_collection:
            log.info("Found collection input step - backgrounding execution")
            return True
        if step.type == "tool" and has_module and step.module.tool.produces_collections_with_unknown_structure:
            log.info("Found dynamically structured output collection - backgrounding execution")
            return True
    return False


def __invoke( trans, workflow, workflow_run_config, workflow_invocation=None, populate_state=False ):
    """ Run the supplied workflow in the supplied target_history.
    """
    if populate_state:
        modules.populate_module_and_state( trans, workflow, workflow_run_config.param_map, allow_tool_state_corrections=workflow_run_config.allow_tool_state_corrections )

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
                trans.sa_session.add( workflow_invocation )
        outputs = []
    except Exception:
        log.exception("Failed to execute scheduled workflow.")
        if workflow_invocation:
            # Running workflow invocation in background, just mark
            # persistent workflow invocation as failed.
            workflow_invocation.fail()
            trans.sa_session.add( workflow_invocation )
        else:
            # Running new transient workflow invocation in legacy
            # controller action - propage the exception up.
            raise
        outputs = []

    if workflow_invocation:
        # Be sure to update state of workflow_invocation.
        trans.sa_session.flush()

    return outputs, invoker.workflow_invocation


def queue_invoke( trans, workflow, workflow_run_config, request_params={}, populate_state=True ):
    if populate_state:
        modules.populate_module_and_state( trans, workflow, workflow_run_config.param_map, allow_tool_state_corrections=workflow_run_config.allow_tool_state_corrections )
    workflow_invocation = workflow_run_config_to_request( trans, workflow_run_config, workflow )
    workflow_invocation.workflow = workflow
    return trans.app.workflow_scheduling_manager.queue( workflow_invocation, request_params )


class WorkflowInvoker( object ):

    def __init__( self, trans, workflow, workflow_run_config, workflow_invocation=None, progress=None ):
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
        self.workflow_invocation.replacement_dict = workflow_run_config.replacement_dict

        module_injector = modules.WorkflowModuleInjector( trans )
        if progress is None:
            progress = WorkflowProgress( self.workflow_invocation, workflow_run_config.inputs, module_injector )
        self.progress = progress

    def invoke( self ):
        workflow_invocation = self.workflow_invocation
        remaining_steps = self.progress.remaining_steps()
        delayed_steps = False
        for step in remaining_steps:
            step_delayed = False
            step_timer = ExecutionTimer()
            jobs = None
            try:
                self.__check_implicitly_dependent_steps(step)

                # TODO: step may fail to invoke, do something about that.
                jobs = self._invoke_step( step )
                for job in (util.listify( jobs ) or [None]):
                    # Record invocation
                    workflow_invocation_step = model.WorkflowInvocationStep()
                    workflow_invocation_step.workflow_invocation = workflow_invocation
                    workflow_invocation_step.workflow_step = step
                    # Job may not be generated in this thread if bursting is enabled
                    # https://github.com/galaxyproject/galaxy/issues/2259
                    if job:
                        workflow_invocation_step.job_id = job.id
            except modules.DelayedWorkflowEvaluation:
                step_delayed = delayed_steps = True
                self.progress.mark_step_outputs_delayed( step )
            except Exception:
                log.exception(
                    "Failed to schedule %s, problem occurred on %s.",
                    self.workflow_invocation.workflow.log_str(),
                    step.log_str(),
                )
                raise

            step_verb = "invoked" if not step_delayed else "delayed"
            log.debug("Workflow step %s of invocation %s %s %s" % (step.id, workflow_invocation.id, step_verb, step_timer))

        if delayed_steps:
            state = model.WorkflowInvocation.states.READY
        else:
            state = model.WorkflowInvocation.states.SCHEDULED
        workflow_invocation.state = state

        # All jobs ran successfully, so we can save now
        self.trans.sa_session.add( workflow_invocation )

        # Not flushing in here, because web controller may create multiple
        # invocations.
        return self.progress.outputs

    def __check_implicitly_dependent_steps( self, step ):
        """ Method will delay the workflow evaluation if implicitly dependent
        steps (steps dependent but not through an input->output way) are not
        yet complete.
        """
        for input_connection in step.input_connections:
            if input_connection.non_data_connection:
                output_id = input_connection.output_step.id
                self.__check_implicitly_dependent_step( output_id )

    def __check_implicitly_dependent_step( self, output_id ):
        step_invocations = self.workflow_invocation.step_invocations_for_step_id( output_id )

        # No steps created yet - have to delay evaluation.
        if not step_invocations:
            raise modules.DelayedWorkflowEvaluation()

        for step_invocation in step_invocations:
            job = step_invocation.job
            if job:
                # At least one job in incomplete.
                if not job.finished:
                    raise modules.DelayedWorkflowEvaluation()

                if job.state != job.states.OK:
                    raise modules.CancelWorkflowEvaluation()

            else:
                # TODO: Handle implicit dependency on stuff like
                # pause steps.
                pass

    def _invoke_step( self, step ):
        jobs = step.module.execute( self.trans, self.progress, self.workflow_invocation, step )
        return jobs


STEP_OUTPUT_DELAYED = object()


class WorkflowProgress( object ):

    def __init__( self, workflow_invocation, inputs_by_step_id, module_injector ):
        self.outputs = odict()
        self.module_injector = module_injector
        self.workflow_invocation = workflow_invocation
        self.inputs_by_step_id = inputs_by_step_id

    def remaining_steps(self):
        # Previously computed and persisted step states.
        step_states = self.workflow_invocation.step_states_by_step_id()
        steps = self.workflow_invocation.workflow.steps
        remaining_steps = []
        step_invocations_by_id = self.workflow_invocation.step_invocations_by_step_id()
        for step in steps:
            step_id = step.id
            if not hasattr( step, 'module' ):
                self.module_injector.inject( step )
                if step_id not in step_states:
                    template = "Workflow invocation [%s] has no step state for step id [%s]. States ids are %s."
                    message = template % (self.workflow_invocation.id, step_id, list(step_states.keys()))
                    raise Exception(message)
                runtime_state = step_states[ step_id ].value
                step.state = step.module.recover_runtime_state( runtime_state )

            invocation_steps = step_invocations_by_id.get( step_id, None )
            if invocation_steps:
                self._recover_mapping( step, invocation_steps )
            else:
                remaining_steps.append( step )
        return remaining_steps

    def replacement_for_tool_input( self, step, input, prefixed_name ):
        """ For given workflow 'step' that has had input_connections_by_name
        populated fetch the actual runtime input for the given tool 'input'.
        """
        replacement = modules.NO_REPLACEMENT
        if prefixed_name in step.input_connections_by_name:
            connection = step.input_connections_by_name[ prefixed_name ]
            if input.type == "data" and input.multiple:
                replacement = [ self.replacement_for_connection( c ) for c in connection ]
                # If replacement is just one dataset collection, replace tool
                # input with dataset collection - tool framework will extract
                # datasets properly.
                if len( replacement ) == 1:
                    if isinstance( replacement[ 0 ], model.HistoryDatasetCollectionAssociation ):
                        replacement = replacement[ 0 ]
            else:
                is_data = input.type in ["data", "data_collection"]
                replacement = self.replacement_for_connection( connection[ 0 ], is_data=is_data )
        return replacement

    def replacement_for_connection( self, connection, is_data=True ):
        output_step_id = connection.output_step.id
        if output_step_id not in self.outputs:
            template = "No outputs found for step id %s, outputs are %s"
            message = template % (output_step_id, self.outputs)
            raise Exception(message)
        step_outputs = self.outputs[ output_step_id ]
        if step_outputs is STEP_OUTPUT_DELAYED:
            raise modules.DelayedWorkflowEvaluation()
        output_name = connection.output_name
        try:
            replacement = step_outputs[ output_name ]
        except KeyError:
            if is_data:
                # Must resolve.
                template = "Workflow evaluation problem - failed to find output_name %s in step_outputs %s"
                message = template % ( output_name, step_outputs )
                raise Exception( message )
            else:
                replacement = modules.NO_REPLACEMENT
        if isinstance( replacement, model.HistoryDatasetCollectionAssociation ):
            if not replacement.collection.populated:
                if not replacement.collection.waiting_for_elements:
                    # If we are not waiting for elements, there was some
                    # problem creating the collection. Collection will never
                    # be populated.
                    # TODO: consider distinguish between cancelled and failed?
                    raise modules.CancelWorkflowEvaluation()

                raise modules.DelayedWorkflowEvaluation()
        return replacement

    def get_replacement_workflow_output( self, workflow_output ):
        step = workflow_output.workflow_step
        output_name = workflow_output.output_name
        return self.outputs[ step.id ][ output_name ]

    def set_outputs_for_input( self, step, outputs=None ):
        if outputs is None:
            outputs = {}

        if self.inputs_by_step_id:
            step_id = step.id
            if step_id not in self.inputs_by_step_id:
                template = "Step with id %s not found in inputs_step_id (%s)"
                message = template % (step_id, self.inputs_by_step_id)
                raise ValueError(message)
            outputs[ 'output' ] = self.inputs_by_step_id[ step_id ]

        self.set_step_outputs( step, outputs )

    def set_step_outputs(self, step, outputs):
        self.outputs[ step.id ] = outputs

    def mark_step_outputs_delayed(self, step):
        self.outputs[ step.id ] = STEP_OUTPUT_DELAYED

    def _subworkflow_invocation(self, step):
        workflow_invocation = self.workflow_invocation
        subworkflow_invocation = workflow_invocation.get_subworkflow_invocation_for_step(step)
        if subworkflow_invocation is None:
            raise Exception("Failed to find persisted workflow invocation for step [%s]" % step.id)
        return subworkflow_invocation

    def subworkflow_invoker(self, trans, step):
        subworkflow_progress = self.subworkflow_progress(step)
        subworkflow_invocation = subworkflow_progress.workflow_invocation
        workflow_run_config = WorkflowRunConfig(
            target_history=subworkflow_invocation.history,
            replacement_dict={},
            inputs={},
            param_map={},
            copy_inputs_to_history=False,
        )
        return WorkflowInvoker(
            trans,
            workflow=subworkflow_invocation.workflow,
            workflow_run_config=workflow_run_config,
            progress=subworkflow_progress,
        )

    def subworkflow_progress(self, step):
        subworkflow_invocation = self._subworkflow_invocation(step)
        subworkflow = subworkflow_invocation.workflow
        subworkflow_inputs = {}
        for input_subworkflow_step in subworkflow.input_steps:
            connection_found = False
            for input_connection in step.input_connections:
                if input_connection.input_subworkflow_step == input_subworkflow_step:
                    subworkflow_step_id = input_subworkflow_step.id
                    is_data = input_connection.output_step.type != "parameter_input"
                    replacement = self.replacement_for_connection(
                        input_connection,
                        is_data=is_data,
                    )
                    subworkflow_inputs[subworkflow_step_id] = replacement
                    connection_found = True
                    break

            if not connection_found:
                raise Exception("Could not find connections for all subworkflow inputs.")

        return WorkflowProgress(
            subworkflow_invocation,
            subworkflow_inputs,
            self.module_injector,
        )

    def _recover_mapping( self, step, step_invocations ):
        try:
            step.module.recover_mapping( step, step_invocations, self )
        except modules.DelayedWorkflowEvaluation:
            self.mark_step_outputs_delayed( step )


__all__ = ( 'invoke', 'WorkflowRunConfig' )
