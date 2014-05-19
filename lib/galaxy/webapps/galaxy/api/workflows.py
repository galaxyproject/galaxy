"""
API operations for Workflows
"""

from __future__ import absolute_import

import logging
from sqlalchemy import desc, or_
from galaxy import exceptions
from galaxy import util
from galaxy import web
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController, url_for, UsesStoredWorkflowMixin
from galaxy.web.base.controller import UsesHistoryMixin
from galaxy.workflow.run import invoke
from galaxy.workflow.run import WorkflowRunConfig
from galaxy.workflow.extract import extract_workflow


log = logging.getLogger(__name__)


class WorkflowsAPIController(BaseAPIController, UsesStoredWorkflowMixin, UsesHistoryMixin):

    @web.expose_api
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
            filter1 = or_( filter1, ( trans.app.model.StoredWorkflow.published == True ) )
        for wf in trans.sa_session.query( trans.app.model.StoredWorkflow ).filter(
                filter1, trans.app.model.StoredWorkflow.table.c.deleted == False ).order_by(
                desc( trans.app.model.StoredWorkflow.table.c.update_time ) ).all():
            item = wf.to_dict( value_mapper={ 'id': trans.security.encode_id } )
            encoded_id = trans.security.encode_id(wf.id)
            item['url'] = url_for('workflow', id=encoded_id)
            item['owner'] = wf.user.username
            rval.append(item)
        for wf_sa in trans.sa_session.query( trans.app.model.StoredWorkflowUserShareAssociation ).filter_by(
                user=trans.user ).join( 'stored_workflow' ).filter(
                trans.app.model.StoredWorkflow.deleted == False ).order_by(
                desc( trans.app.model.StoredWorkflow.update_time ) ).all():
            item = wf_sa.stored_workflow.to_dict( value_mapper={ 'id': trans.security.encode_id } )
            encoded_id = trans.security.encode_id(wf_sa.stored_workflow.id)
            item['url'] = url_for( 'workflow', id=encoded_id )
            item['owner'] = wf_sa.stored_workflow.user.username
            rval.append(item)
        return rval

    @web.expose_api
    def show(self, trans, id, **kwd):
        """
        GET /api/workflows/{encoded_workflow_id}

        Displays information needed to run a workflow from the command line.
        """
        workflow_id = id
        try:
            decoded_workflow_id = trans.security.decode_id(workflow_id)
        except TypeError:
            trans.response.status = 400
            return "Malformed workflow id ( %s ) specified, unable to decode." % str(workflow_id)
        try:
            stored_workflow = trans.sa_session.query(trans.app.model.StoredWorkflow).get(decoded_workflow_id)
            if stored_workflow.importable == False and stored_workflow.user != trans.user and not trans.user_is_admin():
                if trans.sa_session.query(trans.app.model.StoredWorkflowUserShareAssociation).filter_by(user=trans.user, stored_workflow=stored_workflow).count() == 0:
                    trans.response.status = 400
                    return("Workflow is neither importable, nor owned by or shared with current user")
        except:
            trans.response.status = 400
            return "That workflow does not exist."
        item = stored_workflow.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id } )
        item['url'] = url_for('workflow', id=workflow_id)
        item['owner'] = stored_workflow.user.username
        latest_workflow = stored_workflow.latest_workflow
        inputs = {}
        for step in latest_workflow.steps:
            if step.type == 'data_input':
                if step.tool_inputs and "name" in step.tool_inputs:
                    inputs[step.id] = {'label': step.tool_inputs['name'], 'value': ""}
                else:
                    inputs[step.id] = {'label': "Input Dataset", 'value': ""}
            else:
                pass
                # Eventually, allow regular tool parameters to be inserted and modified at runtime.
                # p = step.get_required_parameters()
        item['inputs'] = inputs
        steps = {}
        for step in latest_workflow.steps:
            steps[step.id] = {'id': step.id,
                              'type': step.type,
                              'tool_id': step.tool_id,
                              'tool_version': step.tool_version,
                              'tool_inputs': step.tool_inputs,
                              'input_steps': {}}
            for conn in step.input_connections:
                steps[step.id]['input_steps'][conn.input_name] = {'source_step': conn.output_step_id,
                                                                  'step_output': conn.output_name}
        item['steps'] = steps
        return item

    @web.expose_api
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

        if len( set( ['workflow_id', 'installed_repository_file', 'from_history_id'] ).intersection( payload ) ) > 1:
            trans.response.status = 403
            return "Only one among 'workflow_id', 'installed_repository_file', 'from_history_id' must be specified"

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

        workflow_id = payload.get( 'workflow_id', None )
        if not workflow_id:
            trans.response.status = 403
            return "Either workflow_id, installed_repository_file or from_history_id must be specified"

        # Pull other parameters out of payload.
        param_map = payload.get( 'parameters', {} )
        ds_map = payload.get( 'ds_map', {} )
        add_to_history = 'no_add_to_history' not in payload
        history_param = payload.get('history', '')

        # Get workflow + accessibility check.
        stored_workflow = trans.sa_session.query(self.app.model.StoredWorkflow).get(
                        trans.security.decode_id(workflow_id))
        if stored_workflow.user != trans.user and not trans.user_is_admin():
            if trans.sa_session.query(trans.app.model.StoredWorkflowUserShareAssociation).filter_by(user=trans.user, stored_workflow=stored_workflow).count() == 0:
                trans.response.status = 400
                return("Workflow is not owned by or shared with current user")
        workflow = stored_workflow.latest_workflow

        # Sanity checks.
        if not workflow:
            trans.response.status = 400
            return "Workflow not found."
        if len( workflow.steps ) == 0:
            trans.response.status = 400
            return "Workflow cannot be run because it does not have any steps"
        if workflow.has_cycles:
            trans.response.status = 400
            return "Workflow cannot be run because it contains cycles"
        if workflow.has_errors:
            trans.response.status = 400
            return "Workflow cannot be run because of validation errors in some steps"

        # Get target history.
        if history_param.startswith('hist_id='):
            #Passing an existing history to use.
            history = trans.sa_session.query(self.app.model.History).get(
                    trans.security.decode_id(history_param[8:]))
            if history.user != trans.user and not trans.user_is_admin():
                trans.response.status = 400
                return "Invalid History specified."
        else:
            # Send workflow outputs to new history.
            history = self.app.model.History(name=history_param, user=trans.user)
            trans.sa_session.add(history)
            trans.sa_session.flush()

        # Set workflow inputs.
        for k in ds_map:
            try:
                if ds_map[k]['src'] == 'ldda':
                    ldda = trans.sa_session.query(self.app.model.LibraryDatasetDatasetAssociation).get(
                            trans.security.decode_id(ds_map[k]['id']))
                    assert trans.user_is_admin() or trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), ldda.dataset )
                    hda = ldda.to_history_dataset_association(history, add_to_history=add_to_history)
                elif ds_map[k]['src'] == 'ld':
                    ldda = trans.sa_session.query(self.app.model.LibraryDataset).get(
                            trans.security.decode_id(ds_map[k]['id'])).library_dataset_dataset_association
                    assert trans.user_is_admin() or trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), ldda.dataset )
                    hda = ldda.to_history_dataset_association(history, add_to_history=add_to_history)
                elif ds_map[k]['src'] == 'hda':
                    # Get dataset handle, add to dict and history if necessary
                    hda = trans.sa_session.query(self.app.model.HistoryDatasetAssociation).get(
                            trans.security.decode_id(ds_map[k]['id']))
                    assert trans.user_is_admin() or trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), hda.dataset )
                else:
                    trans.response.status = 400
                    return "Unknown dataset source '%s' specified." % ds_map[k]['src']
                if add_to_history and hda.history != history:
                    hda = hda.copy()
                    history.add_dataset(hda)
                ds_map[k]['hda'] = hda
            except AssertionError:
                trans.response.status = 400
                return "Invalid Dataset '%s' Specified" % ds_map[k]['id']

        # Run each step, connecting outputs to inputs
        replacement_dict = payload.get('replacement_params', {})

        run_config = WorkflowRunConfig(
            target_history=history,
            replacement_dict=replacement_dict,
            ds_map=ds_map,
            param_map=param_map,
        )

        outputs = invoke(
            trans=trans,
            workflow=workflow,
            workflow_run_config=run_config,
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

    @web.expose_api
    def workflow_dict( self, trans, workflow_id, **kwd ):
        """
        GET /api/workflows/{encoded_workflow_id}/download
        Returns a selected workflow as a json dictionary.
        """
        try:
            stored_workflow = trans.sa_session.query(self.app.model.StoredWorkflow).get(trans.security.decode_id(workflow_id))
        except Exception, e:
            return ("Workflow with ID='%s' can not be found\n Exception: %s") % (workflow_id, str( e ))
        # check to see if user has permissions to selected workflow
        if stored_workflow.user != trans.user and not trans.user_is_admin():
            if trans.sa_session.query(trans.app.model.StoredWorkflowUserShareAssociation).filter_by(user=trans.user, stored_workflow=stored_workflow).count() == 0:
                trans.response.status = 400
                return("Workflow is not owned by or shared with current user")

        ret_dict = self._workflow_to_dict( trans, stored_workflow )
        if not ret_dict:
            #This workflow has a tool that's missing from the distribution
            trans.response.status = 400
            return "Workflow cannot be exported due to missing tools."
        return ret_dict

    @web.expose_api
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

        #Mark a workflow as deleted
        stored_workflow.deleted = True
        trans.sa_session.flush()

        # TODO: Unsure of response message to let api know that a workflow was successfully deleted
        #return 'OK'
        return ( "Workflow '%s' successfully deleted" % stored_workflow.name )

    @web.expose_api
    def import_new_workflow(self, trans, payload, **kwd):
        """
        POST /api/workflows/upload
        Importing dynamic workflows from the api. Return newly generated workflow id.
        Author: rpark

        # currently assumes payload['workflow'] is a json representation of a workflow to be inserted into the database
        """

        data = payload['workflow']

        workflow, missing_tool_tups = self._workflow_from_dict( trans, data, source="API" )

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
    def import_shared_workflow(self, trans, payload, **kwd):
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
        try:
            stored_workflow = self.get_stored_workflow( trans, workflow_id, check_ownership=False )
        except:
            raise exceptions.ObjectNotFound( "Malformed workflow id ( %s ) specified." % workflow_id )
        if stored_workflow.importable == False:
            raise exceptions.MessageException( 'The owner of this workflow has disabled imports via this link.' )
        elif stored_workflow.deleted:
            raise exceptions.MessageException( "You can't import this workflow because it has been deleted." )
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
        try:
            stored_workflow = trans.sa_session.query(self.app.model.StoredWorkflow).get(trans.security.decode_id(workflow_id))
        except Exception, e:
            raise exceptions.ObjectNotFound()
        # check to see if user has permissions to selected workflow
        if stored_workflow.user != trans.user and not trans.user_is_admin():
            if trans.sa_session.query(trans.app.model.StoredWorkflowUserShareAssociation).filter_by(user=trans.user, stored_workflow=stored_workflow).count() == 0:
                raise exceptions.ItemOwnershipException()
        results = trans.sa_session.query(self.app.model.WorkflowInvocation).filter(self.app.model.WorkflowInvocation.workflow_id==stored_workflow.latest_workflow_id)
        out = []
        for r in results:
            out.append( self.encode_all_ids( trans, r.to_dict(), True) )
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

        try:
            stored_workflow = trans.sa_session.query(self.app.model.StoredWorkflow).get(trans.security.decode_id(workflow_id))
        except Exception, e:
            raise exceptions.ObjectNotFound()
        # check to see if user has permissions to selected workflow
        if stored_workflow.user != trans.user and not trans.user_is_admin():
            if trans.sa_session.query(trans.app.model.StoredWorkflowUserShareAssociation).filter_by(user=trans.user, stored_workflow=stored_workflow).count() == 0:
                raise exceptions.ItemOwnershipException()
        results = trans.sa_session.query(self.app.model.WorkflowInvocation).filter(self.app.model.WorkflowInvocation.workflow_id==stored_workflow.latest_workflow_id)
        results = results.filter(self.app.model.WorkflowInvocation.id == trans.security.decode_id(usage_id))
        out = results.first()
        if out is not None:
            return self.encode_all_ids( trans, out.to_dict('element'), True)
        return None
