from __future__ import absolute_import

from six import string_types

from collections import namedtuple
import logging
import json
import uuid

from sqlalchemy import and_

from galaxy import model
from galaxy import util
from galaxy import exceptions
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.workflow import modules
from .base import decode_id

# For WorkflowContentManager
from galaxy.util.sanitize_html import sanitize_html
from galaxy.workflow.steps import attach_ordered_steps
from galaxy.workflow.modules import module_factory, is_tool_module_type, ToolModule, WorkflowModuleInjector, MissingToolException
from galaxy.tools.parameters.basic import DataToolParameter, DataCollectionToolParameter, workflow_building_modes
from galaxy.tools.parameters import visit_input_values, params_to_incoming
from galaxy.jobs.actions.post import ActionBox
from galaxy.web import url_for

log = logging.getLogger( __name__ )


class WorkflowsManager( object ):
    """ Handle CRUD type operaitons related to workflows. More interesting
    stuff regarding workflow execution, step sorting, etc... can be found in
    the galaxy.workflow module.
    """

    def __init__( self, app ):
        self.app = app

    def get_stored_workflow( self, trans, workflow_id ):
        """ Use a supplied ID (UUID or encoded stored workflow ID) to find
        a workflow.
        """
        if util.is_uuid(workflow_id):
            # see if they have passed in the UUID for a workflow that is attached to a stored workflow
            workflow_uuid = uuid.UUID(workflow_id)
            stored_workflow = trans.sa_session.query(trans.app.model.StoredWorkflow).filter( and_(
                trans.app.model.StoredWorkflow.latest_workflow_id == trans.app.model.Workflow.id,
                trans.app.model.Workflow.uuid == workflow_uuid
            )).first()
            if stored_workflow is None:
                raise exceptions.ObjectNotFound( "Workflow not found: %s" % workflow_id )
        else:
            workflow_id = decode_id( self.app, workflow_id )
            query = trans.sa_session.query( trans.app.model.StoredWorkflow )
            stored_workflow = query.get( workflow_id )
        if stored_workflow is None:
            raise exceptions.ObjectNotFound( "No such workflow found." )
        return stored_workflow

    def get_stored_accessible_workflow( self, trans, workflow_id ):
        """ Get a stored workflow from a encoded stored workflow id and
        make sure it accessible to the user.
        """
        stored_workflow = self.get_stored_workflow( trans, workflow_id )

        # check to see if user has permissions to selected workflow
        if stored_workflow.user != trans.user and not trans.user_is_admin():
            if trans.sa_session.query(trans.app.model.StoredWorkflowUserShareAssociation).filter_by(user=trans.user, stored_workflow=stored_workflow).count() == 0:
                message = "Workflow is not owned by or shared with current user"
                raise exceptions.ItemAccessibilityException( message )

        return stored_workflow

    def get_owned_workflow( self, trans, encoded_workflow_id ):
        """ Get a workflow (non-stored) from a encoded workflow id and
        make sure it accessible to the user.
        """
        workflow_id = decode_id( self.app, encoded_workflow_id )
        workflow = trans.sa_session.query( model.Workflow ).get( workflow_id )
        self.check_security( trans, workflow, check_ownership=True )
        return workflow

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
        if isinstance( has_workflow, model.Workflow ):
            stored_workflow = has_workflow.top_level_stored_workflow
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


CreatedWorkflow = namedtuple("CreatedWorkflow", ["stored_workflow", "workflow", "missing_tools"])


