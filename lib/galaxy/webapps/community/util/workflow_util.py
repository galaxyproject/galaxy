from galaxy import eggs
import pkg_resources

pkg_resources.require( "SVGFig" )

import logging, svgfig
from galaxy.util import json
import galaxy.util.shed_util_common as suc
from galaxy.tool_shed import encoding_util
from galaxy.workflow.modules import InputDataModule, ToolModule, WorkflowModuleFactory
import galaxy.webapps.galaxy.controllers.workflow
import galaxy.tools
import galaxy.tools.parameters

log = logging.getLogger( __name__ )

class RepoInputDataModule( InputDataModule ):

    type = "data_input"
    name = "Input dataset"

    @classmethod
    def new( Class, trans, tools_metadata=None, tool_id=None ):
        module = Class( trans )
        module.state = dict( name="Input Dataset" )
        return module
    @classmethod
    def from_dict( Class, trans, repository_id, changeset_revision, step_dict, tools_metadata=None, secure=True ):
        module = Class( trans )
        state = json.from_json_string( step_dict[ "tool_state" ] )
        module.state = dict( name=state.get( "name", "Input Dataset" ) )
        return module
    @classmethod
    def from_workflow_step( Class, trans, repository_id, changeset_revision, tools_metadata, step ):
        module = Class( trans )
        module.state = dict( name="Input Dataset" )
        if step.tool_inputs and "name" in step.tool_inputs:
            module.state[ 'name' ] = step.tool_inputs[ 'name' ]
        return module

class RepoToolModule( ToolModule ):
    
    type = "tool"
    
    def __init__( self, trans, repository_id, changeset_revision, tools_metadata, tool_id ):
        self.trans = trans
        self.tools_metadata = tools_metadata
        self.tool_id = tool_id
        self.tool = None
        self.errors = None
        for tool_dict in tools_metadata:
            if self.tool_id in [ tool_dict[ 'id' ], tool_dict[ 'guid' ] ]:
                if trans.webapp.name == 'community':
                    # We're in the tool shed.
                    repository, self.tool, message = suc.load_tool_from_changeset_revision( trans, repository_id, changeset_revision, tool_dict[ 'tool_config' ] )
                    if message and self.tool is None:
                        self.errors = 'unavailable'
                    break
                else:
                    # We're in Galaxy.
                    self.tool = trans.app.toolbox.tools_by_id.get( self.tool_id, None )
                    if self.tool is None:
                        self.errors = 'unavailable'
        self.post_job_actions = {}
        self.workflow_outputs = []
        self.state = None
    @classmethod
    def new( Class, trans, repository_id, changeset_revision, tools_metadata, tool_id=None ):
        module = Class( trans, repository_id, changeset_revision, tools_metadata, tool_id )
        module.state = module.tool.new_state( trans, all_pages=True )
        return module
    @classmethod
    def from_dict( Class, trans, repository_id, changeset_revision, step_dict, tools_metadata, secure=True ):
        tool_id = step_dict[ 'tool_id' ]
        module = Class( trans, repository_id, changeset_revision, tools_metadata, tool_id )
        module.state = galaxy.tools.DefaultToolState()
        if module.tool is not None:
            module.state.decode( step_dict[ "tool_state" ], module.tool, module.trans.app, secure=secure )
        module.errors = step_dict.get( "tool_errors", None )
        return module
    @classmethod
    def from_workflow_step( Class, trans, repository_id, changeset_revision, tools_metadata, step ):
        module = Class( trans, repository_id, changeset_revision, tools_metadata, step.tool_id )
        module.state = galaxy.tools.DefaultToolState()
        if module.tool:
            module.state.inputs = module.tool.params_from_strings( step.tool_inputs, trans.app, ignore_errors=True )
        else:
            module.state.inputs = {}
        module.errors = step.tool_errors
        return module
    def get_data_inputs( self ):
        data_inputs = []
        def callback( input, value, prefixed_name, prefixed_label ):
            if isinstance( input, galaxy.tools.parameters.DataToolParameter ):
                data_inputs.append( dict( name=prefixed_name,
                                          label=prefixed_label,
                                          extensions=input.extensions ) )
        if self.tool:
            galaxy.tools.parameters.visit_input_values( self.tool.inputs, self.state.inputs, callback )
        return data_inputs
    def get_data_outputs( self ):
        data_outputs = []
        if self.tool:
            data_inputs = None
            for name, tool_output in self.tool.outputs.iteritems():
                if tool_output.format_source != None:
                    # Default to special name "input" which remove restrictions on connections
                    formats = [ 'input' ]
                    if data_inputs == None:
                        data_inputs = self.get_data_inputs()
                    # Find the input parameter referenced by format_source
                    for di in data_inputs:
                        # Input names come prefixed with conditional and repeat names separated by '|',
                        # so remove prefixes when comparing with format_source.
                        if di[ 'name' ] != None and di[ 'name' ].split( '|' )[ -1 ] == tool_output.format_source:
                            formats = di[ 'extensions' ]
                else:
                    formats = [ tool_output.format ]
                for change_elem in tool_output.change_format:
                    for when_elem in change_elem.findall( 'when' ):
                        format = when_elem.get( 'format', None )
                        if format and format not in formats:
                            formats.append( format )
                data_outputs.append( dict( name=name, extensions=formats ) )
        return data_outputs

