import re
from elementtree.ElementTree import Element
from galaxy import web
from galaxy.tools.parameters import DataToolParameter, DummyDataset, RuntimeValue, check_param, visit_input_values
from galaxy.tools import DefaultToolState
from galaxy.tools.parameters.grouping import Repeat, Conditional
from galaxy.util.bunch import Bunch
from galaxy.util.json import from_json_string, to_json_string
from galaxy.jobs.actions.post import ActionBox
from galaxy.model import PostJobAction
import logging

log = logging.getLogger( __name__ )

class WorkflowModule( object ):
    
    def __init__( self, trans ):
        self.trans = trans
    
    ## ---- Creating modules from various representations ---------------------
    
    @classmethod
    def new( Class, trans, tool_id=None ):
        """
        Create a new instance of the module with default state
        """
        return Class( trans )
    @classmethod
    def from_dict( Class, trans, d ):
        """
        Create a new instance of the module initialized from values in the
        dictionary `d`.
        """
        return Class( trans )
    @classmethod
    def from_workflow_step( Class, trans, step ):
        return Class( trans )

    ## ---- Saving in various forms ------------------------------------------
    
    def save_to_step( self, step ):
        step.type = self.type
        
    ## ---- General attributes -----------------------------------------------
    
    def get_type( self ):
        return self.type
    def get_name( self ):
        return self.name
    def get_tool_id( self ):
        return None
    def get_tooltip( self ):
        return None
    
    ## ---- Configuration time -----------------------------------------------
    
    def get_state( self ):
        return None
    def get_errors( self ):
        return None
    def get_data_inputs( self ):
        return []
    def get_data_outputs( self ):
        return []
    def update_state( self ):
        pass
    def get_config_form( self ):
        raise TypeError( "Abstract method" )
        
    def check_and_update_state( self ):
        """
        If the state is not in sync with the current implementation of the
        module, try to update. Returns a list of messages to be displayed
        """
        pass
    
    ## ---- Run time ---------------------------------------------------------
    
    def get_runtime_inputs( self ):
        raise TypeError( "Abstract method" )
    def get_runtime_state( self ):
        raise TypeError( "Abstract method" )
    def encode_runtime_state( self, trans, state ):
        raise TypeError( "Abstract method" )
    def decode_runtime_state( self, trans, string ):
        raise TypeError( "Abstract method" )
    def update_runtime_state( self, trans, state, values ):
        raise TypeError( "Abstract method" )
    
    def execute( self, trans, state ):
        raise TypeError( "Abstract method" )

class InputDataModule( WorkflowModule ):
    type = "data_input"
    name = "Input dataset"

    @classmethod
    def new( Class, trans, tool_id=None ):
        module = Class( trans )
        module.state = dict( name="Input Dataset" )
        return module
    @classmethod
    def from_dict( Class, trans, d, secure=True ):
        module = Class( trans )
        state = from_json_string( d["tool_state"] )
        module.state = dict( name=state.get( "name", "Input Dataset" ) )
        return module
    @classmethod
    def from_workflow_step( Class, trans, step ):
        module = Class( trans )
        module.state = dict( name="Input Dataset" )
        if step.tool_inputs and "name" in step.tool_inputs:
            module.state['name'] = step.tool_inputs[ 'name' ]
        return module
    def save_to_step( self, step ):
        step.type = self.type
        step.tool_id = None
        step.tool_inputs = self.state

    def get_data_inputs( self ):
        return []
    def get_data_outputs( self ):
        return [ dict( name='output', extensions=['input'] ) ]
    def get_config_form( self ):
        form = web.FormBuilder( title=self.name ) \
            .add_text( "name", "Name", value=self.state['name'] )
        return self.trans.fill_template( "workflow/editor_generic_form.mako",
                                         module=self, form=form )
    def get_state( self, secure=True ):
        return to_json_string( self.state )
    
    def update_state( self, incoming ):
        self.state['name'] = incoming.get( 'name', 'Input Dataset' )
    
    def get_runtime_inputs( self, filter_set=['data'] ):
        label = self.state.get( "name", "Input Dataset" )
        return dict( input=DataToolParameter( None, Element( "param", name="input", label=label, multiple=True, type="data", format=', '.join(filter_set) ), self.trans ) )
    def get_runtime_state( self ):
        state = DefaultToolState()
        state.inputs = dict( input=None )
        return state
    def encode_runtime_state( self, trans, state ):
        fake_tool = Bunch( inputs = self.get_runtime_inputs() )
        return state.encode( fake_tool, trans.app )
    def decode_runtime_state( self, trans, string ):
        fake_tool = Bunch( inputs = self.get_runtime_inputs() )
        state = DefaultToolState()
        state.decode( string, fake_tool, trans.app )
        return state
    def update_runtime_state( self, trans, state, values ):
        errors = {}
        for name, param in self.get_runtime_inputs().iteritems():
            value, error = check_param( trans, param, values.get( name, None ), values )
            state.inputs[ name ] = value
            if error:
                errors[ name ] = error
        return errors
    
    def execute( self, trans, state ):
        return None, dict( output=state.inputs['input'])
    