class WorkflowContentsManager(UsesAnnotations):

    def __init__(self, app):
        self.app = app

    def build_workflow_from_dict(
        self,
        trans,
        data,
        source=None,
        add_to_menu=False,
        publish=False,
        create_stored_workflow=True,
        exact_tools=False,
    ):
        # Put parameters in workflow mode
        trans.workflow_building_mode = True
        # If there's a source, put it in the workflow name.
        if source:
            name = "%s (imported from %s)" % ( data['name'], source )
        else:
            name = data['name']
        workflow, missing_tool_tups = self._workflow_from_dict(
            trans,
            data,
            name=name,
            exact_tools=exact_tools,
        )
        if 'uuid' in data:
            workflow.uuid = data['uuid']

        if create_stored_workflow:
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

            if add_to_menu:
                if trans.user.stored_workflow_menu_entries is None:
                    trans.user.stored_workflow_menu_entries = []
                menuEntry = model.StoredWorkflowMenuEntry()
                menuEntry.stored_workflow = stored
                trans.user.stored_workflow_menu_entries.append( menuEntry )

        else:
            stored = None
            # Persist
            trans.sa_session.add( workflow )

        trans.sa_session.flush()

        return CreatedWorkflow(
            stored_workflow=stored,
            workflow=workflow,
            missing_tools=missing_tool_tups
        )

    def update_workflow_from_dict(self, trans, stored_workflow, workflow_data):
        # Put parameters in workflow mode
        trans.workflow_building_mode = True

        workflow, missing_tool_tups = self._workflow_from_dict(
            trans,
            workflow_data,
            name=stored_workflow.name,
        )

        if missing_tool_tups:
            errors = []
            for missing_tool_tup in missing_tool_tups:
                errors.append("Step %s requires tool '%s'." % (missing_tool_tup[3], missing_tool_tup[0]))
            raise MissingToolsException(workflow, errors)

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

    def _workflow_from_dict(self, trans, data, name, exact_tools=False):
        if isinstance(data, string_types):
            data = json.loads(data)

        # Create new workflow from source data
        workflow = model.Workflow()

        workflow.name = name

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

        for step_dict in self.__walk_step_dicts( data ):
            module, step = self.__track_module_from_dict( trans, steps, steps_by_external_id, step_dict, exact_tools=exact_tools )
            is_tool = is_tool_module_type( module.type )
            if is_tool and module.tool is None:
                # A required tool is not available in the local Galaxy instance.
                tool_id = step_dict.get('content_id', step_dict.get('tool_id', None))
                assert tool_id is not None  # Threw an exception elsewhere if not

                missing_tool_tup = ( tool_id, step_dict[ 'name' ], step_dict[ 'tool_version' ], step_dict[ 'id'] )
                if missing_tool_tup not in missing_tool_tups:
                    missing_tool_tups.append( missing_tool_tup )

                # Save the entire step_dict in the unused config field, be parsed later
                # when we do have the tool
                step.config = json.dumps(step_dict)

            if step.tool_errors:
                workflow.has_errors = True

        # Second pass to deal with connections between steps
        self.__connect_workflow_steps( steps, steps_by_external_id )

        # Order the steps if possible
        attach_ordered_steps( workflow, steps )

        return workflow, missing_tool_tups

    def workflow_to_dict( self, trans, stored, style="export" ):
        """ Export the workflow contents to a dictionary ready for JSON-ification and to be
        sent out via API for instance. There are three styles of export allowed 'export', 'instance', and
        'editor'. The Galaxy team will do it best to preserve the backward compatibility of the
        'export' stye - this is the export method meant to be portable across Galaxy instances and over
        time. The 'editor' style is subject to rapid and unannounced changes. The 'instance' export
        option describes the workflow in a context more tied to the current Galaxy instance and includes
        fields like 'url' and 'url' and actual unencoded step ids instead of 'order_index'.
        """
        if style == "editor":
            return self._workflow_to_dict_editor( trans, stored )
        elif style == "legacy":
            return self._workflow_to_dict_instance( stored, legacy=True )
        elif style == "instance":
            return self._workflow_to_dict_instance( stored, legacy=False )
        elif style == "run":
            return self._workflow_to_dict_run( trans, stored )
        else:
            return self._workflow_to_dict_export( trans, stored )

    def _workflow_to_dict_run( self, trans, stored ):
        """
        Builds workflow dictionary used by run workflow form
        """
        workflow = stored.latest_workflow
        if len( workflow.steps ) == 0:
            raise exceptions.MessageException( 'Workflow cannot be run because it does not have any steps.' )
        if workflow.has_cycles:
            raise exceptions.MessageException( 'Workflow cannot be run because it contains cycles.' )
        trans.workflow_building_mode = workflow_building_modes.USE_HISTORY
        module_injector = WorkflowModuleInjector( trans )
        has_upgrade_messages = False
        step_version_changes = []
        missing_tools = []
        errors = {}
        for step in workflow.steps:
            try:
                module_injector.inject( step, steps=workflow.steps )
            except MissingToolException:
                if step.tool_id not in missing_tools:
                    missing_tools.append( step.tool_id )
                continue
            if step.upgrade_messages:
                has_upgrade_messages = True
            if step.type == 'tool' or step.type is None:
                if step.module.version_changes:
                    step_version_changes.extend( step.module.version_changes )
                if step.tool_errors:
                    errors[ step.id ] = step.tool_errors
        if missing_tools:
            workflow.annotation = self.get_item_annotation_str( trans.sa_session, trans.user, workflow )
            raise exceptions.MessageException( 'Following tools missing: %s' % missing_tools )
        workflow.annotation = self.get_item_annotation_str( trans.sa_session, trans.user, workflow )
        step_order_indices = {}
        for step in workflow.steps:
            step_order_indices[ step.id ] = step.order_index
        step_models = []
        for i, step in enumerate( workflow.steps ):
            step_model = None

            def step_title(step, default_name):
                return "%d: %s" % (step.order_index + 1, step.label or default_name)

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
                step_model["name"] = step_title(step, step_model.get("name"))
            else:
                inputs = step.module.get_runtime_inputs( connections=step.output_connections )
                step_model = {
                    'name'   : step_title(step, step.module.name),
                    'inputs' : [ input.to_dict( trans ) for input in inputs.itervalues() ]
                }
            step_model[ 'step_type' ] = step.type
            step_model[ 'step_index' ] = step.order_index
            step_model[ 'output_connections' ] = [ {
                'input_step_index'  : step_order_indices.get( oc.input_step_id ),
                'output_step_index' : step_order_indices.get( oc.output_step_id ),
                'input_name'        : oc.input_name,
                'output_name'       : oc.output_name
            } for oc in step.output_connections ]
            if step.annotations:
                step_model[ 'annotation' ] = step.annotations[ 0 ].annotation
            if step.upgrade_messages:
                step_model[ 'messages' ] = step.upgrade_messages
            step_models.append( step_model )
        return {
            'id'                    : trans.app.security.encode_id( stored.id ),
            'history_id'            : trans.app.security.encode_id( trans.history.id ) if trans.history else None,
            'name'                  : stored.name,
            'steps'                 : step_models,
            'step_version_changes'  : step_version_changes,
            'has_upgrade_messages'  : has_upgrade_messages
        }

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
                invalid_tool_form_html = """<div class="toolForm tool-node-error">
                                            <div class="toolFormTitle form-row-error">Unrecognized Tool: %s</div>
                                            <div class="toolFormBody"><div class="form-row">
                                            The tool id '%s' for this tool is unrecognized.<br/><br/>
                                            To save this workflow, you will need to delete this step or enable the tool.
                                            </div></div></div>""" % (step.tool_id, step.tool_id)
                step_dict = {
                    'id': step.order_index,
                    'type': 'invalid',
                    'content_id': step.content_id,
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
                    'uuid': str(step.uuid),
                    'label': step.label or None,
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
                data['upgrade_messages'][step.order_index] = upgrade_message
            if (hasattr(module, "version_changes")) and (module.version_changes):
                if step.order_index in data['upgrade_messages']:
                    data['upgrade_messages'][step.order_index][module.tool.name] = "\n".join(module.version_changes)
                else:
                    data['upgrade_messages'][step.order_index] = {module.tool.name: "\n".join(module.version_changes)}
            # Get user annotation.
            step_annotation = self.get_item_annotation_obj( trans.sa_session, trans.user, step )
            annotation_str = ""
            if step_annotation:
                annotation_str = step_annotation.annotation
            form_html = None
            if trans.history:
                # If in a web session, attach form html. No reason to do
                # so for API requests.
                form_html = module.get_config_form()
            # Pack attributes into plain dictionary
            step_dict = {
                'id': step.order_index,
                'type': module.type,
                'content_id': module.get_content_id(),
                'name': module.get_name(),
                'tool_state': module.get_state(),
                'tooltip': module.get_tooltip( static_path=url_for( '/static' ) ),
                'tool_errors': module.get_errors(),
                'data_inputs': module.get_data_inputs(),
                'data_outputs': module.get_data_outputs(),
                'form_html': form_html,
                'annotation': annotation_str,
                'post_job_actions': {},
                'uuid': str(step.uuid) if step.uuid else None,
                'label': step.label or None,
                'workflow_outputs': []
            }
            # Connections
            input_connections = step.input_connections
            input_connections_type = {}
            multiple_input = {}  # Boolean value indicating if this can be mutliple
            if step.type is None or step.type == 'tool':
                # Determine full (prefixed) names of valid input datasets
                data_input_names = {}

                def callback( input, prefixed_name, **kwargs ):
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

            # workflow outputs
            outputs = []
            for output in step.unique_workflow_outputs:
                output_label = output.label
                output_name = output.output_name
                output_uuid = str(output.uuid) if output.uuid else None
                outputs.append({"output_name": output_name,
                                "uuid": output_uuid,
                                "label": output_label})
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

    def _workflow_to_dict_export( self, trans, stored=None, workflow=None ):
        """ Export the workflow contents to a dictionary ready for JSON-ification and export.
        """
        if workflow is None:
            assert stored is not None
            workflow = stored.latest_workflow

        annotation_str = ""
        if stored is not None:
            workflow_annotation = self.get_item_annotation_obj( trans.sa_session, trans.user, stored )
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
            content_id = module.get_content_id()
            # Step info
            step_dict = {
                'id': step.order_index,
                'type': module.type,
                'content_id': content_id,
                'tool_id': content_id,  # For worklfows exported to older Galaxies,
                                        # eliminate after a few years...
                'tool_version': step.tool_version,
                'name': module.get_name(),
                'tool_state': module.get_state(),
                'tool_errors': module.get_errors(),
                'uuid': str(step.uuid),
                'label': step.label or None,
                # 'data_inputs': module.get_data_inputs(),
                # 'data_outputs': module.get_data_outputs(),
                'annotation': annotation_str
            }
            # Add tool shed repository information and post-job actions to step dict.
            if module.type == 'tool':
                if module.tool.tool_shed_repository:
                    tsr = module.tool.tool_shed_repository
                    step_dict["tool_shed_repository"] = {
                        'name': tsr.name,
                        'owner': tsr.owner,
                        'changeset_revision': tsr.changeset_revision,
                        'tool_shed': tsr.tool_shed
                    }
                pja_dict = {}
                for pja in step.post_job_actions:
                    pja_dict[pja.action_type + pja.output_name] = dict(
                        action_type=pja.action_type,
                        output_name=pja.output_name,
                        action_arguments=pja.action_arguments )
                step_dict[ 'post_job_actions' ] = pja_dict

            if module.type == 'subworkflow':
                del step_dict['content_id']
                del step_dict['tool_version']
                del step_dict['tool_state']
                del step_dict['tool_errors']
                subworkflow = step.subworkflow
                subworkflow_as_dict = self._workflow_to_dict_export(
                    trans,
                    stored=None,
                    workflow=subworkflow
                )
                step_dict['subworkflow'] = subworkflow_as_dict

            # Data inputs
            step_dict['inputs'] = module.get_runtime_input_dicts( annotation_str )
            # User outputs

            workflow_outputs_dicts = []
            for workflow_output in step.unique_workflow_outputs:
                workflow_output_dict = dict(
                    output_name=workflow_output.output_name,
                    label=workflow_output.label,
                    uuid=str(workflow_output.uuid) if workflow_output.uuid is not None else None,
                )
                workflow_outputs_dicts.append(workflow_output_dict)
            step_dict['workflow_outputs'] = workflow_outputs_dicts

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

                def callback( input, prefixed_name, **kwargs ):
                    if isinstance( input, DataToolParameter ) or isinstance( input, DataCollectionToolParameter ):
                        data_input_names[ prefixed_name ] = True
                # FIXME: this updates modules silently right now; messages from updates should be provided.
                module.check_and_update_state()
                visit_input_values( module.tool.inputs, module.state.inputs, callback )
                # Filter
                # FIXME: this removes connection without displaying a message currently!
                input_connections = [ conn for conn in input_connections if (conn.input_name in data_input_names or conn.non_data_connection) ]

            # Encode input connections as dictionary
            input_conn_dict = {}
            unique_input_names = set( [conn.input_name for conn in input_connections] )
            for input_name in unique_input_names:
                input_conn_dicts = []
                for conn in input_connections:
                    if conn.input_name != input_name:
                        continue
                    input_conn = dict(
                        id=conn.output_step.order_index,
                        output_name=conn.output_name
                    )
                    if conn.input_subworkflow_step is not None:
                        subworkflow_step_id = conn.input_subworkflow_step.order_index
                        input_conn["input_subworkflow_step_id"] = subworkflow_step_id

                    input_conn_dicts.append(input_conn)
                input_conn_dict[ input_name ] = input_conn_dicts

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

    def _workflow_to_dict_instance(self, stored, legacy=True):
        encode = self.app.security.encode_id
        sa_session = self.app.model.context
        item = stored.to_dict( view='element', value_mapper={ 'id': encode } )
        workflow = stored.latest_workflow
        item['url'] = url_for('workflow', id=item['id'])
        item['owner'] = stored.user.username
        inputs = {}
        for step in workflow.input_steps:
            step_type = step.type
            if step.tool_inputs and "name" in step.tool_inputs:
                label = step.tool_inputs['name']
            elif step_type == "data_input":
                label = "Input Dataset"
            elif step_type == "data_collection_input":
                label = "Input Dataset Collection"
            else:
                raise ValueError("Invalid step_type %s" % step_type)
            if legacy:
                index = step.id
            else:
                index = step.order_index
            step_uuid = str(step.uuid) if step.uuid else None
            inputs[index] = {'label': label, 'value': "", "uuid": step_uuid}
        item['inputs'] = inputs
        item['annotation'] = self.get_item_annotation_str( sa_session, stored.user, stored )
        steps = {}
        steps_to_order_index = {}
        for step in workflow.steps:
            steps_to_order_index[step.id] = step.order_index
        for step in workflow.steps:
            step_uuid = str(step.uuid) if step.uuid else None
            step_id = step.id if legacy else step.order_index
            step_type = step.type
            step_dict = {'id': step_id,
                         'type': step_type,
                         'tool_id': step.tool_id,
                         'tool_version': step.tool_version,
                         'annotation': self.get_item_annotation_str( sa_session, stored.user, step ),
                         'tool_inputs': step.tool_inputs,
                         'input_steps': {}}

            if step_type == 'subworkflow':
                del step_dict['tool_id']
                del step_dict['tool_version']
                del step_dict['tool_inputs']
                workflow = step.subworkflow
                step_dict['stored_workflow_id'] = encode(workflow.stored_workflow.id)
                step_dict['workflow_id'] = encode(workflow.id)

            for conn in step.input_connections:
                step_id = step.id if legacy else step.order_index
                source_id = conn.output_step_id
                source_step = source_id if legacy else steps_to_order_index[source_id]
                step_dict['input_steps'][conn.input_name] = {'source_step': source_step,
                                                             'step_output': conn.output_name}

            steps[step_id] = step_dict

        item['steps'] = steps
        return item

    def __walk_step_dicts( self, data ):
        """ Walk over the supplid step dictionaries and return them in a way designed
        to preserve step order when possible.
        """
        supplied_steps = data[ 'steps' ]
        # Try to iterate through imported workflow in such a way as to
        # preserve step order.
        step_indices = supplied_steps.keys()
        try:
            step_indices = sorted( step_indices, key=int )
        except ValueError:
            # to defensive, were these ever or will they ever not be integers?
            pass

        discovered_labels = set()
        discovered_uuids = set()

        discovered_output_labels = set()
        discovered_output_uuids = set()

        # First pass to build step objects and populate basic values
        for step_index in step_indices:
            step_dict = supplied_steps[ step_index ]
            uuid = step_dict.get("uuid", None)
            if uuid and uuid != "None":
                if uuid in discovered_uuids:
                    raise exceptions.DuplicatedIdentifierException("Duplicate step UUID in request.")
                discovered_uuids.add(uuid)
            label = step_dict.get("label", None)
            if label:
                if label in discovered_labels:
                    raise exceptions.DuplicatedIdentifierException("Duplicated step label in request.")
                discovered_labels.add(label)

            if 'workflow_outputs' in step_dict:
                outputs = step_dict['workflow_outputs']
                # outputs may be list of name (deprecated legacy behavior)
                # or dictionary of names to {uuid: <uuid>, label: <label>}
                if isinstance(outputs, dict):
                    for output_name in outputs:
                        output_dict = outputs[output_name]
                        output_label = output_dict.get("label", None)
                        if output_label:
                            if label in discovered_output_labels:
                                raise exceptions.DuplicatedIdentifierException("Duplicated workflow output label in request.")
                            discovered_output_labels.add(label)

                        output_uuid = step_dict.get("output_uuid", None)
                        if output_uuid:
                            if output_uuid in discovered_output_uuids:
                                raise exceptions.DuplicatedIdentifierException("Duplicate workflow output UUID in request.")
                            discovered_output_uuids.add(uuid)

            yield step_dict

    def __track_module_from_dict( self, trans, steps, steps_by_external_id, step_dict, exact_tools=False ):
        module, step = self.__module_from_dict( trans, step_dict, exact_tools=exact_tools )
        # Create the model class for the step
        steps.append( step )
        steps_by_external_id[ step_dict['id' ] ] = step
        if 'workflow_outputs' in step_dict:
            workflow_outputs = step_dict['workflow_outputs']
            found_output_names = set([])
            for workflow_output in workflow_outputs:
                # Allow workflow outputs as list of output_names for backward compatiblity.
                if not isinstance(workflow_output, dict):
                    workflow_output = {"output_name": workflow_output}
                output_name = workflow_output["output_name"]
                if output_name in found_output_names:
                    raise exceptions.ObjectAttributeInvalidException("Duplicate workflow outputs with name [%s] found." % output_name)
                if not output_name:
                    raise exceptions.ObjectAttributeInvalidException("Workflow output with empty name encountered.")
                found_output_names.add(output_name)
                uuid = workflow_output.get("uuid", None)
                label = workflow_output.get("label", None)
                m = step.create_or_update_workflow_output(
                    output_name=output_name,
                    uuid=uuid,
                    label=label,
                )
                trans.sa_session.add(m)
        return module, step

    def __module_from_dict( self, trans, step_dict, exact_tools=False ):
        """ Create a WorkflowStep model object and corresponding module
        representing type-specific functionality from the incoming dictionary.
        """
        step = model.WorkflowStep()
        # TODO: Consider handling position inside module.
        step.position = step_dict['position']
        if "uuid" in step_dict and step_dict['uuid'] != "None":
            step.uuid = step_dict["uuid"]
        if "label" in step_dict:
            step.label = step_dict["label"]

        step_type = step_dict.get("type", None)
        if step_type == "subworkflow":
            subworkflow = self.__load_subworkflow_from_step_dict(
                trans, step_dict
            )
            step_dict["subworkflow"] = subworkflow

        module = module_factory.from_dict( trans, step_dict, exact_tools=exact_tools )
        module.save_to_step( step )

        annotation = step_dict[ 'annotation' ]
        if annotation:
            annotation = sanitize_html( annotation, 'utf-8', 'text/html' )
            self.add_item_annotation( trans.sa_session, trans.get_user(), step, annotation )

        # Stick this in the step temporarily
        step.temp_input_connections = step_dict['input_connections']

        return module, step

    def __load_subworkflow_from_step_dict(self, trans, step_dict):
        embedded_subworkflow = step_dict.get("subworkflow", None)
        subworkflow_id = step_dict.get("content_id", None)
        if embedded_subworkflow and subworkflow_id:
            raise Exception("Subworkflow step defines both subworkflow and content_id, only one may be specified.")

        if not embedded_subworkflow and not subworkflow_id:
            raise Exception("Subworkflow step must define either subworkflow or content_id.")

        if embedded_subworkflow:
            subworkflow = self.build_workflow_from_dict(
                trans,
                embedded_subworkflow,
                create_stored_workflow=False,
            ).workflow
        else:
            workflow_manager = WorkflowsManager(self.app)
            subworkflow = workflow_manager.get_owned_workflow(
                trans, subworkflow_id
            )

        return subworkflow

    def __connect_workflow_steps( self, steps, steps_by_external_id ):
        """ Second pass to deal with connections between steps.

        Create workflow connection objects using externally specified ids
        using during creation or update.
        """
        for step in steps:
            # Input connections
            for input_name, conn_list in step.temp_input_connections.iteritems():
                if not conn_list:
                    continue
                if not isinstance(conn_list, list):  # Older style singleton connection
                    conn_list = [conn_list]
                for conn_dict in conn_list:
                    if 'output_name' not in conn_dict or 'id' not in conn_dict:
                        template = "Invalid connection [%s] - must be dict with output_name and id fields."
                        message = template % conn_dict
                        raise exceptions.MessageException(message)
                    conn = model.WorkflowStepConnection()
                    conn.input_step = step
                    conn.input_name = input_name
                    conn.output_name = conn_dict['output_name']
                    conn.output_step = steps_by_external_id[ conn_dict['id'] ]

                    input_subworkflow_step_index = conn_dict.get('input_subworkflow_step_id', None)
                    if input_subworkflow_step_index is not None:
                        conn.input_subworkflow_step = step.subworkflow.step_by_index(input_subworkflow_step_index)

            del step.temp_input_connections


class MissingToolsException(exceptions.MessageException):

    def __init__(self, workflow, errors):
        self.workflow = workflow
        self.errors = errors
