from galaxy.web.base.controller import *

import simplejson

from galaxy.tools.parameters import DataToolParameter
from galaxy.tools import DefaultToolState
from galaxy.tools.parameters.grouping import Repeat, Conditional
from galaxy.datatypes.data import Data
from galaxy.util.odict import odict
from galaxy.util.topsort import topsort, topsort_levels, CycleError

class WorkflowController( BaseController ):
    beta = True
    
    @web.expose
    def index( self, trans ):
        """
        Render workflow main page (management of existing workflows)
        """
        user = trans.get_user()
        if not user:
            return error( "You must be logged in to use <b>Galaxy</b> workflows." )
        workflows = trans.sa_session.query( model.StoredWorkflow ).filter_by( user=user, deleted=False ).all()
        return trans.fill_template( "workflow/index.mako",
                                    workflows = workflows )
    
    @web.expose
    def create( self, trans, workflow_name=None ):
        """
        Create a new stored workflow with name `workflow_name`.
        """
        user = trans.get_user()
        if not user:
            return error( "Must be logged in to create or modify workflows" )
        if not workflow_name:
            return error( "Must provide a name for the new workflow" )
        # Create the new stored workflow
        stored_workflow = model.StoredWorkflow()
        stored_workflow.name = workflow_name
        stored_workflow.user = user
        # And the first (empty) workflow revision
        workflow = model.Workflow()
        workflow.name = workflow_name
        workflow.stored_workflow = stored_workflow
        stored_workflow.latest_workflow = workflow
        # Persist
        session = trans.sa_session
        session.save( stored_workflow )
        session.flush()
        # Display the management page
        return self.index( trans )
    
    @web.expose
    def delete( self, trans, id=None ):
        """
        Mark a workflow as deleted
        """        
        # Load workflow from database
        stored = get_stored_workflow( trans, id )
        # Marke as deleted and save
        stored.deleted = True
        stored.flush()
        # Display the management page
        return self.index( trans )
        
        
    @web.expose
    def editor( self, trans, id=None ):
        """
        Render the main workflow editor interface. The canvas is embedded as
        an iframe (neccesary for scrolling to work properly), which is
        rendered by `editor_canvas`.
        """
        if not id:
            return trans.show_error_message( "Invalid workflow id" )
        id = trans.security.decode_id( id )
        user = trans.get_user()
        if not user:
            return trans.show_error_message( "Must be logged in to create or modify workflows" )
        return trans.fill_template( "workflow/editor.mako",
                                    workflow_id=id )
        
    @web.json
    def editor_tool_form( self, trans, tool_id=None, **incoming ):
        """
        Accepts a tool state and incoming values, and generates a new tool
        form and some additional information, packed into a json dictionary.
        This is used for the form shown in the right pane when a node
        is selected.
        """
        trans.workflow_building_mode = True
        tool = trans.app.toolbox.tools_by_id[tool_id]
        state = DefaultToolState()
        state.decode( incoming.pop("tool_state"), tool, trans.app )
        errors = tool.update_state( trans, tool.inputs, state.inputs, incoming )
        rval = {}
        rval['form_html'] = trans.fill_template( "workflow/editor_tool_form.mako", 
            tool=tool, as_html=as_html, values=state.inputs, errors=errors )
        if errors:
            rval['tool_errors'] = errors
        else:
            rval['tool_errors'] = None
        # Updated data_inputs
        rval['data_inputs'] = get_data_inputs( tool.inputs, state.inputs )
        rval['state'] = state.encode( tool, trans.app )
        return rval
        
    @web.json
    def get_tool_info( self, trans, tool_id ):
        """
        Generate a json dictionary containing info about the tool specified by
        `tool_id`. Info includes data inputs and outputs, html representation
        of the initial form, and the initial tool state (with default values).
        This is called asynchronously whenever a new node is added.
        """
        trans.workflow_building_mode = True
        tool = trans.app.toolbox.tools_by_id[tool_id]
        rval = {}
        rval['name'] = tool.name
        rval['tool_id'] = tool.id
        data_outputs = []
        for name, ( format, metadata_source, parent ) in tool.outputs.iteritems():
            data_outputs.append( dict( name=name, extension=format ) )
        rval['data_outputs'] = data_outputs
        state = tool.new_state( trans, all_pages=True )
        rval['form_html'] = trans.fill_template( "workflow/editor_tool_form.mako", 
            tool=tool, as_html=as_html, values=state.inputs, errors={} )
        rval['tool_state'] = state.encode( tool, trans.app )
        rval['data_inputs'] = get_data_inputs( tool.inputs, state.inputs )
        return rval
                
    @web.json
    def load_workflow( self, trans, id ):
        """
        Get the latest Workflow for the StoredWorkflow identified by `id` and
        encode it as a json string that can be read by the workflow editor
        web interface.
        """
        user = trans.get_user()
        id = trans.security.decode_id( id )
        trans.workflow_building_mode = True
        # Load encoded workflow from database
        stored = trans.sa_session.query( model.StoredWorkflow ).get( id )
        assert stored.user == user
        workflow = stored.latest_workflow
        # Pack workflow data into a dictionary and return
        data = {}
        data['name'] = workflow.name
        data['steps'] = {}
        # For each step, rebuild the form and encode the state
        for step in workflow.steps:
            step_dict = {}
            step_dict['id'] = step.order_index
            step_dict['tool_id'] = tool_id = step.tool_id
            # Load tool
            tool = trans.app.toolbox.tools_by_id[tool_id]
            # Build a state from the tool_inputs dict
            state = DefaultToolState()
            state.inputs = tool.params_from_strings( step.tool_inputs, trans.app, ignore_errors=True )
            step_dict['tool_state'] = state.encode( tool, trans.app )
            # Error messages for the tool
            step_dict['tool_errors'] = ( step.tool_errors or None )
            # Connections
            input_conn_dict = {}
            for conn in step.input_connections:
                input_conn_dict[ conn.input_name ] = dict( id=conn.output_step.order_index,
                                                           output_name=conn.output_name )
            step_dict['input_connections'] = input_conn_dict
            # Position
            step_dict['position'] = step.position
            # Input and output specs
            step_dict['data_inputs'] = get_data_inputs( tool.inputs, state.inputs )
            data_outputs = []
            for name, ( format, metadata_source, parent ) in tool.outputs.iteritems():
                data_outputs.append( dict( name=name, extension=format ) )
            step_dict['data_outputs'] = data_outputs
            # Build the tool form html
            errors = step.tool_errors
            step_dict['form_html'] = trans.fill_template( "workflow/editor_tool_form.mako", 
                tool=tool, as_html=as_html, values=state.inputs, errors=( step.tool_errors or {} ) )
            step_dict['name'] = tool.name
            data['steps'][step.order_index] = step_dict
        return data

    @web.json
    def save_workflow( self, trans, id, workflow_data ):
        """
        Save the workflow described by `workflow_data` with id `id`.
        """
        # Get the stored workflow
        stored = get_stored_workflow( trans, id )
        # Put parameters in workflow mode
        trans.workflow_building_mode = True
        # Convert incoming workflow data from json
        data = simplejson.loads( workflow_data )
        # Create new workflow from incoming data
        workflow = model.Workflow()
        # Just keep the last name (user can rename later)
        workflow.name = stored.name
        # Assume no errors until we find a step that has some
        workflow.has_errors = False
        # Create each step
        steps = []
        # The editor will provide ids for each step that we don't need to save,
        # but do need to use to make connections
        steps_by_external_id = {}
        # First pass to build step objects and populate basic values
        for key, step_dict in data['steps'].iteritems():
            # Decode the tool state from the step dict
            tool = trans.app.toolbox.tools_by_id[ step_dict['tool_id'] ]
            state = DefaultToolState()
            state.decode( step_dict['tool_state'], tool, trans.app )
            # Convert back to strings for database
            tool_inputs = tool.params_to_strings( state.inputs, trans.app )
            # Create the model class for the step
            step = model.WorkflowStep()
            steps.append( step )
            steps_by_external_id[ step_dict['id' ] ] = step
            step.tool_id = step_dict['tool_id']
            step.tool_inputs = tool_inputs
            step.tool_errors = step_dict['tool_errors']
            if step.tool_errors:
                workflow.has_errors = True
            step.position = step_dict['position']
            # Stick this in the step temporarily
            step.temp_input_connections = step_dict['input_connections']
        # Second pass to deal with connections between steps
        for step in steps:
            # Input connections
            for input_name, conn_dict in step.temp_input_connections.iteritems():
                if conn_dict:
                    conn = model.WorkflowStepConnection()
                    conn.input_step = step
                    conn.input_name = input_name
                    conn.output_name = conn_dict['output_name']
                    conn.output_step = steps_by_external_id[ conn_dict['id'] ]
            del step.temp_input_connections
        # Order the steps if possible
        attach_ordered_steps( workflow, steps )
        # Connect up
        workflow.stored_workflow = stored
        stored.latest_workflow = workflow
        # Persist
        trans.sa_session.save( stored )
        trans.sa_session.flush()
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
        rval['name'] = workflow.name
        return rval

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
        history = trans.get_history()
        if not user:
            return trans.show_error_message( "Must be logged in to create workflows" )
        if job_ids is None or workflow_name is None:
            jobs, warnings = get_job_dict( trans )
            # Render
            return trans.fill_template(
                        "workflow/build_from_current_history.mako", 
                        jobs=jobs,
                        warnings=warnings,
                        history=history )
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
            job_id_to_step_index = dict( ( job_id, i ) for ( i, job_id ) in enumerate( job_ids ) )
            # Back-translate each job
            jobs_by_id = dict( ( job.id, job ) for job in jobs.keys() )
            steps = []
            for job_id in job_ids:
                assert job_id in jobs_by_id, "Attempt to create workflow with job not connected to current history"
                job = jobs_by_id[ job_id ]
                tool = trans.app.toolbox.tools_by_id[ job.tool_id ]
                param_values = job.get_param_values( trans.app )
                associations = cleanup_param_values( tool.inputs, param_values )
                step = model.WorkflowStep()
                step.tool_id = job.tool_id
                step.tool_inputs = tool.params_to_strings( param_values, trans.app )
                # NOTE: We shouldn't need to do two passes here since only
                #       an earlier job can be used as an input to a later
                #       job.
                for other_hid, input_name in associations:
                    if other_hid in hid_to_output_pair:
                        other_job_id, other_name = hid_to_output_pair[ other_hid ]
                        # Only create association if the associated output dataset
                        # is being included in this workflow
                        if other_job_id in job_id_to_step_index:
                            conn = model.WorkflowStepConnection()
                            conn.input_step = step
                            conn.input_name = input_name
                            # Should always be connected to an earlier step
                            conn.output_step = steps[ job_id_to_step_index[ other_job_id ] ]
                            conn.output_name = other_name                   
                steps.append( step )
            # Workflow to populate
            workflow = model.Workflow()
            workflow.name = workflow_name
            # Order the steps if possible
            attach_ordered_steps( workflow, steps )
            # And let's try to set up some reasonable locations on the canvas
            # (these are pretty arbitrary values)
            levorder = order_workflow_steps_with_levels( steps )
            base_pos = 2510
            for i, steps_at_level in enumerate( levorder ):
                for j, index in enumerate( steps_at_level ):
                    step = steps[ index ]
                    step.position = dict( top = ( base_pos + 120 * j ),
                                          left = ( base_pos + 220 * i ) )
            # Store it
            stored = model.StoredWorkflow()
            stored.user = user
            stored.name = workflow_name
            workflow.stored_workflow = stored
            stored.latest_workflow = workflow
            trans.sa_session.save( stored )
            trans.sa_session.flush()
            # Index page with message
            trans.template_context['message'] = "Workflow '%s' created" % workflow_name
            return self.index( trans )
            ## return trans.show_ok_message( "<p>Workflow '%s' created.</p><p><a target='_top' href='%s'>Click to load in workflow editor</a></p>"
            ##     % ( workflow_name, web.url_for( action='editor', id=trans.security.encode_id(stored.id) ) ) )       
        
    @web.expose
    def run( self, trans, id, **kwargs ):
        stored = get_stored_workflow( trans, id )
        # Get the latest revision
        workflow = stored.latest_workflow
        # It is possible for a workflow to have 0 steps
        if len( workflow.steps ) == 0:
            return trans.show_error_message(
                "Workflow cannot be run because it does not have any steps" )
        #workflow = Workflow.from_simple( simplejson.loads( stored.encoded_value ), trans.app )
        if workflow.has_cycles:
            return trans.show_error_message(
                "Workflow cannot be run because it contains cycles" )
        if workflow.has_errors:
            return trans.show_error_message(
                "Workflow cannot be run because of validation errors in some steps" )
        # Build the state for each step
        errors = {}
        if kwargs:
            # If kwargs were provided, the states for each step should have
            # been POSTed
            for step in workflow.steps:
                # Extract just the arguments for this step by prefix
                p = "%s|" % step.id
                l = len(p)
                step_args = dict( ( k[l:], v ) for ( k, v ) in kwargs.iteritems() if k.startswith( p ) )
                # Get the tool
                tool = trans.app.toolbox.tools_by_id[ step.tool_id ]
                # Get the state
                state = DefaultToolState()
                state.decode( step_args.pop("tool_state"), tool, trans.app )
                step.state = state
                # Connections by input name
                step.input_connections_by_name = dict( ( conn.input_name, conn ) for conn in step.input_connections )
                # Get old errors
                old_errors = state.inputs.pop( "__errors__", {} )
                # Update the state
                step_errors = tool.update_state( trans, tool.inputs, step.state.inputs, step_args,
                                                 update_only=True, old_errors=old_errors )
                if step_errors:
                    errors[step.id] = state.inputs["__errors__"] = step_errors
            if not errors:
                # Run each step, connecting outputs to inputs
                outputs = {}
                for step in workflow.steps:
                    tool = trans.app.toolbox.tools_by_id[ step.tool_id ]
                    inputs = step.state.inputs
                    # Connect up 
                    for conn in step.input_connections:
                        inputs[ conn.input_name ] = outputs[ conn.output_step.id ][ conn.output_name ]                    
                    outputs[ step.id ] = tool.execute( trans, step.state.inputs )
                return trans.fill_template( "workflow/run_complete.mako",
                                            workflow=stored,
                                            outputs=outputs )
        else:
            for step in workflow.steps:
                # Build a new tool state for the step
                tool = trans.app.toolbox.tools_by_id[ step.tool_id ]
                state = DefaultToolState()
                state.inputs = tool.params_from_strings( step.tool_inputs, trans.app )
                # Store state with the step
                step.state = state
                # Connections by input name
                step.input_connections_by_name = dict( ( conn.input_name, conn ) for conn in step.input_connections )
                # This should never actually happen since we don't allow
                # running workflows with errors (yet?)
                if step.tool_errors:
                    errors[step.id] = step.tool_errors
        # Render the form
        return trans.fill_template(
                    "workflow/run.mako", 
                    steps=workflow.steps,
                    workflow=stored,
                    errors=errors )
        
