from galaxy.web.base.controller import *

import pkg_resources
pkg_resources.require( "simplejson" )
import simplejson

from galaxy.tools.parameters import *
from galaxy.tools import DefaultToolState
from galaxy.tools.parameters.grouping import Repeat, Conditional
from galaxy.datatypes.data import Data
from galaxy.util.odict import odict
from galaxy.util.bunch import Bunch
from galaxy.util.topsort import topsort, topsort_levels, CycleError
from galaxy.workflow.modules import *
from galaxy.model.mapping import desc
from galaxy.model.orm import *

class WorkflowController( BaseController ):
    
    @web.expose
    def index( self, trans ):
        return trans.fill_template( "workflow/index.mako" )
                                   
    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def list( self, trans ):
        """
        Render workflow main page (management of existing workflows)
        """
        user = trans.get_user()
        workflows = trans.sa_session.query( model.StoredWorkflow ) \
            .filter_by( user=user, deleted=False ) \
            .order_by( desc( model.StoredWorkflow.table.c.update_time ) ) \
            .all()
        shared_by_others = trans.sa_session \
            .query( model.StoredWorkflowUserShareAssociation ) \
            .filter_by( user=user ) \
            .join( 'stored_workflow' ) \
            .filter( model.StoredWorkflow.deleted == False ) \
            .order_by( desc( model.StoredWorkflow.update_time ) ) \
            .all()
        return trans.fill_template( "workflow/list.mako",
                                    workflows = workflows,
                                    shared_by_others = shared_by_others )
    
    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def list_for_run( self, trans ):
        """
        Render workflow list for analysis view (just allows running workflow
        or switching to management view)
        """
        user = trans.get_user()
        workflows = trans.sa_session.query( model.StoredWorkflow ) \
            .filter_by( user=user, deleted=False ) \
            .order_by( desc( model.StoredWorkflow.table.c.update_time ) ) \
            .all()
        shared_by_others = trans.sa_session \
            .query( model.StoredWorkflowUserShareAssociation ) \
            .filter_by( user=user ) \
            .filter( model.StoredWorkflow.deleted == False ) \
            .order_by( desc( model.StoredWorkflow.table.c.update_time ) ) \
            .all()
        return trans.fill_template( "workflow/list_for_run.mako",
                                    workflows = workflows,
                                    shared_by_others = shared_by_others )
    
    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def share( self, trans, id, email="" ):
        msg = mtype = None
        # Load workflow from database
        stored = get_stored_workflow( trans, id )
        if email:
            other = trans.sa_session.query( model.User ) \
                                    .filter( and_( model.User.table.c.email==email,
                                                   model.User.table.c.deleted==False ) ) \
                                    .first()
            if not other:
                mtype = "error"
                msg = ( "User '%s' does not exist" % email )
            elif other == trans.get_user():
                mtype = "error"
                msg = ( "You cannot share a workflow with yourself" )
            elif trans.sa_session.query( model.StoredWorkflowUserShareAssociation ) \
                    .filter_by( user=other, stored_workflow=stored ).count() > 0:
                mtype = "error"
                msg = ( "Workflow already shared with '%s'" % email )
            else:
                share = model.StoredWorkflowUserShareAssociation()
                share.stored_workflow = stored
                share.user = other
                session = trans.sa_session
                session.add( share )
                session.flush()
                trans.set_message( "Workflow '%s' shared with user '%s'" % ( stored.name, other.email ) )
                return trans.response.send_redirect( url_for( controller='workflow', action='sharing', id=id ) )
        return trans.fill_template( "workflow/share.mako",
                                    message = msg,
                                    messagetype = mtype,
                                    stored=stored,
                                    email=email )
    
    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def sharing( self, trans, id, **kwargs ):
        session = trans.sa_session
        stored = get_stored_workflow( trans, id )
        if 'enable_import_via_link' in kwargs:
            stored.importable = True
            stored.flush()
        elif 'disable_import_via_link' in kwargs:
            stored.importable = False
            stored.flush()
        elif 'unshare_user' in kwargs:
            user = session.query( model.User ).get( trans.security.decode_id( kwargs['unshare_user' ] ) )
            if not user:
                error( "User not found for provided id" )
            association = session.query( model.StoredWorkflowUserShareAssociation ) \
                                 .filter_by( user=user, stored_workflow=stored ).one()
            session.delete( association )
            session.flush()
        return trans.fill_template( "workflow/sharing.mako",
                                    stored=stored )
        
    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def imp( self, trans, id, **kwargs ):
        session = trans.sa_session
        stored = get_stored_workflow( trans, id, check_ownership=False )
        if stored.importable == False:
            error( "The owner of this workflow has disabled imports via this link" )
        elif stored.user == trans.user:
            error( "You are already the owner of this workflow, can't import" )
        elif stored.deleted:
            error( "This workflow has been deleted, can't import" )
        elif session.query( model.StoredWorkflowUserShareAssociation ) \
                    .filter_by( user=trans.user, stored_workflow=stored ).count() > 0:
            error( "This workflow is already shared with you" )
        else:
            share = model.StoredWorkflowUserShareAssociation()
            share.stored_workflow = stored
            share.user = trans.user
            session = trans.sa_session
            session.add( share )
            session.flush()
            # Redirect to load galaxy frames.
            return trans.response.send_redirect( url_for( controller='workflow' ) )
    
    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def rename( self, trans, id, new_name=None ):
        stored = get_stored_workflow( trans, id )
        if new_name is not None:
            stored.name = new_name
            trans.sa_session.flush()
            trans.set_message( "Workflow renamed to '%s'." % new_name )
            return self.list( trans )
        else:
            return form( url_for( id=trans.security.encode_id(stored.id) ), "Rename workflow", submit_text="Rename" ) \
                .add_text( "new_name", "Workflow Name", value=stored.name )
    
    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def clone( self, trans, id ):
        stored = get_stored_workflow( trans, id, check_ownership=False )
        user = trans.get_user()
        if stored.user == user:
            owner = True
        else:
            if trans.sa_session.query( model.StoredWorkflowUserShareAssociation ) \
                    .filter_by( user=user, stored_workflow=stored ).count() == 0:
                error( "Workflow is not owned by or shared with current user" )
            owner = False
        new_stored = model.StoredWorkflow()
        new_stored.name = "Clone of '%s'" % stored.name
        new_stored.latest_workflow = stored.latest_workflow
        if not owner:
            new_stored.name += " shared by '%s'" % stored.user.email
        new_stored.user = user
        # Persist
        session = trans.sa_session
        session.add( new_stored )
        session.flush()
        # Display the management page
        trans.set_message( 'Clone created with name "%s"' % new_stored.name )
        return self.list( trans )
    
    @web.expose
    @web.require_login( "create workflows" )
    def create( self, trans, workflow_name=None ):
        """
        Create a new stored workflow with name `workflow_name`.
        """
        user = trans.get_user()
        if workflow_name is not None:
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
            session.add( stored_workflow )
            session.flush()
            # Display the management page
            trans.set_message( "Workflow '%s' created" % stored_workflow.name )
            return self.list( trans )
        else:
            return form( url_for(), "Create new workflow", submit_text="Create" ) \
                .add_text( "workflow_name", "Workflow Name", value="Unnamed workflow" )
    
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
        trans.set_message( "Workflow '%s' deleted" % stored.name )
        return self.list( trans )
        
    @web.expose
    @web.require_login( "edit workflows" )
    def editor( self, trans, id=None ):
        """
        Render the main workflow editor interface. The canvas is embedded as
        an iframe (neccesary for scrolling to work properly), which is
        rendered by `editor_canvas`.
        """
        if not id:
            error( "Invalid workflow id" )
        id = trans.security.decode_id( id )
        return trans.fill_template( "workflow/editor.mako", workflow_id=id )
        
    @web.json
    def editor_form_post( self, trans, type='tool', tool_id=None, **incoming ):
        """
        Accepts a tool state and incoming values, and generates a new tool
        form and some additional information, packed into a json dictionary.
        This is used for the form shown in the right pane when a node
        is selected.
        """
        trans.workflow_building_mode = True
        module = module_factory.from_dict( trans, {
            'type': type,
            'tool_id': tool_id,
            'tool_state': incoming.pop("tool_state")
        } )
        module.update_state( incoming )
        return {
            'tool_state': module.get_state(),
            'data_inputs': module.get_data_inputs(),
            'data_outputs': module.get_data_outputs(),
            'tool_errors': module.get_errors(),
            'form_html': module.get_config_form()
        }
        
    @web.json
    def get_new_module_info( self, trans, type, **kwargs ):
        """
        Get the info for a new instance of a module initialized with default
        paramters (any keyword arguments will be passed along to the module).
        Result includes data inputs and outputs, html representation
        of the initial form, and the initial tool state (with default values).
        This is called asynchronously whenever a new node is added.
        """
        trans.workflow_building_mode = True
        module = module_factory.new( trans, type, **kwargs )
        return {
            'type': module.type,
            'name':  module.get_name(),
            'tool_id': module.get_tool_id(),
            'tool_state': module.get_state(),
            'data_inputs': module.get_data_inputs(),
            'data_outputs': module.get_data_outputs(),
            'form_html': module.get_config_form()
        }
                
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
        data['upgrade_messages'] = {}
        # For each step, rebuild the form and encode the state
        for step in workflow.steps:
            # Load from database representation
            module = module_factory.from_workflow_step( trans, step )
            # Fix any missing parameters
            upgrade_message = module.check_and_update_state()
            if upgrade_message:
                data['upgrade_messages'][step.order_index] = upgrade_message
            # Pack atrributes into plain dictionary
            step_dict = {
                'id': step.order_index,
                'type': module.type,
                'tool_id': module.get_tool_id(),
                'name': module.get_name(),
                'tool_state': module.get_state(),
                'tool_errors': module.get_errors(),
                'data_inputs': module.get_data_inputs(),
                'data_outputs': module.get_data_outputs(),
                'form_html': module.get_config_form(),
            }
            # Connections
            input_conn_dict = {}
            for conn in step.input_connections:
                input_conn_dict[ conn.input_name ] = \
                    dict( id=conn.output_step.order_index, output_name=conn.output_name )
            step_dict['input_connections'] = input_conn_dict
            # Position
            step_dict['position'] = step.position
            # Add to return value
            data['steps'][step.order_index] = step_dict
        print data['upgrade_messages']
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
            # Create the model class for the step
            step = model.WorkflowStep()
            steps.append( step )
            steps_by_external_id[ step_dict['id' ] ] = step
            # FIXME: Position should be handled inside module
            step.position = step_dict['position']
            module = module_factory.from_dict( trans, step_dict )
            module.save_to_step( step )
            if step.tool_errors:
                workflow.has_errors = True
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
    def build_from_current_history( self, trans, job_ids=None, dataset_ids=None, workflow_name=None ):
        user = trans.get_user()
        history = trans.get_history()
        if not user:
            return trans.show_error_message( "Must be logged in to create workflows" )
        if ( job_ids is None and dataset_ids is None ) or workflow_name is None:
            jobs, warnings = get_job_dict( trans )
            # Render
            return trans.fill_template(
                        "workflow/build_from_current_history.mako", 
                        jobs=jobs,
                        warnings=warnings,
                        history=history )
        else:
            # Ensure job_ids and dataset_ids are lists (possibly empty)
            if job_ids is None:
                job_ids = []
            elif type( job_ids ) is not list:
                job_ids = [ job_ids ]
            if dataset_ids is None:
                dataset_ids = []
            elif type( dataset_ids ) is not list:
                dataset_ids = [ dataset_ids ]
            # Convert both sets of ids to integers
            job_ids = [ int( id ) for id in job_ids ]
            dataset_ids = [ int( id ) for id in dataset_ids ]
            # Find each job, for security we (implicately) check that they are
            # associated witha job in the current history. 
            jobs, warnings = get_job_dict( trans )
            jobs_by_id = dict( ( job.id, job ) for job in jobs.keys() )
            steps = []
            steps_by_job_id = {}
            hid_to_output_pair = {}
            # Input dataset steps
            for hid in dataset_ids:
                step = model.WorkflowStep()
                step.type = 'data_input'
                hid_to_output_pair[ hid ] = ( step, 'output' )
                steps.append( step )
            # Tool steps
            for job_id in job_ids:
                assert job_id in jobs_by_id, "Attempt to create workflow with job not connected to current history"
                job = jobs_by_id[ job_id ]
                tool = trans.app.toolbox.tools_by_id[ job.tool_id ]
                param_values = job.get_param_values( trans.app )
                associations = cleanup_param_values( tool.inputs, param_values )
                step = model.WorkflowStep()
                step.type = 'tool'
                step.tool_id = job.tool_id
                step.tool_inputs = tool.params_to_strings( param_values, trans.app )
                # NOTE: We shouldn't need to do two passes here since only
                #       an earlier job can be used as an input to a later
                #       job.
                for other_hid, input_name in associations:
                    if other_hid in hid_to_output_pair:
                        other_step, other_name = hid_to_output_pair[ other_hid ]
                        conn = model.WorkflowStepConnection()
                        conn.input_step = step
                        conn.input_name = input_name
                        # Should always be connected to an earlier step
                        conn.output_step = other_step
                        conn.output_name = other_name
                steps.append( step )
                steps_by_job_id[ job_id ] = step                
                # Store created dataset hids
                for assoc in job.output_datasets:
                    hid_to_output_pair[ assoc.dataset.hid ] = ( step, assoc.name )
            # Workflow to populate
            workflow = model.Workflow()
            workflow.name = workflow_name
            # Order the steps if possible
            attach_ordered_steps( workflow, steps )
            # And let's try to set up some reasonable locations on the canvas
            # (these are pretty arbitrary values)
            levorder = order_workflow_steps_with_levels( steps )
            base_pos = 10
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
            trans.sa_session.add( stored )
            trans.sa_session.flush()
            # Index page with message
            return trans.show_message( "Workflow '%s' created from current history." % workflow_name )
            ## return trans.show_ok_message( "<p>Workflow '%s' created.</p><p><a target='_top' href='%s'>Click to load in workflow editor</a></p>"
            ##     % ( workflow_name, web.url_for( action='editor', id=trans.security.encode_id(stored.id) ) ) )       
        
    @web.expose
    def run( self, trans, id, check_user=True, **kwargs ):
        stored = get_stored_workflow( trans, id, check_ownership=False )
        if check_user:
            user = trans.get_user()
            if stored.user != user:
                if trans.sa_session.query( model.StoredWorkflowUserShareAssociation ) \
                        .filter_by( user=user, stored_workflow=stored ).count() == 0:
                    error( "Workflow is not owned by or shared with current user" )
        # Get the latest revision
        workflow = stored.latest_workflow
        # It is possible for a workflow to have 0 steps
        if len( workflow.steps ) == 0:
            error( "Workflow cannot be run because it does not have any steps" )
        #workflow = Workflow.from_simple( simplejson.loads( stored.encoded_value ), trans.app )
        if workflow.has_cycles:
            error( "Workflow cannot be run because it contains cycles" )
        if workflow.has_errors:
            error( "Workflow cannot be run because of validation errors in some steps" )
        # Build the state for each step
        errors = {}
        if kwargs:
            # If kwargs were provided, the states for each step should have
            # been POSTed
            for step in workflow.steps:
                # Connections by input name
                step.input_connections_by_name = \
                    dict( ( conn.input_name, conn ) for conn in step.input_connections ) 
                # Extract just the arguments for this step by prefix
                p = "%s|" % step.id
                l = len(p)
                step_args = dict( ( k[l:], v ) for ( k, v ) in kwargs.iteritems() if k.startswith( p ) )
                step_errors = None
                if step.type == 'tool' or step.type is None:
                    module = module_factory.from_workflow_step( trans, step )
                    # Any connected input needs to have value DummyDataset (these
                    # are not persisted so we need to do it every time)
                    module.add_dummy_datasets( connections=step.input_connections )    
                    # Get the tool
                    tool = module.tool
                    # Get the state
                    step.state = state = module.state
                    # Get old errors
                    old_errors = state.inputs.pop( "__errors__", {} )
                    # Update the state
                    step_errors = tool.update_state( trans, tool.inputs, step.state.inputs, step_args,
                                                     update_only=True, old_errors=old_errors )
                else:
                    module = step.module = module_factory.from_workflow_step( trans, step )
                    state = step.state = module.decode_runtime_state( trans, step_args.pop( "tool_state" ) )
                    step_errors = module.update_runtime_state( trans, state, step_args )
                if step_errors:
                    errors[step.id] = state.inputs["__errors__"] = step_errors   
            if 'run_workflow' in kwargs and not errors:
                # Run each step, connecting outputs to inputs
                outputs = odict()
                for i, step in enumerate( workflow.steps ):
                    if step.type == 'tool' or step.type is None:
                        tool = trans.app.toolbox.tools_by_id[ step.tool_id ]
                        input_values = step.state.inputs
                        # Connect up
                        def callback( input, value, prefixed_name, prefixed_label ):
                            if isinstance( input, DataToolParameter ):
                                if prefixed_name in step.input_connections_by_name:
                                    conn = step.input_connections_by_name[ prefixed_name ]
                                    return outputs[ conn.output_step.id ][ conn.output_name ]
                        visit_input_values( tool.inputs, step.state.inputs, callback )
                        # Execute it
                        outputs[ step.id ] = tool.execute( trans, step.state.inputs )
                    else:
                        outputs[ step.id ] = step.module.execute( trans, step.state )
                        
                return trans.fill_template( "workflow/run_complete.mako",
                                            workflow=stored,
                                            outputs=outputs )
        else:
            for step in workflow.steps:
                if step.type == 'tool' or step.type is None:
                    # Restore the tool state for the step
                    module = module_factory.from_workflow_step( trans, step )
                    # Any connected input needs to have value DummyDataset (these
                    # are not persisted so we need to do it every time)
                    module.add_dummy_datasets( connections=step.input_connections )                  
                    # Store state with the step
                    step.module = module
                    step.state = module.state
                    # Error dict
                    if step.tool_errors:
                        errors[step.id] = step.tool_errors
                else:
                    ## Non-tool specific stuff?
                    step.module = module_factory.from_workflow_step( trans, step )
                    step.state = step.module.get_runtime_state()
                # Connections by input name
                step.input_connections_by_name = dict( ( conn.input_name, conn ) for conn in step.input_connections )
        # Render the form
        return trans.fill_template(
                    "workflow/run.mako", 
                    steps=workflow.steps,
                    workflow=stored,
                    errors=errors,
                    incoming=kwargs )
    
    @web.expose
    def configure_menu( self, trans, workflow_ids=None ):
        user = trans.get_user()
        if trans.request.method == "POST":
            if workflow_ids is None:
                workflow_ids = []
            elif type( workflow_ids ) != list:
                workflow_ids = [ workflow_ids ]
            sess = trans.sa_session
            # This explicit remove seems like a hack, need to figure out
            # how to make the association do it automatically.
            for m in user.stored_workflow_menu_entries:
                sess.delete( m )
            user.stored_workflow_menu_entries = []
            q = sess.query( model.StoredWorkflow )
            # To ensure id list is unique
            seen_workflow_ids = set()
            for id in workflow_ids:
                if id in seen_workflow_ids:
                    continue
                else:
                    seen_workflow_ids.add( id )
                m = model.StoredWorkflowMenuEntry()
                m.stored_workflow = q.get( id )
                user.stored_workflow_menu_entries.append( m )
            sess.flush()
            return trans.show_message( "Menu updated", refresh_frames=['tools'] )
        else:                
            user = trans.get_user()
            ids_in_menu = set( [ x.stored_workflow_id for x in user.stored_workflow_menu_entries ] )
            workflows = trans.sa_session.query( model.StoredWorkflow ) \
                .filter_by( user=user, deleted=False ) \
                .order_by( desc( model.StoredWorkflow.table.c.update_time ) ) \
                .all()
            shared_by_others = trans.sa_session \
                .query( model.StoredWorkflowUserShareAssociation ) \
                .filter_by( user=user ) \
                .filter( model.StoredWorkflow.deleted == False ) \
                .all()
            return trans.fill_template( "workflow/configure_menu.mako",
                                        workflows=workflows,
                                        shared_by_others=shared_by_others,
                                        ids_in_menu=ids_in_menu )
    
