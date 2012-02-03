import pkg_resources
pkg_resources.require( "simplejson" )
pkg_resources.require( "SVGFig" )
import os, logging, ConfigParser, tempfile, shutil, svgfig
from galaxy.webapps.community import model
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.util.json import from_json_string, to_json_string
from galaxy.workflow.modules import InputDataModule, ToolModule, WorkflowModuleFactory
from galaxy.tools import DefaultToolState
from galaxy.web.controllers.workflow import attach_ordered_steps
from galaxy.model.orm import *
from common import *

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
        state = from_json_string( step_dict[ "tool_state" ] )
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
                self.tool, message = load_tool_from_changeset_revision( trans, repository_id, changeset_revision, tool_dict[ 'tool_config' ] )
                if message and self.tool is None:
                    self.errors = 'unavailable'
                break
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
        module.state = DefaultToolState()
        if module.tool is not None:
            module.state.decode( step_dict[ "tool_state" ], module.tool, module.trans.app, secure=secure )
        module.errors = step_dict.get( "tool_errors", None )
        return module
    @classmethod
    def from_workflow_step( Class, trans, repository_id, changeset_revision, tools_metadata, step ):
        module = Class( trans, repository_id, changeset_revision, tools_metadata, step.tool_id )
        module.state = DefaultToolState()
        if module.tool:
            module.state.inputs = module.tool.params_from_strings( step.tool_inputs, trans.app, ignore_errors=True )
        else:
            module.state.inputs = {}
        module.errors = step.tool_errors
        return module
    def get_data_inputs( self ):
        data_inputs = []
        def callback( input, value, prefixed_name, prefixed_label ):
            if isinstance( input, DataToolParameter ):
                data_inputs.append( dict( name=prefixed_name,
                                          label=prefixed_label,
                                          extensions=input.extensions ) )
        if self.tool:
            visit_input_values( self.tool.inputs, self.state.inputs, callback )
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

class WorkflowController( BaseUIController ):
    @web.expose
    def view_workflow( self, trans, **kwd ):
        repository_metadata_id = kwd.get( 'repository_metadata_id', '' )
        workflow_name = kwd.get( 'workflow_name', '' )
        if workflow_name:
            workflow_name = decode( workflow_name )
        webapp = kwd.get( 'webapp', 'community' )
        message = kwd.get( 'message', '' )
        status = kwd.get( 'status', 'done' )
        repository_metadata = get_repository_metadata_by_id( trans, repository_metadata_id )
        repository = get_repository( trans, trans.security.encode_id( repository_metadata.repository_id ) )
        return trans.fill_template( "/webapps/community/repository/view_workflow.mako",
                                    repository=repository,
                                    changeset_revision=repository_metadata.changeset_revision,
                                    repository_metadata_id=repository_metadata_id,
                                    workflow_name=workflow_name,
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    def generate_workflow_image( self, trans, repository_metadata_id, workflow_name, webapp='community' ):
        repository_metadata = get_repository_metadata_by_id( trans, repository_metadata_id )
        repository_id = trans.security.encode_id( repository_metadata.repository_id )
        changeset_revision = repository_metadata.changeset_revision
        metadata = repository_metadata.metadata
        workflow_name = decode( workflow_name )
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
        workflow, missing_tool_tups = self.__workflow_from_dict( trans, workflow_dict, tools_metadata, repository_id, changeset_revision )
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
            module_data_inputs = self.__get_data_inputs( step, module )
            module_data_outputs = self.__get_data_outputs( step, module, workflow.steps )
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
            module_name = self.__get_name( module, missing_tool_tups )
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
            if tool_unavailable:
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
    def __get_name( self, module, missing_tool_tups ):
        module_name = module.get_name()
        if module.type == 'tool' and module_name == 'unavailable':
            for missing_tool_tup in missing_tool_tups:
                missing_tool_id, missing_tool_name, missing_tool_version = missing_tool_tup
                if missing_tool_id == module.tool_id:
                    module_name = '%s' % missing_tool_name
        return module_name
    def __get_data_inputs( self, step, module ):
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
    def __get_data_outputs( self, step, module, steps ):
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
    def __workflow_from_dict( self, trans, workflow_dict, tools_metadata, repository_id, changeset_revision ):
        """Creates and returns workflow object from a dictionary."""
        trans.workflow_building_mode = True
        workflow = model.Workflow()
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
            step = model.WorkflowStep()
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
                    conn = model.WorkflowStepConnection()
                    conn.input_step = step
                    conn.input_name = input_name
                    conn.output_step = output_step
                    conn.output_name = conn_dict[ 'output_name' ]
                    step.input_connections.append( conn )
            del step.temp_input_connections
        # Order the steps if possible.
        attach_ordered_steps( workflow, steps )
        return workflow, missing_tool_tups
    @web.expose
    def import_workflow( self, trans, **kwd ):
        repository_metadata_id = kwd.get( 'repository_metadata_id', '' )
        workflow_name = kwd.get( 'workflow_name', '' )
        if workflow_name:
            workflow_name = decode( workflow_name )
        webapp = kwd.get( 'webapp', 'community' )
        message = kwd.get( 'message', '' )
        status = kwd.get( 'status', 'done' )
        repository_metadata = get_repository_metadata_by_id( trans, repository_metadata_id )
        workflows = repository_metadata.metadata[ 'workflows' ]
        workflow_data = None
        for workflow_data in workflows:
            if workflow_data[ 'name' ] == workflow_name:
                break
        if workflow_data:
            if kwd.get( 'open_for_url', False ):
                tmp_fd, tmp_fname = tempfile.mkstemp()
                to_file = open( tmp_fname, 'wb' )
                to_file.write( to_json_string( workflow_data ) )
                return open( tmp_fname )
            galaxy_url = trans.get_cookie( name='toolshedgalaxyurl' )
            url = '%sworkflow/import_workflow?tool_shed_url=%s&repository_metadata_id=%s&workflow_name=%s&webapp=%s' % \
                ( galaxy_url, url_for( '/', qualified=True ), repository_metadata_id, encode( workflow_name ), webapp )
            return trans.response.send_redirect( url )
        return trans.response.send_redirect( web.url_for( controller='workflow',
                                                          action='view_workflow',
                                                          message=message,
                                                          status=status ) )
