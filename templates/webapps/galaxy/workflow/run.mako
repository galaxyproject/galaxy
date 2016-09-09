<%inherit file="/base.mako"/>

${h.js("libs/bibtex", "libs/jquery/jquery-ui")}
${h.css('jquery-ui/smoothness/jquery-ui')}
<%
    from galaxy.tools.parameters import params_to_incoming
    from galaxy.jobs.actions.post import ActionBox
    from galaxy.tools.parameters.basic import workflow_building_modes
    step_models = []
    for i, step in enumerate( steps ):
        step_model = None
        if step.type == 'tool':
            incoming = {}
            tool = trans.app.toolbox.get_tool( step.tool_id )
            params_to_incoming( incoming, tool.inputs, step.state.inputs, trans.app )
            step_model = tool.to_json( trans, incoming, workflow_building_mode=workflow_building_modes.USE_HISTORY )
            step_model[ 'post_job_actions' ] = [{
                'short_str'         : ActionBox.get_short_str( pja ),
                'action_type'       : pja.action_type,
                'output_name'       : pja.output_name,
                'action_arguments'  : pja.action_arguments
            } for pja in step.post_job_actions ]
        else:
            inputs = step.module.get_runtime_inputs( connections=step.output_connections )
            step_model = {
                'name'   : step.module.name,
                'inputs' : [ input.to_dict( trans ) for input in inputs.itervalues() ]
            }
        step_model[ 'step_id' ] = step.id
        step_model[ 'step_type' ] = step.type
        step_model[ 'output_connections' ] = [ {
            'input_step_id'     : oc.input_step_id,
            'output_step_id'    : oc.output_step_id,
            'input_name'        : oc.input_name,
            'output_name'       : oc.output_name
        } for oc in step.output_connections ]
        if step.annotations:
            step_model[ 'annotation' ] = step.annotations[0].annotation
        if step.upgrade_messages:
            step_model[ 'messages' ] = step.upgrade_messages
        step_models.append( step_model )
    self.form_config = {
        'id'                    : app.security.encode_id( workflow.id ),
        'name'                  : workflow.name,
        'history_id'            : history_id,
        'steps'                 : step_models,
        'has_upgrade_messages'  : has_upgrade_messages
    }
%>
<script>
    require(['mvc/tool/tool-form-composite'], function( ToolForm ) {
        $(function() {
            var form = new ToolForm.View(${ h.dumps( self.form_config ) });
        });
    });
</script>
