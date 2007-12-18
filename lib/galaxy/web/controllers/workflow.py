from galaxy.web.base.controller import *

import simplejson

from galaxy.tools.parameters import DataToolParameter
from galaxy.tools import DefaultToolState
from galaxy.tools.grouping import Repeat, Conditional
from galaxy.datatypes.data import Data
from galaxy.workflow import Workflow, WorkflowStep
from galaxy.util.odict import odict

class WorkflowController( BaseController ):
    beta = True
    
    @web.expose
    def editor( self, trans, workflow_name=None ):
        user = trans.get_user()
        if not user:
            return trans.show_error_message( "Must be logged in to create or modify workflows" )
        return trans.fill_template( "workflow/editor.mako",
                                    workflow_name=workflow_name )
    
    @web.expose
    def editor_canvas( self, trans ):
        return trans.fill_template( "workflow/editor_canvas.mako" )
        
    @web.json
    def editor_tool_form( self, trans, tool_id=None, **incoming ):
        trans.workflow_building_mode = True
        tool = trans.app.toolbox.tools_by_id[tool_id]
        state = DefaultToolState()
        state.decode( incoming.pop("tool_state"), tool, trans.app )
        errors = tool.update_state( trans, tool.inputs, state.inputs, incoming )
        rval = {}
        rval['form_html'] = trans.fill_template( "workflow/editor_tool_form.mako", 
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
        rval['form_html'] = trans.fill_template( "workflow/editor_tool_form.mako", 
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
        workflow.order_nodes()
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
            step['form_html'] = trans.fill_template( "workflow/editor_tool_form.mako", 
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
    
    @web.expose
    def build_from_current_history( self, trans, job_ids=None, workflow_name=None ):
        user = trans.get_user()
        if not user:
            return trans.show_error_message( "Must be logged in to create workflows" )
        if job_ids is None or workflow_name is None:
            jobs, warnings = get_job_dict( trans )
            # Render
            return trans.fill_template(
                        "workflow/build_from_current_history.mako", 
                        jobs=jobs,
                        warnings=warnings )
        else:
            # Ensure job_ids is a list
            if type( job_ids ) == str:
                job_ids = [ job_ids ]
            job_ids = [ int( id ) for id in job_ids ]
            # Find each job, for security we (implicately) check that they are
            # associated witha job in the current history. 
            jobs, warnings = get_job_dict( trans )
            # Create a mapping from hid to ( job_id, output_name )
            hid_to_output_pair = {}
            for job, datasets in jobs.iteritems():
                for assoc_name, data in datasets:
                    hid_to_output_pair[ data.hid ] = ( job.id, assoc_name )
            # Mapping from job ids to workflow step ids (0, 1, 2, ...)
            job_id_to_step_id = dict( ( job_id, i ) for ( i, job_id ) in enumerate( job_ids ) )
            # Workflow to populate
            workflow = Workflow()
            # Back-translate each job
            jobs_by_id = dict( ( job.id, job ) for job in jobs.keys() )
            for step_id, job_id in enumerate( job_ids ):
                assert job_id in jobs_by_id, "Attempt to create workflow with job not connected to current history"
                job = jobs_by_id[ job_id ]
                tool = trans.app.toolbox.tools_by_id[ job.tool_id ]
                param_values = job.get_param_values( trans.app )
                associations = cleanup_param_values( tool.inputs, param_values )
                step = WorkflowStep()
                step.id = step_id
                step.tool_id = job.tool_id
                step.tool_inputs = param_values
                for other_hid, input_name in associations:
                    other_job_id, other_name = hid_to_output_pair[ other_hid ]
                    # Only create association if the associated output dataset
                    # is being included in this workflow
                    if other_job_id in job_id_to_step_id:
                        step.input_connections[input_name] = ( job_id_to_step_id[ other_job_id ], other_name )
                    else:
                        step.input_connections[input_name] = None
                workflow.steps[ step_id ] = step
            # Try to order the nodes
            workflow.order_nodes()
            # And let's try to set up some reasonable locations
            levorder = workflow.order_nodes_levels()
            base_pos = 2510
            for i, steps_at_level in enumerate( levorder ):
                for j, step_id in enumerate( steps_at_level ):
                    step = workflow.steps[step_id]
                    step.position = dict( top = ( base_pos + 120 * j ),
                                          left = ( base_pos + 220 * i ) )
            # Store it
            stored = model.StoredWorkflow.get_by( user = user, name = workflow_name )
            if stored is None:
                stored = model.StoredWorkflow()
                stored.user = user
                stored.name = workflow_name
            stored.encoded_value = simplejson.dumps( workflow.to_simple() )
            stored.flush()
            # 
            return trans.show_ok_message( "Workflow '%s' created.<br/><a target='_top' href='%s'>Click to load in workflow editor</a>"
                % ( workflow_name, web.url_for( action='editor', workflow_name=workflow_name ) ) )       
        
    @web.expose
    def run( self, trans, workflow_name ):
        user = trans.get_user()
        trans.workflow_building_mode = True
        # Load encoded workflow from database
        stored = model.StoredWorkflow.get_by( user = user, name = workflow_name )
        workflow = Workflow.from_simple( simplejson.loads( stored.encoded_value ) )
        if workflow.has_cycles:
            return trans.show_error_message(
                "Workflow cannot be run because it contains cycles" )
        if workflow.has_errors:
            return trans.show_error_message(
                "Workflow cannot be run because of validation errors is some steps" )
        rval = ""
        for step_id in workflow.node_order:
            step = workflow.steps[step]
            for input_name, assoc in step.input_associations.iteritems():
                if assoc is None:
                    rval += str( step.tool_id + " " + input_name + "\n" )
        return rval
            
        
## ---- Utility methods -------------------------------------------------------
        
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
    
def get_job_dict( trans ):
    """
    Return a dictionary of Job -> [ Dataset ] mappings, for all finished
    active Datasets in the current history and the jobs that created them.
    """
    history = trans.get_history()
    # Get the jobs that created the datasets
    warnings = set()
    jobs = odict()
    for dataset in history.active_datasets:
        # FIXME: Create "Dataset.is_finished"
        if dataset.state in ( 'new', 'running', 'queued' ):
            warnings.add( "Some datasets still queued or running were ignored" )
            continue
        for assoc in dataset.creating_job_associations:
            job = assoc.job
            if job in jobs:
                jobs[ job ].append( ( assoc.name, dataset ) )
            else:
                jobs[ job ] = [ ( assoc.name, dataset ) ]
    return jobs, warnings    

def cleanup_param_values( inputs, values ):
    """
    Remove 'Data' values from `param_values`, along with metadata cruft,
    but track the associations.
    """
    associations = []
    names_to_clean = []
    # dbkey is pushed in by the framework
    if 'dbkey' in values:
        del values['dbkey']
    root_values = values
    # Cleanup all data inputs
    def cleanup( prefix, inputs, values ):
        for key, input in inputs.items():
            if isinstance( input, DataToolParameter ):
                tmp = values[key]
                values[key] = None
                # HACK: Nested associations are not yet working, but we
                #       still need to clean them up so we can serialize
                if not( prefix ):
                    associations.append( ( tmp.hid, prefix + key ) )
                # Cleanup the other deprecated crap associated with datasets
                # as well. Worse, for nested datasets all the metadata is
                # being pushed into the root. FIXME: MUST REMOVE SOON
                key = prefix + key + "_"
                for k in root_values.keys():
                    if k.startswith( key ):
                        del root_values[k]            
            elif isinstance( input, Repeat ):
                group_values = values[key]
                for i in range( len( group_values ) ):
                    prefix = "%s_%d|" % ( key, i )
                    cleanup( prefix, input.inputs, group_values[i] )
            elif isinstance( input, Conditional ):
                group_values = values[input.name]
                current_case = group_values['__current_case__']
                prefix = "%s|" % ( key )
                cleanup( prefix, input.cases[current_case].inputs, group_values )
    cleanup( "", inputs, values )
    return associations