class ToolModule( WorkflowModule ):
    
    type = "tool"
    
    def __init__( self, trans, tool_id ):
        self.trans = trans
        self.tool_id = tool_id
        self.tool = trans.app.toolbox.get_tool( tool_id )
        self.post_job_actions = {}
        self.workflow_outputs = []
        self.state = None
        if self.tool:
            self.errors = None
        else:
            self.errors = {}
            self.errors[ tool_id ] = 'Tool unavailable'
    @classmethod
    def new( Class, trans, tool_id=None ):
        module = Class( trans, tool_id )
        module.state = module.tool.new_state( trans, all_pages=True )
        return module
    @classmethod
    def from_dict( Class, trans, d, secure=True ):
        tool_id = d[ 'tool_id' ]
        module = Class( trans, tool_id )
        module.state = DefaultToolState()
        if module.tool is not None:
            module.state.decode( d[ "tool_state" ], module.tool, module.trans.app, secure=secure )
        module.errors = d.get( "tool_errors", None )
        module.post_job_actions = d.get( "post_job_actions", {} )
        module.workflow_outputs = d.get( "workflow_outputs", [] )
        return module
    @classmethod
    def from_workflow_step( Class, trans, step ):
        tool_id = step.tool_id
        if trans.app.toolbox and tool_id not in trans.app.toolbox.tools_by_id:
            # See if we have access to a different version of the tool.
            # TODO: If workflows are ever enhanced to use tool version
            # in addition to tool id, enhance the selection process here
            # to retrieve the correct version of the tool.
            tool_version = Class.__get_tool_version( trans, tool_id )
            if tool_version:
                tool_version_ids = tool_version.get_version_ids( trans.app )
                for tool_version_id in tool_version_ids:
                    if tool_version_id in trans.app.toolbox.tools_by_id:
                        tool_id = tool_version_id
                        break
        if ( trans.app.toolbox and tool_id in trans.app.toolbox.tools_by_id ):
            module = Class( trans, tool_id )
            module.state = DefaultToolState()
            module.state.inputs = module.tool.params_from_strings( step.tool_inputs, trans.app, ignore_errors=True )
            module.errors = step.tool_errors
            # module.post_job_actions = step.post_job_actions
            module.workflow_outputs = step.workflow_outputs
            pjadict = {}
            for pja in step.post_job_actions:
                pjadict[pja.action_type] = pja
            module.post_job_actions = pjadict
            return module
        return None
    @classmethod
    def __get_tool_version( cls, trans, tool_id ):
        # Return a ToolVersion if one exists for tool_id.
        return trans.sa_session.query( trans.app.model.ToolVersion ) \
                               .filter( trans.app.model.ToolVersion.table.c.tool_id == tool_id ) \
                               .first()
    def save_to_step( self, step ):
        step.type = self.type
        step.tool_id = self.tool_id
        if self.tool:
            step.tool_version = self.get_tool_version()
            step.tool_inputs = self.tool.params_to_strings( self.state.inputs, self.trans.app )
        else:
            step.tool_version = None
            step.tool_inputs = None
        step.tool_errors = self.errors
        for k, v in self.post_job_actions.iteritems():
            # Must have action_type, step.  output and a_args are optional.
            if 'output_name' in v:
                output_name = v['output_name']
            else:
                output_name = None
            if 'action_arguments' in v:
                action_arguments = v['action_arguments']
            else:
                action_arguments = None
            n_p = PostJobAction(v['action_type'], step, output_name, action_arguments)
    def get_name( self ):
        if self.tool:
            return self.tool.name
        return 'unavailable'
    def get_tool_id( self ):
        return self.tool_id
    def get_tool_version( self ):
        return self.tool.version
    def get_state( self, secure=True ):
        return self.state.encode( self.tool, self.trans.app, secure=secure )
    def get_errors( self ):
        return self.errors
    def get_tooltip( self ):
        return self.tool.help
    def get_data_inputs( self ):
        data_inputs = []
        def callback( input, value, prefixed_name, prefixed_label ):
            if isinstance( input, DataToolParameter ):
                data_inputs.append( dict(
                    name=prefixed_name,
                    label=prefixed_label,
                    extensions=input.extensions ) )
        visit_input_values( self.tool.inputs, self.state.inputs, callback )
        return data_inputs
    def get_data_outputs( self ):
        data_outputs = []
        data_inputs = None
        for name, tool_output in self.tool.outputs.iteritems():
            if tool_output.format_source != None:
                formats = [ 'input' ] # default to special name "input" which remove restrictions on connections
                if data_inputs == None:
                    data_inputs = self.get_data_inputs()
                # find the input parameter referenced by format_source
                for di in data_inputs:
                    # input names come prefixed with conditional and repeat names separated by '|'
                    # remove prefixes when comparing with format_source
                    if di['name'] != None and di['name'].split('|')[-1] == tool_output.format_source:
                        formats = di['extensions']
            else:
                formats = [ tool_output.format ]
            for change_elem in tool_output.change_format:
                for when_elem in change_elem.findall( 'when' ):
                    format = when_elem.get( 'format', None )
                    if format and format not in formats:
                        formats.append( format )
            data_outputs.append( dict( name=name, extensions=formats ) )
        return data_outputs
    def get_post_job_actions( self ):
        return self.post_job_actions
    def get_config_form( self ):
        self.add_dummy_datasets()
        return self.trans.fill_template( "workflow/editor_tool_form.mako", 
            tool=self.tool, values=self.state.inputs, errors=( self.errors or {} ) )
    def update_state( self, incoming ):       
        # Build a callback that handles setting an input to be required at
        # runtime. We still process all other parameters the user might have
        # set. We also need to make sure all datasets have a dummy value
        # for dependencies to see
        
        self.post_job_actions = ActionBox.handle_incoming(incoming)
        
        make_runtime_key = incoming.get( 'make_runtime', None )
        make_buildtime_key = incoming.get( 'make_buildtime', None )
        def item_callback( trans, key, input, value, error, old_value, context ):
            # Dummy value for Data parameters
            if isinstance( input, DataToolParameter ):
                return DummyDataset(), None
            # Deal with build/runtime (does not apply to Data parameters)
            if key == make_buildtime_key:
                return input.get_initial_value( trans, context ), None
            elif isinstance( old_value, RuntimeValue ):
                return old_value, None
            elif key == make_runtime_key:
                return RuntimeValue(), None
            elif isinstance(value, basestring) and re.search("\$\{.+?\}", str(value)):
                # Workflow Parameter Replacement, so suppress error from going to the workflow level.
                return value, None
            else:
                return value, error
        # Update state using incoming values
        errors = self.tool.update_state( self.trans, self.tool.inputs, self.state.inputs, incoming, item_callback=item_callback )
        self.errors = errors or None
    def check_and_update_state( self ):
        return self.tool.check_and_update_param_values( self.state.inputs, self.trans )
    def add_dummy_datasets( self, connections=None):
        if connections:
            # Store onnections by input name
            input_connections_by_name = \
                dict( ( conn.input_name, conn ) for conn in connections )
        else:
            input_connections_by_name = {}
        # Any connected input needs to have value DummyDataset (these
        # are not persisted so we need to do it every time)
        def callback( input, value, prefixed_name, prefixed_label ):
            if isinstance( input, DataToolParameter ):
                if connections is None or prefixed_name in input_connections_by_name:
                    return DummyDataset()
        visit_input_values( self.tool.inputs, self.state.inputs, callback ) 

class WorkflowModuleFactory( object ):
    def __init__( self, module_types ):
        self.module_types = module_types
    def new( self, trans, type, tool_id=None ):
        """
        Return module for type and (optional) tool_id intialized with
        new / default state.
        """
        assert type in self.module_types
        return self.module_types[type].new( trans, tool_id )
    def from_dict( self, trans, d, **kwargs ):
        """
        Return module initialized from the data in dictionary `d`.
        """
        type = d['type']
        assert type in self.module_types
        return self.module_types[type].from_dict( trans, d, **kwargs )    
    def from_workflow_step( self, trans, step ):
        """
        Return module initializd from the WorkflowStep object `step`.
        """
        type = step.type
        return self.module_types[type].from_workflow_step( trans, step )
    
module_factory = WorkflowModuleFactory( dict( data_input=InputDataModule, tool=ToolModule ) )
