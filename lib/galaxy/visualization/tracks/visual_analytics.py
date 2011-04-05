import urllib

from galaxy.tools.parameters.basic import IntegerToolParameter, FloatToolParameter, SelectToolParameter
from galaxy.tools.parameters.dynamic_options import DynamicOptions

def get_dataset_job( hda ):
    # Get dataset's job.
    job = None
    for job_output_assoc in hda.creating_job_associations:
        job = job_output_assoc.job
        break
    return job

def get_tool_def( trans, hda ):
    """ Returns definition of an interactive tool for an HDA. """
    
    job = get_dataset_job( hda )
    # TODO: could use this assertion to provide more information.
    # assert job is not None, 'Requested job has not been loaded.'
    if not job:
        return {}
    tool = trans.app.toolbox.tools_by_id.get( job.tool_id, None )
    # TODO: could use this assertion to provide more information.
    # assert tool is not None, 'Requested tool has not been loaded.'
    if not tool:
        return {}

    # Get list of tool parameters that can be interactively modified.
    tool_params = []
    tool_param_values = dict( [ ( p.name, p.value ) for p in job.parameters ] )
    tool_param_values = tool.params_from_strings( tool_param_values, trans.app, ignore_errors=True )
    for name, input in tool.inputs.items():
        if type( input ) == IntegerToolParameter or type( input ) == FloatToolParameter:
            param_dict = { 'name' : name, 'label' : input.label, \
                           'value' : tool_param_values.get( name, input.value ), \
                           'type' : 'number', 'init_value' : input.value,
                           'html' : urllib.quote( input.get_html() ) }
            if input.min:
                param_dict['min'] = input.min
            if input.max:
                param_dict['max'] = input.max
            tool_params.append( param_dict )
        elif type( input ) == SelectToolParameter and type( input.options ) != DynamicOptions:
            tool_params.append( { 'name' : name, 'label' : input.label, 'type' : 'select', \
                                  'html' : urllib.quote( input.get_html() ) } )
        
    # If tool has parameters that can be interactively modified, return tool.
    # Return empty set otherwise.
    if len( tool_params ) != 0:
        return { 'name' : tool.name, 'params' : tool_params } 
    return {}