class RepoWorkflowModuleFactory( WorkflowModuleFactory ):
    def __init__( self, module_types ):
        self.module_types = module_types
    def new( self, trans, type, tools_metadata=None, tool_id=None ):
        """Return module for type and (optional) tool_id initialized with new / default state."""
        assert type in self.module_types
        return self.module_types[type].new( trans, tool_id )
    def from_dict( self, trans, repository_id, changeset_revision, step_dict, **kwd ):
        """Return module initialized from the data in dictionary `step_dict`."""
        type = step_dict[ 'type' ]
        assert type in self.module_types
        return self.module_types[ type ].from_dict( trans, repository_id, changeset_revision, step_dict, **kwd )
    def from_workflow_step( self, trans, repository_id, changeset_revision, tools_metadata, step ):
        """Return module initialized from the WorkflowStep object `step`."""
        type = step.type
        return self.module_types[ type ].from_workflow_step( trans, repository_id, changeset_revision, tools_metadata, step )

module_factory = RepoWorkflowModuleFactory( dict( data_input=RepoInputDataModule, tool=RepoToolModule ) )

def generate_workflow_image( trans, workflow_name, repository_metadata_id=None, repository_id=None ):
    """
    Return an svg image representation of a workflow dictionary created when the workflow was exported.  This method is called
    from both Galaxy and the tool shed.  When called from the tool shed, repository_metadata_id will have a value and repository_id
    will be None.  When called from Galaxy, repository_metadata_id will be None and repository_id will have a value.
    """
    workflow_name = encoding_util.tool_shed_decode( workflow_name )
    if trans.webapp.name == 'community':
        # We're in the tool shed.
        repository_metadata = suc.get_repository_metadata_by_id( trans, repository_metadata_id )
        repository_id = trans.security.encode_id( repository_metadata.repository_id )
        changeset_revision = repository_metadata.changeset_revision
        metadata = repository_metadata.metadata
    else:
        # We're in Galaxy.
        repository = suc.get_tool_shed_repository_by_id( trans, repository_id )
        changeset_revision = repository.changeset_revision
        metadata = repository.metadata
    # metadata[ 'workflows' ] is a list of tuples where each contained tuple is
    # [ <relative path to the .ga file in the repository>, <exported workflow dict> ]
    for workflow_tup in metadata[ 'workflows' ]:
        workflow_dict = workflow_tup[1]
        if workflow_dict[ 'name' ] == workflow_name:
            break
    if 'tools' in metadata:
        tools_metadata = metadata[ 'tools' ]
    else:
        tools_metadata = []
    workflow, missing_tool_tups = get_workflow_from_dict( trans=trans,
                                                          workflow_dict=workflow_dict,
                                                          tools_metadata=tools_metadata,
                                                          repository_id=repository_id,
                                                          changeset_revision=changeset_revision )
    data = []
    canvas = svgfig.canvas( style="stroke:black; fill:none; stroke-width:1px; stroke-linejoin:round; text-anchor:left" )
    text = svgfig.SVG( "g" )
    connectors = svgfig.SVG( "g" )
    boxes = svgfig.SVG( "g" )
    svgfig.Text.defaults[ "font-size" ] = "10px"
    in_pos = {}
    out_pos = {}
    margin = 5
    # Spacing between input/outputs.
    line_px = 16
    # Store px width for boxes of each step.
    widths = {}
    max_width, max_x, max_y = 0, 0, 0
    for step in workflow.steps:
        step.upgrade_messages = {}
        module = module_factory.from_workflow_step( trans, repository_id, changeset_revision, tools_metadata, step )
        tool_errors = module.type == 'tool' and not module.tool
        module_data_inputs = get_workflow_data_inputs( step, module )
        module_data_outputs = get_workflow_data_outputs( step, module, workflow.steps )
        step_dict = {
            'id' : step.order_index,
            'data_inputs' : module_data_inputs,
            'data_outputs' : module_data_outputs,
            'position' : step.position,
            'tool_errors' : tool_errors
        }
        input_conn_dict = {}
        for conn in step.input_connections:
            input_conn_dict[ conn.input_name ] = dict( id=conn.output_step.order_index, output_name=conn.output_name )
        step_dict[ 'input_connections' ] = input_conn_dict
        data.append( step_dict )
        x, y = step.position[ 'left' ], step.position[ 'top' ]
        count = 0
        module_name = get_workflow_module_name( module, missing_tool_tups )
        max_len = len( module_name ) * 1.5
        text.append( svgfig.Text( x, y + 20, module_name, **{ "font-size": "14px" } ).SVG() )
        y += 45
        for di in module_data_inputs:
            cur_y = y + count * line_px
            if step.order_index not in in_pos:
                in_pos[ step.order_index ] = {}
            in_pos[ step.order_index ][ di[ 'name' ] ] = ( x, cur_y )
            text.append( svgfig.Text( x, cur_y, di[ 'label' ] ).SVG() )
            count += 1
            max_len = max( max_len, len( di[ 'label' ] ) )
        if len( module.get_data_inputs() ) > 0:
            y += 15
        for do in module_data_outputs:
            cur_y = y + count * line_px
            if step.order_index not in out_pos:
                out_pos[ step.order_index ] = {}
            out_pos[ step.order_index ][ do[ 'name' ] ] = ( x, cur_y )
            text.append( svgfig.Text( x, cur_y, do[ 'name' ] ).SVG() )
            count += 1
            max_len = max( max_len, len( do['name' ] ) )
        widths[ step.order_index ] = max_len * 5.5
        max_x = max( max_x, step.position[ 'left' ] )
        max_y = max( max_y, step.position[ 'top' ] )
        max_width = max( max_width, widths[ step.order_index ] )
    for step_dict in data:
        tool_unavailable = step_dict[ 'tool_errors' ]
        width = widths[ step_dict[ 'id' ] ]
        x, y = step_dict[ 'position' ][ 'left' ], step_dict[ 'position' ][ 'top' ]
        # Only highlight missing tools if displaying in the tool shed.
        if trans.webapp.name == 'community' and tool_unavailable:
            fill = "#EBBCB2"
        else:
            fill = "#EBD9B2"    
        boxes.append( svgfig.Rect( x - margin, y, x + width - margin, y + 30, fill=fill ).SVG() )
        box_height = ( len( step_dict[ 'data_inputs' ] ) + len( step_dict[ 'data_outputs' ] ) ) * line_px + margin
        # Draw separator line.
        if len( step_dict[ 'data_inputs' ] ) > 0:
            box_height += 15
            sep_y = y + len( step_dict[ 'data_inputs' ] ) * line_px + 40
            text.append( svgfig.Line( x - margin, sep_y, x + width - margin, sep_y ).SVG() )
        # Define an input/output box.
        boxes.append( svgfig.Rect( x - margin, y + 30, x + width - margin, y + 30 + box_height, fill="#ffffff" ).SVG() )
        for conn, output_dict in step_dict[ 'input_connections' ].iteritems():
            in_coords = in_pos[ step_dict[ 'id' ] ][ conn ]
            # out_pos_index will be a step number like 1, 2, 3...
            out_pos_index = output_dict[ 'id' ]
            # out_pos_name will be a string like 'o', 'o2', etc.
            out_pos_name = output_dict[ 'output_name' ]
            if out_pos_index in out_pos:
                # out_conn_index_dict will be something like:
                # 7: {'o': (824.5, 618)}
                out_conn_index_dict = out_pos[ out_pos_index ]
                if out_pos_name in out_conn_index_dict:
                    out_conn_pos = out_pos[ out_pos_index ][ out_pos_name ]
                else:
                    # Take any key / value pair available in out_conn_index_dict.
                    # A problem will result if the dictionary is empty.
                    if out_conn_index_dict.keys():
                        key = out_conn_index_dict.keys()[0]
                        out_conn_pos = out_pos[ out_pos_index ][ key ]
            adjusted = ( out_conn_pos[ 0 ] + widths[ output_dict[ 'id' ] ], out_conn_pos[ 1 ] )
            text.append( svgfig.SVG( "circle",
                                     cx=out_conn_pos[ 0 ] + widths[ output_dict[ 'id' ] ] - margin,
                                     cy=out_conn_pos[ 1 ] - margin,
                                     r = 5,
                                     fill="#ffffff" ) )
            connectors.append( svgfig.Line( adjusted[ 0 ],
                                            adjusted[ 1 ] - margin,
                                            in_coords[ 0 ] - 10,
                                            in_coords[ 1 ],
                                            arrow_end = "true" ).SVG() )
    canvas.append( connectors )
    canvas.append( boxes )
    canvas.append( text )
    width, height = ( max_x + max_width + 50 ), max_y + 300
    canvas[ 'width' ] = "%s px" % width
    canvas[ 'height' ] = "%s px" % height
    canvas[ 'viewBox' ] = "0 0 %s %s" % ( width, height )
    trans.response.set_content_type( "image/svg+xml" )
    return canvas.standalone_xml()
