import uuid

from galaxy import model
from galaxy import util

from galaxy.util.odict import odict
from galaxy.workflow import modules
from galaxy.workflow.run_request import WorkflowRunConfig

import logging
log = logging.getLogger( __name__ )


def invoke( trans, workflow, workflow_run_config, populate_state=False ):
    """ Run the supplied workflow in the supplied target_history.
    """
    if populate_state:
        modules.populate_module_and_state( trans, workflow, workflow_run_config.param_map )

    return WorkflowInvoker(
        trans,
        workflow,
        workflow_run_config,
    ).invoke()


class WorkflowInvoker( object ):

    def __init__( self, trans, workflow, workflow_run_config ):
        self.trans = trans
        self.workflow = workflow
        workflow_invocation = model.WorkflowInvocation()
        workflow_invocation.workflow = self.workflow
        self.workflow_invocation = workflow_invocation
        self.progress = WorkflowProgress( self.workflow_invocation, workflow_run_config.inputs )

        invocation_uuid = uuid.uuid1().hex

        # In one way or another, following attributes will become persistent
        # so they are available during delayed/revisited workflow scheduling.
        self.workflow_invocation.uuid = invocation_uuid
        self.workflow_invocation.history = workflow_run_config.target_history
        self.workflow_invocation.copy_inputs_to_history = workflow_run_config.copy_inputs_to_history
        self.workflow_invocation.replacement_dict = workflow_run_config.replacement_dict

    def invoke( self ):
        workflow_invocation = self.workflow_invocation
        remaining_steps = self.progress.remaining_steps()
        for step in remaining_steps:
            jobs = self._invoke_step( step )
            for job in util.listify( jobs ):
                # Record invocation
                workflow_invocation_step = model.WorkflowInvocationStep()
                workflow_invocation_step.workflow_invocation = workflow_invocation
                workflow_invocation_step.workflow_step = step
                workflow_invocation_step.job = job

        # All jobs ran successfully, so we can save now
        self.trans.sa_session.add( workflow_invocation )

        # Not flushing in here, because web controller may create multiple
        # invocations.
        return self.progress.outputs

    def _invoke_step( self, step ):
        jobs = step.module.execute( self.trans, self.progress, self.workflow_invocation, step )
        return jobs


class WorkflowProgress( object ):

    def __init__( self, workflow_invocation, inputs_by_step_id ):
        self.outputs = odict()
        self.workflow_invocation = workflow_invocation
        self.inputs_by_step_id = inputs_by_step_id

    def remaining_steps(self):
        steps = self.workflow_invocation.workflow.steps

        return steps

    def replacement_for_tool_input( self, step, input, prefixed_name ):
        """ For given workflow 'step' that has had input_connections_by_name
        populated fetch the actual runtime input for the given tool 'input'.
        """
        replacement = None
        if prefixed_name in step.input_connections_by_name:
            connection = step.input_connections_by_name[ prefixed_name ]
            if input.multiple:
                replacement = [ self.replacement_for_connection( c ) for c in connection ]
                # If replacement is just one dataset collection, replace tool
                # input with dataset collection - tool framework will extract
                # datasets properly.
                if len( replacement ) == 1:
                    if isinstance( replacement[ 0 ], model.HistoryDatasetCollectionAssociation ):
                        replacement = replacement[ 0 ]
            else:
                replacement = self.replacement_for_connection( connection[ 0 ] )
        return replacement

    def replacement_for_connection( self, connection ):
        step_outputs = self.outputs[ connection.output_step.id ]
        return step_outputs[ connection.output_name ]

    def set_outputs_for_input( self, step, outputs={} ):
        if self.inputs_by_step_id:
            outputs[ 'output' ] = self.inputs_by_step_id[ step.id ]

        self.set_step_outputs( step, outputs )

    def set_step_outputs(self, step, outputs):
        self.outputs[ step.id ] = outputs


__all__ = [ invoke, WorkflowRunConfig ]
