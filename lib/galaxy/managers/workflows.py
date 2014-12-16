from __future__ import absolute_import

from collections import namedtuple
import json

from galaxy import model
from galaxy import exceptions
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.workflow import modules

# For WorkflowContentManager
from galaxy.util.sanitize_html import sanitize_html
from galaxy.workflow.steps import attach_ordered_steps
from galaxy.workflow.modules import module_factory, is_tool_module_type, ToolModule
from galaxy.tools.parameters.basic import DataToolParameter, DataCollectionToolParameter
from galaxy.tools.parameters import visit_input_values
from galaxy.web import url_for


class WorkflowsManager( object ):
    """ Handle CRUD type operaitons related to workflows. More interesting
    stuff regarding workflow execution, step sorting, etc... can be found in
    the galaxy.workflow module.
    """

    def __init__( self, app ):
        self.app = app

    def check_security( self, trans, has_workflow, check_ownership=True, check_accessible=True):
        """ check accessibility or ownership of workflows, storedworkflows, and
        workflowinvocations. Throw an exception or returns True if user has
        needed level of access.
        """
        if not check_ownership or check_accessible:
            return True

        # If given an invocation follow to workflow...
        if isinstance( has_workflow, model.WorkflowInvocation ):
            has_workflow = has_workflow.workflow

        # stored workflow contains security stuff - follow that workflow to
        # that unless given a stored workflow.
        if hasattr( has_workflow, "stored_workflow" ):
            stored_workflow = has_workflow.stored_workflow
        else:
            stored_workflow = has_workflow

        if stored_workflow.user != trans.user and not trans.user_is_admin():
            if check_ownership:
                raise exceptions.ItemOwnershipException()
            # else check_accessible...
            if trans.sa_session.query( model.StoredWorkflowUserShareAssociation ).filter_by(user=trans.user, stored_workflow=stored_workflow ).count() == 0:
                raise exceptions.ItemAccessibilityException()

        return True

    def get_invocation( self, trans, decoded_invocation_id ):
        try:
            workflow_invocation = trans.sa_session.query(
                self.app.model.WorkflowInvocation
            ).get( decoded_invocation_id )
        except Exception:
            raise exceptions.ObjectNotFound()
        self.check_security( trans, workflow_invocation, check_ownership=True, check_accessible=False )
        return workflow_invocation

    def cancel_invocation( self, trans, decoded_invocation_id ):
        workflow_invocation = self.get_invocation( trans, decoded_invocation_id )
        cancelled = workflow_invocation.cancel()

        if cancelled:
            trans.sa_session.add( workflow_invocation )
            trans.sa_session.flush()
        else:
            # TODO: More specific exception?
            raise exceptions.MessageException( "Cannot cancel an inactive workflow invocation." )

        return workflow_invocation

    def get_invocation_step( self, trans, decoded_workflow_invocation_step_id ):
        try:
            workflow_invocation_step = trans.sa_session.query(
                model.WorkflowInvocationStep
            ).get( decoded_workflow_invocation_step_id )
        except Exception:
            raise exceptions.ObjectNotFound()
        self.check_security( trans, workflow_invocation_step.workflow_invocation, check_ownership=True, check_accessible=False )
        return workflow_invocation_step

    def update_invocation_step( self, trans, decoded_workflow_invocation_step_id, action ):
        if action is None:
            raise exceptions.RequestParameterMissingException( "Updating workflow invocation step requires an action parameter. " )

        workflow_invocation_step = self.get_invocation_step( trans, decoded_workflow_invocation_step_id )
        workflow_invocation = workflow_invocation_step.workflow_invocation
        if not workflow_invocation.active:
            raise exceptions.RequestParameterInvalidException( "Attempting to modify the state of an completed workflow invocation." )

        step = workflow_invocation_step.workflow_step
        module = modules.module_factory.from_workflow_step( trans, step )
        performed_action = module.do_invocation_step_action( step, action )
        workflow_invocation_step.action = performed_action
        trans.sa_session.add( workflow_invocation_step )
        trans.sa_session.flush()
        return workflow_invocation_step

    def build_invocations_query( self, trans, decoded_stored_workflow_id ):
        try:
            stored_workflow = trans.sa_session.query(
                self.app.model.StoredWorkflow
            ).get( decoded_stored_workflow_id )
        except Exception:
            raise exceptions.ObjectNotFound()
        self.check_security( trans, stored_workflow, check_ownership=True, check_accessible=False )
        return trans.sa_session.query(
            model.WorkflowInvocation
        ).filter_by(
            workflow_id=stored_workflow.latest_workflow_id
        )