def get_workflow_data_inputs( step, module ):
    if module.type == 'tool':
        if module.tool:
            return module.get_data_inputs()
        else:
            data_inputs = []
            for wfsc in step.input_connections:
                data_inputs_dict = {}
                data_inputs_dict[ 'extensions' ] = [ '' ]
                data_inputs_dict[ 'name' ] = wfsc.input_name
                data_inputs_dict[ 'label' ] = 'Unknown'
                data_inputs.append( data_inputs_dict )
            return data_inputs
    return module.get_data_inputs()
def get_workflow_data_outputs( step, module, steps ):
    if module.type == 'tool':
        if module.tool:
            return module.get_data_outputs()
        else:
            data_outputs = []
            data_outputs_dict = {}
            data_outputs_dict[ 'extensions' ] = [ 'input' ]
            found = False
            for workflow_step in steps:
                for wfsc in workflow_step.input_connections:
                    if step.name == wfsc.output_step.name:
                        data_outputs_dict[ 'name' ] = wfsc.output_name
                        found = True
                        break
                if found:
                    break
            if not found:
                # We're at the last step of the workflow.
                data_outputs_dict[ 'name' ] = 'output'
            data_outputs.append( data_outputs_dict )       
            return data_outputs
    return module.get_data_outputs()
def get_workflow_from_dict( trans, workflow_dict, tools_metadata, repository_id, changeset_revision ):
    """
    Return an in-memory Workflow object from the dictionary object created when it was exported.  This method is called from
    both Galaxy and the tool shed to retrieve a Workflow object that can be displayed as an SVG image.  This method is also
    called from Galaxy to retrieve a Workflow object that can be used for saving to the Galaxy database.
    """
    trans.workflow_building_mode = True
    workflow = trans.model.Workflow()
    workflow.name = workflow_dict[ 'name' ]
    workflow.has_errors = False
    steps = []
    # Keep ids for each step that we need to use to make connections.
    steps_by_external_id = {}
    # Keep track of tools required by the workflow that are not available in
    # the tool shed repository.  Each tuple in the list of missing_tool_tups
    # will be ( tool_id, tool_name, tool_version ).
    missing_tool_tups = []
    # First pass to build step objects and populate basic values
    for key, step_dict in workflow_dict[ 'steps' ].iteritems():
        # Create the model class for the step
        step = trans.model.WorkflowStep()
        step.name = step_dict[ 'name' ]
        step.position = step_dict[ 'position' ]
        module = module_factory.from_dict( trans, repository_id, changeset_revision, step_dict, tools_metadata=tools_metadata, secure=False )
        if module.type == 'tool' and module.tool is None:
            # A required tool is not available in the current repository.
            step.tool_errors = 'unavailable'
            missing_tool_tup = ( step_dict[ 'tool_id' ], step_dict[ 'name' ], step_dict[ 'tool_version' ] )
            if missing_tool_tup not in missing_tool_tups:
                missing_tool_tups.append( missing_tool_tup )
        module.save_to_step( step )
        if step.tool_errors:
            workflow.has_errors = True
        # Stick this in the step temporarily.
        step.temp_input_connections = step_dict[ 'input_connections' ]
        steps.append( step )
        steps_by_external_id[ step_dict[ 'id' ] ] = step
    # Second pass to deal with connections between steps.
    for step in steps:
        # Input connections.
        for input_name, conn_dict in step.temp_input_connections.iteritems():
            if conn_dict:
                output_step = steps_by_external_id[ conn_dict[ 'id' ] ]
                conn = trans.model.WorkflowStepConnection()
                conn.input_step = step
                conn.input_name = input_name
                conn.output_step = output_step
                conn.output_name = conn_dict[ 'output_name' ]
                step.input_connections.append( conn )
        del step.temp_input_connections
    # Order the steps if possible.
    galaxy.webapps.galaxy.controllers.workflow.attach_ordered_steps( workflow, steps )
    # Return the in-memory Workflow object for display or later persistence to the Galaxy database.
    return workflow, missing_tool_tups
def get_workflow_module_name( module, missing_tool_tups ):
    module_name = module.get_name()
    if module.type == 'tool' and module_name == 'unavailable':
        for missing_tool_tup in missing_tool_tups:
            missing_tool_id, missing_tool_name, missing_tool_version = missing_tool_tup
            if missing_tool_id == module.tool_id:
                module_name = '%s' % missing_tool_name
                break
    return module_name
def save_workflow( trans, workflow ):
    """Use the received in-memory Workflow object for saving to the Galaxy database."""
    stored = trans.model.StoredWorkflow()
    stored.name = workflow.name
    workflow.stored_workflow = stored
    stored.latest_workflow = workflow
    stored.user = trans.user
    trans.sa_session.add( stored )
    trans.sa_session.flush()
    # Add a new entry to the Workflows menu.
    if trans.user.stored_workflow_menu_entries is None:
        trans.user.stored_workflow_menu_entries = []
    menuEntry = trans.model.StoredWorkflowMenuEntry()
    menuEntry.stored_workflow = stored
    trans.user.stored_workflow_menu_entries.append( menuEntry )
    trans.sa_session.flush()
    return stored