## ---- Utility methods -------------------------------------------------------
        
def get_stored_workflow( trans, id, check_ownership=True ):
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
    if check_ownership and not( stored.user == user ):
        error( "Workflow is not owned by current user" )
    # Looks good
    return stored

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
    
class FakeJob( object ):
    """
    Fake job object for datasets that have no creating_job_associations,
    they will be treated as "input" datasets.
    """
    def __init__( self, dataset ):
        self.is_fake = True
        self.id = "fake_%s" % dataset.id
    
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
        
        #if this hda was copied from another, we need to find the job that created the origial hda
        job_hda = dataset
        while job_hda.copied_from_history_dataset_association:
            job_hda = job_hda.copied_from_history_dataset_association
        
        if not job_hda.creating_job_associations:
            jobs[ FakeJob( dataset ) ] = [ ( None, dataset ) ]
        
        for assoc in job_hda.creating_job_associations:
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
    # Recursively clean data inputs and dynamic selects
    def cleanup( prefix, inputs, values ):
        for key, input in inputs.items():
            if isinstance( input, ( SelectToolParameter, DrillDownSelectToolParameter ) ):
                if input.is_dynamic:
                    values[key] = UnvalidatedValue( values[key] )
            if isinstance( input, DataToolParameter ):
                tmp = values[key]
                values[key] = None
                # HACK: Nested associations are not yet working, but we
                #       still need to clean them up so we can serialize
                # if not( prefix ):
                if tmp: #this is false for a non-set optional dataset
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
