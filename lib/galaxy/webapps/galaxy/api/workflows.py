"""
API operations for Workflows
"""

from __future__ import absolute_import

import uuid
import logging
from sqlalchemy import desc, or_, and_
from galaxy import exceptions, util
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.managers import histories
from galaxy.managers import workflows
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController, url_for, UsesStoredWorkflowMixin
from galaxy.web.base.controller import UsesHistoryMixin
from galaxy.web.base.controller import SharableMixin
from galaxy.workflow.extract import extract_workflow
from galaxy.workflow.run import invoke
from galaxy.workflow.run_request import build_workflow_run_config

log = logging.getLogger(__name__)


class WorkflowsAPIController(BaseAPIController, UsesStoredWorkflowMixin, UsesHistoryMixin, UsesAnnotations, SharableMixin):

    def __init__( self, app ):
        super( BaseAPIController, self ).__init__( app )
        self.history_manager = histories.HistoryManager()
        self.workflow_manager = workflows.WorkflowsManager( app )

    @expose_api
    def index(self, trans, **kwd):
        """
        GET /api/workflows

        Displays a collection of workflows.

        :param  show_published:      if True, show also published workflows
        :type   show_published:      boolean
        """
        show_published = util.string_as_bool( kwd.get( 'show_published', 'False' ) )
        rval = []
        filter1 = ( trans.app.model.StoredWorkflow.user == trans.user )
        if show_published:
            filter1 = or_( filter1, ( trans.app.model.StoredWorkflow.published == True ) ) #noqa -- sqlalchemy comparison
        for wf in trans.sa_session.query( trans.app.model.StoredWorkflow ).filter(
                filter1, trans.app.model.StoredWorkflow.table.c.deleted == False ).order_by( #noqa -- sqlalchemy comparison
                desc( trans.app.model.StoredWorkflow.table.c.update_time ) ).all():
            item = wf.to_dict( value_mapper={ 'id': trans.security.encode_id } )
            encoded_id = trans.security.encode_id(wf.id)
            item['url'] = url_for('workflow', id=encoded_id)
            item['owner'] = wf.user.username
            rval.append(item)
        for wf_sa in trans.sa_session.query( trans.app.model.StoredWorkflowUserShareAssociation ).filter_by(
                user=trans.user ).join( 'stored_workflow' ).filter(
                trans.app.model.StoredWorkflow.deleted == False ).order_by( #noqa -- sqlalchemy comparison
                desc( trans.app.model.StoredWorkflow.update_time ) ).all():
            item = wf_sa.stored_workflow.to_dict( value_mapper={ 'id': trans.security.encode_id } )
            encoded_id = trans.security.encode_id(wf_sa.stored_workflow.id)
            item['url'] = url_for( 'workflow', id=encoded_id )
            item['owner'] = wf_sa.stored_workflow.user.username
            rval.append(item)
        return rval

    @expose_api
    def show(self, trans, id, **kwd):
        """
        GET /api/workflows/{encoded_workflow_id}

        Displays information needed to run a workflow from the command line.
        """
        stored_workflow = self.__get_stored_workflow( trans, id )
        if stored_workflow.importable is False and stored_workflow.user != trans.user and not trans.user_is_admin():
            if trans.sa_session.query(trans.app.model.StoredWorkflowUserShareAssociation).filter_by(user=trans.user, stored_workflow=stored_workflow).count() == 0:
                message = "Workflow is neither importable, nor owned by or shared with current user"
                raise exceptions.ItemAccessibilityException( message )

        item = stored_workflow.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id } )
        item['url'] = url_for('workflow', id=id)
        item['owner'] = stored_workflow.user.username
        latest_workflow = stored_workflow.latest_workflow
        inputs = {}
        for step in latest_workflow.steps:
            step_type = step.type
            if step_type in ['data_input', 'data_collection_input']:
                if step.tool_inputs and "name" in step.tool_inputs:
                    label = step.tool_inputs['name']
                elif step_type == "data_input":
                    label = "Input Dataset"
                elif step_type == "data_collection_input":
                    label = "Input Dataset Collection"
                else:
                    raise ValueError("Invalid step_type %s" % step_type)
                inputs[step.id] = {'label': label, 'value': ""}
            else:
                pass
                # Eventually, allow regular tool parameters to be inserted and modified at runtime.
                # p = step.get_required_parameters()
        item['inputs'] = inputs
        item['annotation'] = self.get_item_annotation_str( trans.sa_session, stored_workflow.user, stored_workflow )
        steps = {}
        for step in latest_workflow.steps:
            steps[step.id] = {'id': step.id,
                              'type': step.type,
                              'tool_id': step.tool_id,
                              'tool_version': step.tool_version,
                              'annotation': self.get_item_annotation_str( trans.sa_session, stored_workflow.user, step ),
                              'tool_inputs': step.tool_inputs,
                              'input_steps': {}}
            for conn in step.input_connections:
                steps[step.id]['input_steps'][conn.input_name] = {'source_step': conn.output_step_id,
                                                                  'step_output': conn.output_name}
        item['steps'] = steps
        return item

    @expose_api
    def create(self, trans, payload, **kwd):
        """
        POST /api/workflows

        Run or create workflows from the api.

        If installed_repository_file or from_history_id is specified a new
        workflow will be created for this user. Otherwise, workflow_id must be
        specified and this API method will cause a workflow to execute.

        :param  installed_repository_file    The path of a workflow to import. Either workflow_id, installed_repository_file or from_history_id must be specified
        :type   installed_repository_file    str

        :param  workflow_id:                 An existing workflow id. Either workflow_id, installed_repository_file or from_history_id must be specified
        :type   workflow_id:                 str

        :param  parameters:                  If workflow_id is set - see _update_step_parameters()
        :type   parameters:                  dict

        :param  ds_map:                      If workflow_id is set - a dictionary mapping each input step id to a dictionary with 2 keys: 'src' (which can be 'ldda', 'ld' or 'hda') and 'id' (which should be the id of a LibraryDatasetDatasetAssociation, LibraryDataset or HistoryDatasetAssociation respectively)
        :type   ds_map:                      dict

        :param  no_add_to_history:           If workflow_id is set - if present in the payload with any value, the input datasets will not be added to the selected history
        :type   no_add_to_history:           str

        :param  history:                     If workflow_id is set - optional history where to run the workflow, either the name of a new history or "hist_id=HIST_ID" where HIST_ID is the id of an existing history. If not specified, the workflow will be run a new unnamed history
        :type   history:                     str

        :param  replacement_params:          If workflow_id is set - an optional dictionary used when renaming datasets
        :type   replacement_params:          dict

        :param  from_history_id:             Id of history to extract a workflow from. Either workflow_id, installed_repository_file or from_history_id must be specified
        :type   from_history_id:             str

        :param  job_ids:                     If from_history_id is set - optional list of jobs to include when extracting a workflow from history
        :type   job_ids:                     str

        :param  dataset_ids:                 If from_history_id is set - optional list of HDA `hid`s corresponding to workflow inputs when extracting a workflow from history
        :type   dataset_ids:                 str

        :param  dataset_collection_ids:      If from_history_id is set - optional list of HDCA `hid`s corresponding to workflow inputs when extracting a workflow from history
        :type   dataset_collection_ids:      str

        :param  workflow_name:               If from_history_id is set - name of the workflow to create when extracting a workflow from history
        :type   workflow_name:               str
        """
        ways_to_create = set( [
            'workflow_id',
            'installed_repository_file',
            'from_history_id',
            'shared_workflow_id',
            'workflow',
        ] ).intersection( payload )
        if len( ways_to_create ) == 0:
            message = "One parameter among - %s - must be specified" % ", ".join( ways_to_create )
            raise exceptions.RequestParameterMissingException( message )

        if len( ways_to_create ) > 1:
            message = "Only one parameter among - %s - must be specified" % ", ".join( ways_to_create )
            raise exceptions.RequestParameterInvalidException( message )

        if 'installed_repository_file' in payload:
            workflow_controller = trans.webapp.controllers[ 'workflow' ]
            result = workflow_controller.import_workflow( trans=trans,
                                                          cntrller='api',
                                                          **payload)
            return result

        if 'from_history_id' in payload:
            from_history_id = payload.get( 'from_history_id' )
            history = self.get_history( trans, from_history_id, check_ownership=False, check_accessible=True )
            job_ids = map( trans.security.decode_id, payload.get( 'job_ids', [] ) )
            dataset_ids = payload.get( 'dataset_ids', [] )
            dataset_collection_ids = payload.get( 'dataset_collection_ids', [] )
            workflow_name = payload[ 'workflow_name' ]
            stored_workflow = extract_workflow(
                trans=trans,
                user=trans.get_user(),
                history=history,
                job_ids=job_ids,
                dataset_ids=dataset_ids,
                dataset_collection_ids=dataset_collection_ids,
                workflow_name=workflow_name,
            )
            item = stored_workflow.to_dict( value_mapper={ 'id': trans.security.encode_id } )
            item[ 'url' ] = url_for( 'workflow', id=item[ 'id' ] )
            return item

        if 'shared_workflow_id' in payload:
            workflow_id = payload[ 'shared_workflow_id' ]
            return self.__api_import_shared_workflow( trans, workflow_id, payload )

        if 'workflow' in payload:
            return self.__api_import_new_workflow( trans, payload, **kwd )

        workflow_id = payload.get( 'workflow_id', None )
        if not workflow_id:
            message = "Invalid workflow_id specified."
            raise exceptions.RequestParameterInvalidException( message )

        # Get workflow + accessibility check.
        stored_workflow = self.__get_stored_accessible_workflow( trans, workflow_id )
        workflow = stored_workflow.latest_workflow

        run_config = build_workflow_run_config( trans, workflow, payload )
        history = run_config.target_history

        # invoke may throw MessageExceptions on tool erors, failure
        # to match up inputs, etc...
        outputs = invoke(
            trans=trans,
            workflow=workflow,
            workflow_run_config=run_config,
            populate_state=True,
        )
        trans.sa_session.flush()

        # Build legacy output - should probably include more information from
        # outputs.
        rval = {}
        rval['history'] = trans.security.encode_id(history.id)
        rval['outputs'] = []
        for step in workflow.steps:
            if step.type == 'tool' or step.type is None:
                for v in outputs[ step.id ].itervalues():
                    rval[ 'outputs' ].append( trans.security.encode_id( v.id ) )

        return rval

    @expose_api
    def workflow_dict( self, trans, workflow_id, **kwd ):
        """
        GET /api/workflows/{encoded_workflow_id}/download
        Returns a selected workflow as a json dictionary.
        """
        stored_workflow = self.__get_stored_accessible_workflow( trans, workflow_id )

        ret_dict = self._workflow_to_dict( trans, stored_workflow )
        if not ret_dict:
            # This workflow has a tool that's missing from the distribution
            message = "Workflow cannot be exported due to missing tools."
            raise exceptions.MessageException( message )
        return ret_dict

    @expose_api
    def delete( self, trans, id, **kwd ):
        """
        DELETE /api/workflows/{encoded_workflow_id}
        Deletes a specified workflow
        Author: rpark

        copied from galaxy.web.controllers.workflows.py (delete)
        """
        workflow_id = id

        try:
            stored_workflow = trans.sa_session.query(self.app.model.StoredWorkflow).get(trans.security.decode_id(workflow_id))
        except Exception, e:
            trans.response.status = 400
            return ("Workflow with ID='%s' can not be found\n Exception: %s") % (workflow_id, str( e ))

        # check to see if user has permissions to selected workflow
        if stored_workflow.user != trans.user and not trans.user_is_admin():
            trans.response.status = 403
            return("Workflow is not owned by current user")

        # Mark a workflow as deleted
        stored_workflow.deleted = True
        trans.sa_session.flush()

        # TODO: Unsure of response message to let api know that a workflow was successfully deleted
        return ( "Workflow '%s' successfully deleted" % stored_workflow.name )

    @expose_api
    def import_new_workflow_deprecated(self, trans, payload, **kwd):
        """
        POST /api/workflows/upload
        Importing dynamic workflows from the api. Return newly generated workflow id.
        Author: rpark

        # currently assumes payload['workflow'] is a json representation of a workflow to be inserted into the database

        Deprecated in favor to POST /api/workflows with encoded 'workflow' in
        payload the same way.
        """
        return self.__api_import_new_workflow( trans, payload, **kwd )

    def __api_import_new_workflow( self, trans, payload, **kwd ):
        data = payload['workflow']

        publish = util.string_as_bool( payload.get( "publish", False ) )
        # If 'publish' set, default to importable.
        importable = util.string_as_bool( payload.get( "importable", publish ) )

        if publish and not importable:
            raise exceptions.RequestParameterInvalidException( "Published workflow must be importable." )

        from_dict_kwds = dict(
            source="API",
            publish=publish,
        )
        workflow, missing_tool_tups = self._workflow_from_dict( trans, data, **from_dict_kwds )

        if importable:
            self._make_item_accessible( trans.sa_session, workflow )
            trans.sa_session.flush()

        # galaxy workflow newly created id
        workflow_id = workflow.id
        # api encoded, id
        encoded_id = trans.security.encode_id(workflow_id)

        # return list
        rval = []

        item = workflow.to_dict(value_mapper={'id': trans.security.encode_id})
        item['url'] = url_for('workflow', id=encoded_id)

        rval.append(item)

        return item

    @expose_api
    def import_shared_workflow_deprecated(self, trans, payload, **kwd):
        """
        POST /api/workflows/import
        Import a workflow shared by other users.

        :param  workflow_id:      the workflow id (required)
        :type   workflow_id:      str

        :raises: exceptions.MessageException, exceptions.ObjectNotFound
        """
        # Pull parameters out of payload.
        workflow_id = payload.get('workflow_id', None)
        if workflow_id is None:
            raise exceptions.ObjectAttributeMissingException( "Missing required parameter 'workflow_id'." )
        self.__api_import_shared_workflow( trans, workflow_id, payload )

    def __api_import_shared_workflow( self, trans, workflow_id, payload, **kwd ):
        try:
            stored_workflow = self.get_stored_workflow( trans, workflow_id, check_ownership=False )
        except:
            raise exceptions.ObjectNotFound( "Malformed workflow id ( %s ) specified." % workflow_id )
        if stored_workflow.importable is False:
            raise exceptions.ItemAccessibilityException( 'The owner of this workflow has disabled imports via this link.' )
        elif stored_workflow.deleted:
            raise exceptions.ItemDeletionException( "You can't import this workflow because it has been deleted." )
        imported_workflow = self._import_shared_workflow( trans, stored_workflow )
        item = imported_workflow.to_dict( value_mapper={ 'id': trans.security.encode_id } )
        encoded_id = trans.security.encode_id(imported_workflow.id)
        item['url'] = url_for('workflow', id=encoded_id)
        return item

    @expose_api
    def workflow_usage(self, trans, workflow_id, **kwd):
        """
        GET /api/workflows/{workflow_id}/usage
        Get the list of the workflow usage

        :param  workflow_id:      the workflow id (required)
        :type   workflow_id:      str

        :raises: exceptions.MessageException, exceptions.ObjectNotFound
        """
        decoded_stored_workflow_invocation_id = self.__decode_id( trans, workflow_id )
        results = self.workflow_manager.build_invocations_query( trans, decoded_stored_workflow_invocation_id )
        out = []
        for r in results:
            out.append( self.__encode_invocation( trans, r ) )
        return out

    @expose_api
    def workflow_usage_contents(self, trans, workflow_id, usage_id, **kwd):
        """
        GET /api/workflows/{workflow_id}/usage/{usage_id}
        Get detailed description of workflow usage

        :param  workflow_id:      the workflow id (required)
        :type   workflow_id:      str

        :param  usage_id:      the usage id (required)
        :type   usage_id:      str

        :raises: exceptions.MessageException, exceptions.ObjectNotFound
        """
        decoded_workflow_invocation_id = self.__decode_id( trans, usage_id )
        workflow_invocation = self.workflow_manager.get_invocation( trans, decoded_workflow_invocation_id )
        if workflow_invocation:
            return self.__encode_invocation( trans, workflow_invocation )
        return None

    def __get_stored_accessible_workflow( self, trans, workflow_id ):
        stored_workflow = self.__get_stored_workflow( trans, workflow_id )

        # check to see if user has permissions to selected workflow
        if stored_workflow.user != trans.user and not trans.user_is_admin():
            if trans.sa_session.query(trans.app.model.StoredWorkflowUserShareAssociation).filter_by(user=trans.user, stored_workflow=stored_workflow).count() == 0:
                message = "Workflow is not owned by or shared with current user"
                raise exceptions.ItemAccessibilityException( message )

        return stored_workflow

    def __get_stored_workflow( self, trans, workflow_id ):
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
            workflow_id = self.__decode_id( trans, workflow_id )
            query = trans.sa_session.query( trans.app.model.StoredWorkflow )
            stored_workflow = query.get( workflow_id )
        if stored_workflow is None:
            raise exceptions.ObjectNotFound( "No such workflow found." )
        return stored_workflow

    def __encode_invocation( self, trans, invocation, view="element" ):
        return self.encode_all_ids(
            trans,
            invocation.to_dict( view ),
            True
        )

    def __decode_id( self, trans, workflow_id, model_type="workflow" ):
        try:
            return trans.security.decode_id( workflow_id )
        except Exception:
            message = "Malformed %s id ( %s ) specified, unable to decode" % ( model_type, workflow_id )
            raise exceptions.MalformedId( message )