## ---- Utility methods -------------------------------------------------------
        
def get_stored_workflow( trans, id ):
    """
    Get a StoredWorkflow from the database by id, verifying ownership. 
    """
    # Load workflow from database
    id = trans.security.decode_id( id )
    stored = trans.sa_session.query( model.StoredWorkflow ).get( id )
    if not stored:
        error( "Workflow not found" )
    # Verify ownership
    user = trans.get_user()
    if not user:
        error( "Must be logged in to use workflows" )
    if not( stored.user == user ):
        error( "Workflow is not owned by current user" )
    # Looks good
    return stored
        
def as_html( param, value, trans, prefix ):
    if type( param ) is DataToolParameter:
        return "Data input '" + param.name + "' (" + ( " or ".join( param.extensions ) ) + ")"
    else:
        return param.get_html_field( trans, value ).get_html( prefix )

def attach_ordered_steps( workflow, steps ):
    ordered_steps = order_workflow_steps( steps )
    if ordered_steps:
        workflow.has_cycles = False
        for i, step in enumerate( ordered_steps ):
            step.order_index = i
            workflow.steps.append( step )
    else:
        workflow.has_cycles = True
        workflow.steps = steps

def edgelist_for_workflow_steps( steps ):
    """
    Create a list of tuples representing edges between `WorkflowSteps` based
    on associated `WorkflowStepConnection`s
    """
    edges = []
    steps_to_index = dict( ( step, i ) for i, step in enumerate( steps ) )
    for step in steps:
        edges.append( ( steps_to_index[step], steps_to_index[step] ) )
        for conn in step.input_connections:
            edges.append( ( steps_to_index[conn.output_step], steps_to_index[conn.input_step] ) )
    return edges