CreatedWorkflow = namedtuple("CreatedWorkflow", ["stored_workflow", "missing_tools"])


class WorkflowContentsManager(UsesAnnotations):

    def build_workflow_from_dict(
        self,
        trans,
        data,
        source=None,
        add_to_menu=False,
        publish=False
    ):
        # Put parameters in workflow mode
        trans.workflow_building_mode = True
        # Create new workflow from incoming dict
        workflow = model.Workflow()
        # If there's a source, put it in the workflow name.
        if source:
            name = "%s (imported from %s)" % ( data['name'], source )
        else:
            name = data['name']
        workflow.name = name
        if 'uuid' in data:
            workflow.uuid = data['uuid']
        # Assume no errors until we find a step that has some
        workflow.has_errors = False
        # Create each step
        steps = []
        # The editor will provide ids for each step that we don't need to save,
        # but do need to use to make connections
        steps_by_external_id = {}
        # Keep track of tools required by the workflow that are not available in
        # the local Galaxy instance.  Each tuple in the list of missing_tool_tups
        # will be ( tool_id, tool_name, tool_version ).
        missing_tool_tups = []
        supplied_steps = data[ 'steps' ]
        # Try to iterate through imported workflow in such a way as to
        # preserve step order.
        step_indices = supplied_steps.keys()
        try:
            step_indices = sorted( step_indices, key=int )
        except ValueError:
            # to defensive, were these ever or will they ever not be integers?
            pass
        # First pass to build step objects and populate basic values
        for step_index in step_indices:
            step_dict = supplied_steps[ step_index ]
            # Create the model class for the step
            step = model.WorkflowStep()
            steps.append( step )
            steps_by_external_id[ step_dict['id' ] ] = step
            # FIXME: Position should be handled inside module
            step.position = step_dict['position']
            module = module_factory.from_dict( trans, step_dict, secure=False )
            module.save_to_step( step )
            if module.type == 'tool' and module.tool is None:
                # A required tool is not available in the local Galaxy instance.
                missing_tool_tup = ( step_dict[ 'tool_id' ], step_dict[ 'name' ], step_dict[ 'tool_version' ] )
                if missing_tool_tup not in missing_tool_tups:
                    missing_tool_tups.append( missing_tool_tup )
                # Save the entire step_dict in the unused config field, be parsed later
                # when we do have the tool
                step.config = json.dumps(step_dict)
            if step.tool_errors:
                workflow.has_errors = True
            # Stick this in the step temporarily
            step.temp_input_connections = step_dict['input_connections']
            # Save step annotation.
            annotation = step_dict[ 'annotation' ]
            if annotation:
                annotation = sanitize_html( annotation, 'utf-8', 'text/html' )
                self.add_item_annotation( trans.sa_session, trans.get_user(), step, annotation )
        # Second pass to deal with connections between steps
        for step in steps:
            # Input connections
            for input_name, conn_list in step.temp_input_connections.iteritems():
                if not conn_list:
                    continue
                if not isinstance(conn_list, list):  # Older style singleton connection
                    conn_list = [conn_list]
                for conn_dict in conn_list:
                    conn = model.WorkflowStepConnection()
                    conn.input_step = step
                    conn.input_name = input_name
                    conn.output_name = conn_dict['output_name']
                    conn.output_step = steps_by_external_id[ conn_dict['id'] ]
            del step.temp_input_connections

        # Order the steps if possible
        attach_ordered_steps( workflow, steps )

        # Connect up
        stored = model.StoredWorkflow()
        stored.name = workflow.name
        workflow.stored_workflow = stored
        stored.latest_workflow = workflow
        stored.user = trans.user
        stored.published = publish
        if data[ 'annotation' ]:
            annotation = sanitize_html( data[ 'annotation' ], 'utf-8', 'text/html' )
            self.add_item_annotation( trans.sa_session, stored.user, stored, annotation )

        # Persist
        trans.sa_session.add( stored )
        trans.sa_session.flush()

        if add_to_menu:
            if trans.user.stored_workflow_menu_entries is None:
                trans.user.stored_workflow_menu_entries = []
            menuEntry = model.StoredWorkflowMenuEntry()
            menuEntry.stored_workflow = stored
            trans.user.stored_workflow_menu_entries.append( menuEntry )
            trans.sa_session.flush()

        return CreatedWorkflow(
            stored_workflow=stored,
            missing_tools=missing_tool_tups
        )

    def update_workflow_from_dict(self, trans, stored_workflow, workflow_data, from_editor=False):
        # Put parameters in workflow mode
        trans.workflow_building_mode = True
        # Convert incoming workflow data from json if coming from editor
        data = json.loads(workflow_data) if from_editor else workflow_data
        # Create new workflow from incoming data
        workflow = model.Workflow()
        # Just keep the last name (user can rename later)
        workflow.name = stored_workflow.name
        # Assume no errors until we find a step that has some
        workflow.has_errors = False
        # Create each step
        steps = []
        # The editor will provide ids for each step that we don't need to save,
        # but do need to use to make connections
        steps_by_external_id = {}
        errors = []
        for key, step_dict in data['steps'].iteritems():
            is_tool = is_tool_module_type( step_dict[ 'type' ] )
            if is_tool and step_dict['tool_id'] not in trans.app.toolbox.tools_by_id:
                errors.append("Step %s requires tool '%s'." % (step_dict['id'], step_dict['tool_id']))
        if errors:
            raise MissingToolsException(workflow, errors)

        # First pass to build step objects and populate basic values
        for key, step_dict in data['steps'].iteritems():
            # Create the model class for the step
            step = model.WorkflowStep()
            steps.append( step )
            steps_by_external_id[ step_dict['id' ] ] = step
            # FIXME: Position should be handled inside module
            step.position = step_dict['position']
            module = module_factory.from_dict( trans, step_dict, secure=from_editor )
            module.save_to_step( step )
            if 'workflow_outputs' in step_dict:
                for output_name in step_dict['workflow_outputs']:
                    m = model.WorkflowOutput(workflow_step=step, output_name=output_name)
                    trans.sa_session.add(m)
            if step.tool_errors:
                # DBTODO Check for conditional inputs here.
                workflow.has_errors = True
            # Stick this in the step temporarily
            step.temp_input_connections = step_dict['input_connections']
            # Save step annotation.
            annotation = step_dict[ 'annotation' ]
            if annotation:
                annotation = sanitize_html( annotation, 'utf-8', 'text/html' )
                self.add_item_annotation( trans.sa_session, trans.get_user(), step, annotation )
        # Second pass to deal with connections between steps
        for step in steps:
            # Input connections
            for input_name, conns in step.temp_input_connections.iteritems():
                if conns:
                    conn_dicts = conns if isinstance(conns, list) else [ conns ]
                    for conn_dict in conn_dicts:
                        conn = model.WorkflowStepConnection()
                        conn.input_step = step
                        conn.input_name = input_name
                        conn.output_name = conn_dict['output_name']
                        conn.output_step = steps_by_external_id[ conn_dict['id'] ]
            del step.temp_input_connections
        # Order the steps if possible
        attach_ordered_steps( workflow, steps )
        # Connect up
        workflow.stored_workflow = stored_workflow
        stored_workflow.latest_workflow = workflow
        # Persist
        trans.sa_session.flush()
        # Return something informative
        errors = []
        if workflow.has_errors:
            errors.append( "Some steps in this workflow have validation errors" )
        if workflow.has_cycles:
            errors.append( "This workflow contains cycles" )
        return workflow, errors

    def workflow_to_dict( self, trans, stored, style="export" ):
        """ Export the workflow contents to a dictionary ready for JSON-ification and to be
        sent out via API for instance. There are two styles of export allowed 'editor' and 'export'.
        The Galaxy team will do it best to preserve the backward compatibility of the 'export' stye -
        but the 'editor' style is subject to rapid and unannounced changes.
        """
        if style == "editor":
            return self._workflow_to_dict_editor( trans, stored )
        else:
            return self._workflow_to_dict_export( trans, stored )

    def _workflow_to_dict_editor(self, trans, stored):
        """
        """
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
            if not module:
                step_annotation = self.get_item_annotation_obj( trans.sa_session, trans.user, step )
                annotation_str = ""
                if step_annotation:
                    annotation_str = step_annotation.annotation
                invalid_tool_form_html = """<div class="toolForm tool-node-error"><div class="toolFormTitle form-row-error">Unrecognized Tool: %s</div><div class="toolFormBody"><div class="form-row">
                                            The tool id '%s' for this tool is unrecognized.<br/><br/>To save this workflow, you will need to delete this step or enable the tool.
                                            </div></div></div>""" % (step.tool_id, step.tool_id)
                step_dict = {
                    'id': step.order_index,
                    'type': 'invalid',
                    'tool_id': step.tool_id,
                    'name': 'Unrecognized Tool: %s' % step.tool_id,
                    'tool_state': None,
                    'tooltip': None,
                    'tool_errors': ["Unrecognized Tool Id: %s" % step.tool_id],
                    'data_inputs': [],
                    'data_outputs': [],
                    'form_html': invalid_tool_form_html,
                    'annotation': annotation_str,
                    'input_connections': {},
                    'post_job_actions': {},
                    'workflow_outputs': []
                }
                # Position
                step_dict['position'] = step.position
                # Add to return value
                data['steps'][step.order_index] = step_dict
                continue
            # Fix any missing parameters
            upgrade_message = module.check_and_update_state()
            if upgrade_message:
                # FIXME: Frontend should be able to handle workflow messages
                #        as a dictionary not just the values
                data['upgrade_messages'][step.order_index] = upgrade_message.values()
            # Get user annotation.
            step_annotation = self.get_item_annotation_obj( trans.sa_session, trans.user, step )
            annotation_str = ""
            if step_annotation:
                annotation_str = step_annotation.annotation
            # Pack attributes into plain dictionary
            step_dict = {
                'id': step.order_index,
                'type': module.type,
                'tool_id': module.get_tool_id(),
                'name': module.get_name(),
                'tool_state': module.get_state(),
                'tooltip': module.get_tooltip( static_path=url_for( '/static' ) ),
                'tool_errors': module.get_errors(),
                'data_inputs': module.get_data_inputs(),
                'data_outputs': module.get_data_outputs(),
                'form_html': module.get_config_form(),
                'annotation': annotation_str,
                'post_job_actions': {},
                'workflow_outputs': []
            }
            # Connections
            input_connections = step.input_connections
            input_connections_type = {}
            multiple_input = {}  # Boolean value indicating if this can be mutliple
            if step.type is None or step.type == 'tool':
                # Determine full (prefixed) names of valid input datasets
                data_input_names = {}

                def callback( input, value, prefixed_name, prefixed_label ):
                    if isinstance( input, DataToolParameter ) or isinstance( input, DataCollectionToolParameter ):
                        data_input_names[ prefixed_name ] = True
                        multiple_input[ prefixed_name ] = input.multiple
                        if isinstance( input, DataToolParameter ):
                            input_connections_type[ input.name ] = "dataset"
                        if isinstance( input, DataCollectionToolParameter ):
                            input_connections_type[ input.name ] = "dataset_collection"
                visit_input_values( module.tool.inputs, module.state.inputs, callback )
                # Filter
                # FIXME: this removes connection without displaying a message currently!
                input_connections = [ conn for conn in input_connections if conn.input_name in data_input_names ]
                # post_job_actions
                pja_dict = {}
                for pja in step.post_job_actions:
                    pja_dict[pja.action_type + pja.output_name] = dict(
                        action_type=pja.action_type,
                        output_name=pja.output_name,
                        action_arguments=pja.action_arguments
                    )
                step_dict['post_job_actions'] = pja_dict
                #workflow outputs
                outputs = []
                for output in step.workflow_outputs:
                    outputs.append(output.output_name)
                step_dict['workflow_outputs'] = outputs
            # Encode input connections as dictionary
            input_conn_dict = {}
            for conn in input_connections:
                input_type = "dataset"
                if conn.input_name in input_connections_type:
                    input_type = input_connections_type[ conn.input_name ]
                conn_dict = dict( id=conn.output_step.order_index, output_name=conn.output_name, input_type=input_type )
                if conn.input_name in multiple_input:
                    if conn.input_name in input_conn_dict:
                        input_conn_dict[ conn.input_name ].append( conn_dict )
                    else:
                        input_conn_dict[ conn.input_name ] = [ conn_dict ]
                else:
                    input_conn_dict[ conn.input_name ] = conn_dict
            step_dict['input_connections'] = input_conn_dict
            # Position
            step_dict['position'] = step.position
            # Add to return value
            data['steps'][step.order_index] = step_dict
        return data

    def _workflow_to_dict_export( self, trans, stored ):
        """ Export the workflow contents to a dictionary ready for JSON-ification and export.
        """
        workflow = stored.latest_workflow
        workflow_annotation = self.get_item_annotation_obj( trans.sa_session, trans.user, stored )
        annotation_str = ""
        if workflow_annotation:
            annotation_str = workflow_annotation.annotation
        # Pack workflow data into a dictionary and return
        data = {}
        data['a_galaxy_workflow'] = 'true'  # Placeholder for identifying galaxy workflow
        data['format-version'] = "0.1"
        data['name'] = workflow.name
        data['annotation'] = annotation_str
        if workflow.uuid is not None:
            data['uuid'] = str(workflow.uuid)
        data['steps'] = {}
        # For each step, rebuild the form and encode the state
        for step in workflow.steps:
            # Load from database representation
            module = module_factory.from_workflow_step( trans, step )
            if not module:
                return None
            # Get user annotation.
            step_annotation = self.get_item_annotation_obj(trans.sa_session, trans.user, step )
            annotation_str = ""
            if step_annotation:
                annotation_str = step_annotation.annotation
            # Step info
            step_dict = {
                'id': step.order_index,
                'type': module.type,
                'tool_id': module.get_tool_id(),
                'tool_version': step.tool_version,
                'name': module.get_name(),
                'tool_state': module.get_state( secure=False ),
                'tool_errors': module.get_errors(),
                ## 'data_inputs': module.get_data_inputs(),
                ## 'data_outputs': module.get_data_outputs(),
                'annotation': annotation_str
            }
            # Add post-job actions to step dict.
            if module.type == 'tool':
                pja_dict = {}
                for pja in step.post_job_actions:
                    pja_dict[pja.action_type + pja.output_name] = dict( action_type=pja.action_type,
                                                                        output_name=pja.output_name,
                                                                        action_arguments=pja.action_arguments )
                step_dict[ 'post_job_actions' ] = pja_dict
            # Data inputs
            step_dict['inputs'] = module.get_runtime_input_dicts( annotation_str )
            # User outputs
            step_dict['user_outputs'] = []

            # All step outputs
            step_dict['outputs'] = []
            if type( module ) is ToolModule:
                for output in module.get_data_outputs():
                    step_dict['outputs'].append( { 'name': output['name'], 'type': output['extensions'][0] } )

            # Connections
            input_connections = step.input_connections
            if step.type is None or step.type == 'tool':
                # Determine full (prefixed) names of valid input datasets
                data_input_names = {}

                def callback( input, value, prefixed_name, prefixed_label ):
                    if isinstance( input, DataToolParameter ) or isinstance( input, DataCollectionToolParameter ):
                        data_input_names[ prefixed_name ] = True
                # FIXME: this updates modules silently right now; messages from updates should be provided.
                module.check_and_update_state()
                visit_input_values( module.tool.inputs, module.state.inputs, callback )
                # Filter
                # FIXME: this removes connection without displaying a message currently!
                input_connections = [ conn for conn in input_connections if conn.input_name in data_input_names ]

            # Encode input connections as dictionary
            input_conn_dict = {}
            unique_input_names = set( [conn.input_name for conn in input_connections] )
            for input_name in unique_input_names:
                input_conn_dict[ input_name ] = \
                    [ dict( id=conn.output_step.order_index, output_name=conn.output_name ) for conn in input_connections if conn.input_name == input_name ]

            # Preserve backward compatability. Previously Galaxy
            # assumed input connections would be dictionaries not
            # lists of dictionaries, so replace any singleton list
            # with just the dictionary so that workflows exported from
            # newer Galaxy instances can be used with older Galaxy
            # instances if they do no include multiple input
            # tools. This should be removed at some point. Mirrored
            # hack in _workflow_from_dict should never be removed so
            # existing workflow exports continue to function.
            for input_name, input_conn in dict(input_conn_dict).iteritems():
                if len(input_conn) == 1:
                    input_conn_dict[input_name] = input_conn[0]
            step_dict['input_connections'] = input_conn_dict
            # Position
            step_dict['position'] = step.position
            # Add to return value
            data['steps'][step.order_index] = step_dict
        return data


class MissingToolsException(object):

    def __init__(self, workflow, errors):
        self.workflow = workflow
        self.errors = errors
