from galaxy.web.base.controller import *

import simplejson

from galaxy.tools.parameters import DataToolParameter
from galaxy.tools import DefaultToolState
from galaxy.datatypes.data import Data
from galaxy.workflow import Workflow

class WorkflowEditor( BaseController ):
    beta = True
    
    @web.expose
    def index( self, trans ):
        user = trans.get_user()
        if not user:
            return trans.show_error_message( "Must be logged in to create or modify workflows" )
        return trans.fill_template( "workflow_editor/index.mako" )
    
    @web.expose
    def canvas( self, trans ):
        return trans.fill_template( "workflow_editor/canvas.mako" )
        
    @web.json
    def tool_form( self, trans, tool_id=None, **incoming ):
        trans.workflow_building_mode = True
        tool = trans.app.toolbox.tools_by_id[tool_id]
        state = DefaultToolState()
        state.decode( incoming.pop("tool_state"), tool, trans.app )
        errors = tool.update_state( trans, tool.inputs, state.inputs, incoming )
        rval = {}
        rval['form_html'] = trans.fill_template( "workflow_editor/tool_form.mako", 
            tool=tool, as_html=as_html, values=state.inputs, errors=errors )
        rval['has_errors'] = bool( errors )
        rval['state'] = state.encode( tool, trans.app )
        return rval
        
    @web.json
    def get_tool_info( self, trans, tool_id ):
        trans.workflow_building_mode = True
        tool = trans.app.toolbox.tools_by_id[tool_id]
        rval = {}
        rval['name'] = tool.name
        rval['tool_id'] = tool.id
        data_inputs = []
        for name, input in tool.inputs.iteritems():
            if isinstance( input, DataToolParameter ):
                data_inputs.append( dict( name=input.name, label=input.label, extensions=input.extensions ) )
        rval['data_inputs'] = data_inputs
        data_outputs = []
        for name, ( format, metadata_source, parent ) in tool.outputs.iteritems():
            data_outputs.append( dict( name=name, extension=format ) )
        rval['data_outputs'] = data_outputs
        state = tool.new_state( trans, all_pages=True )
        rval['form_html'] = trans.fill_template( "workflow_editor/tool_form.mako", 
            tool=tool, as_html=as_html, values=state.inputs, errors={} )
        rval['tool_state'] = state.encode( tool, trans.app )
        return rval
        
    @web.json
    def save_workflow( self, trans, workflow_data, workflow_name ):
        user = trans.get_user()
        trans.workflow_building_mode = True
        data = simplejson.loads( workflow_data )
        nodes = data['nodes']
        for key, node in nodes.iteritems():
            decode_state( node, trans.app )
        # Create workflow from json data
        workflow = Workflow.from_simple( data )
        # Store it
        stored = model.StoredWorkflow.get_by( user = user, name = workflow_name )
        if stored is None:
            stored = model.StoredWorkflow()
            stored.user = user
            stored.name = workflow_name
        stored.encoded_value = simplejson.dumps( workflow.to_simple() )
        stored.flush()
        # Return something informative
        errors = []
        if workflow.has_errors:
            errors.append( "Some steps in this workflow have validation errors" )
        if workflow.has_cycles:
            errors.append( "This workflow contains cycles" )
        if errors:
            rval = dict( message="Workflow saved, but will not be runnable due to the following errors",
                         errors=errors )
        else:
            rval = dict( message="Workflow saved" )
        rval['name'] = workflow_name
        return rval
        
    @web.json
    def load_workflow( self, trans, workflow_name ):
        user = trans.get_user()
        trans.workflow_building_mode = True
        # Load encoded workflow from database
        stored = model.StoredWorkflow.get_by( user = user, name = workflow_name )
        data = simplejson.loads( stored.encoded_value )
        # For each step, rebuild the form and encode the state
        for step in data['steps'].values():
            tool_id = step['tool_id']
            tool = trans.app.toolbox.tools_by_id[tool_id]
            # Build a state from the tool_inputs dict
            inputs = step['tool_inputs']
            state = DefaultToolState()
            state.inputs = inputs
            # Replace state in dict with encoded version
            step['tool_state'] = state.encode( tool, trans.app )
            del step['tool_inputs']
            # Input and output specs
            data_inputs = []
            for name, input in tool.inputs.iteritems():
                if isinstance( input, DataToolParameter ):
                    data_inputs.append( dict( name=input.name, label=input.label, extensions=input.extensions ) )
            step['data_inputs'] = data_inputs
            data_outputs = []
            for name, ( format, metadata_source, parent ) in tool.outputs.iteritems():
                data_outputs.append( dict( name=name, extension=format ) )
            step['data_outputs'] = data_outputs
            # Build the tool form html
            errors = step.get( 'errors', {} )
            step['form_html'] = trans.fill_template( "workflow_editor/tool_form.mako", 
                tool=tool, as_html=as_html, values=state.inputs, errors={} )
            step['name'] = tool.name
        data['name'] = stored.name
        return data
        
    @web.json
    def get_datatypes( self, trans ):
        ext_to_class_name = dict()
        classes = []
        for k, v in trans.app.datatypes_registry.datatypes_by_extension.iteritems():
            c = v.__class__
            ext_to_class_name[k] = c.__module__ + "." + c.__name__
            classes.append( c )
        class_to_classes = dict()
        def visit_bases( types, cls ):
            for base in cls.__bases__:
                if issubclass( base, Data ):
                    types.add( base.__module__ + "." + base.__name__ )
                visit_bases( types, base )
        for c in classes:      
            n =  c.__module__ + "." + c.__name__
            types = set( [ n ] )
            visit_bases( types, c )
            class_to_classes[ n ] = dict( ( t, True ) for t in types )
        return dict( ext_to_class_name=ext_to_class_name, class_to_classes=class_to_classes )
        
def as_html( param, value, trans, prefix ):
    if type( param ) is DataToolParameter:
        return "Data input '" + param.name + "' (" + ( " or ".join( param.extensions ) ) + ")"
    else:
        return param.get_html_field( trans, value ).get_html( prefix )
    
def decode_state( data, app ):
    """
    tool_inputs --> tool_state
    """
    tool = app.toolbox.tools_by_id[ data['tool_id'] ]
    state = DefaultToolState()
    state.decode( data['tool_state'], tool, app )
    data['tool_inputs'] = state.inputs
    del data['tool_state']
    
def encode_state( data, app ):
    """
    tool_state --> tool_inputs
    """
    tool = app.toolbox.tools_by_id[ data['tool_id'] ]
    state = DefaultToolState()
    state.inputs = data['tool_inputs']
    data['tool_state'] = state.encode( tool, app )
    del data['tool_inputs']