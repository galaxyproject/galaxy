from galaxy import model
from galaxy import exceptions

from galaxy.jobs.actions.post import ActionBox

from galaxy.tools.parameters.basic import DataToolParameter
from galaxy.tools.parameters import visit_input_values
from galaxy.util.odict import odict


def invoke( trans, workflow, target_history, replacement_dict, copy_inputs_to_history=False, ds_map={} ):
    """ Run the supplied workflow in the supplied target_history.
    """
    return WorkflowInvoker(
        trans,
        workflow,
        target_history,
        replacement_dict,
        copy_inputs_to_history=copy_inputs_to_history,
        ds_map=ds_map,
    ).invoke()


class WorkflowInvoker( object ):

    def __init__( self, trans, workflow, target_history, replacement_dict, copy_inputs_to_history, ds_map ):
        self.trans = trans
        self.workflow = workflow
        self.target_history = target_history
        self.replacement_dict = replacement_dict
        self.copy_inputs_to_history = copy_inputs_to_history
        self.ds_map = ds_map

        self.outputs = odict()

    def invoke( self ):
        workflow_invocation = model.WorkflowInvocation()
        workflow_invocation.workflow = self.workflow

        for step in self.workflow.steps:
            job = None
            job = self._invoke_step( step )
            # Record invocation
            workflow_invocation_step = model.WorkflowInvocationStep()
            workflow_invocation_step.workflow_invocation = workflow_invocation
            workflow_invocation_step.workflow_step = step
            workflow_invocation_step.job = job

        # All jobs ran successfully, so we can save now
        self.trans.sa_session.add( workflow_invocation )

        # Not flushing in here, because web controller may create multiple
        # invokations.
        return self.outputs

    def _invoke_step( self, step ):
        if step.type == 'tool' or step.type is None:
            job = self._execute_tool_step( step )
        else:
            job = self._execute_input_step( step )

        return job

    def _execute_tool_step( self, step ):
        trans = self.trans
        outputs = self.outputs

        tool = trans.app.toolbox.get_tool( step.tool_id )

        # Connect up
        def callback( input, value, prefixed_name, prefixed_label ):
            replacement = None
            if isinstance( input, DataToolParameter ):
                replacement = self._replacement_for_input( input, prefixed_name, step )
            return replacement
        try:
            # Replace DummyDatasets with historydatasetassociations
            visit_input_values( tool.inputs, step.state.inputs, callback )
        except KeyError, k:
            raise exceptions.MessageException( "Error due to input mapping of '%s' in '%s'.  A common cause of this is conditional outputs that cannot be determined until runtime, please review your workflow." % (tool.name, k.message))
        # Execute it
        job, out_data = tool.execute( trans, step.state.inputs, history=self.target_history )
        outputs[ step.id ] = out_data

        self._handle_post_job_actions( step, job )
        return job

    def _execute_input_step( self, step ):
        trans = self.trans
        outputs = self.outputs

        job, out_data = step.module.execute( trans, step.state )
        outputs[ step.id ] = out_data

        # Web controller may set copy_inputs_to_history, API controller always sets
        # ds_map.
        if self.copy_inputs_to_history:
            for input_dataset_hda in out_data.values():
                new_hda = input_dataset_hda.copy( copy_children=True )
                self.target_history.add_dataset( new_hda )
                outputs[ step.id ][ 'input_ds_copy' ] = new_hda
        if self.ds_map:
            outputs[ step.id ][ 'output' ] = self.ds_map[ str( step.id ) ][ 'hda' ]

        return job

    def _handle_post_job_actions( self, step, job ):
        # Create new PJA associations with the created job, to be run on completion.
        # PJA Parameter Replacement (only applies to immediate actions-- rename specifically, for now)
        # Pass along replacement dict with the execution of the PJA so we don't have to modify the object.
        for pja in step.post_job_actions:
            if pja.action_type in ActionBox.immediate_actions:
                ActionBox.execute( self.trans.app, self.trans.sa_session, pja, job, self.replacement_dict )
            else:
                job.add_post_job_action( pja )

    def _replacement_for_input( self, input, prefixed_name, step ):
        """ For given workflow 'step' that has had input_connections_by_name
        populated fetch the actual runtime input for the given tool 'input'.
        """
        replacement = None
        if prefixed_name in step.input_connections_by_name:
            outputs = self.outputs
            connection = step.input_connections_by_name[ prefixed_name ]
            if input.multiple:
                replacement = [ outputs[ c.output_step.id ][ c.output_name ] for c in connection ]
            else:
                replacement = outputs[ connection[ 0 ].output_step.id ][ connection[ 0 ].output_name ]
        return replacement

__all__ = [ invoke ]