def order_workflow_steps( steps ):
    """
    Perform topological sort of the steps, return ordered or None
    """
    try:
        edges = edgelist_for_workflow_steps( steps )
        node_order = topsort( edges )
        return [ steps[i] for i in node_order ]
    except CycleError:
        return None
    
def order_workflow_steps_with_levels( steps ):
    try:
        return topsort_levels( edgelist_for_workflow_steps( steps ) )
    except CycleError:
        return None
    
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
                # if not( prefix ):
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
                for i, rep_values in enumerate( group_values ):
                    rep_index = rep_values['__index__']
                    prefix = "%s_%d|" % ( key, rep_index )
                    cleanup( prefix, input.inputs, group_values[i] )
            elif isinstance( input, Conditional ):
                group_values = values[input.name]
                current_case = group_values['__current_case__']
                prefix = "%s|" % ( key )
                cleanup( prefix, input.cases[current_case].inputs, group_values )
    cleanup( "", inputs, values )
    return associations

def get_data_inputs( inputs, input_values ):
    """
    For a set of input definitions and a tool state, find all of the dataset
    inputs
    """
    data_inputs = []
    def visitor( inputs, input_values, name_prefix, label_prefix ):
        for input in inputs.itervalues():
            if isinstance( input, Repeat ):  
                for i, d in enumerate( input_values[ input.name ] ):
                    index = d['__index__']
                    new_name_prefix = name_prefix + "%s_%d|" % ( input.name, index )
                    new_label_prefix = label_prefix + "%s %d > " % ( input.title, i + 1 )
                    visitor( input.inputs, d, new_name_prefix, new_label_prefix )
            elif isinstance( input, Conditional ):
                values = input_values[ input.name ]
                current = values["__current_case__"]
                label_prefix = label_prefix
                name_prefix = name_prefix + "|" + input.name
                visitor( input.cases[current].inputs, values, name_prefix, label_prefix )
            else:
                if isinstance( input, DataToolParameter ):
                    data_inputs.append( dict( name=name_prefix+input.name, label=label_prefix+input.label, extensions=input.extensions ) )
    visitor( inputs, input_values, "", "" )
    return data_inputs
    
    
