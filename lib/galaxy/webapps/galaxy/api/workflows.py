from __future__ import absolute_import

"""
API operations for Workflows
"""

import logging
from sqlalchemy import desc, or_
from galaxy import exceptions
from galaxy import util
from galaxy import web
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController, url_for, UsesStoredWorkflowMixin
from galaxy.workflow.modules import module_factory
from galaxy.workflow.run import invoke


log = logging.getLogger(__name__)


def _update_step_parameters(step, param_map):
    """
    Update ``step`` parameters based on the user-provided ``param_map`` dict.

    ``param_map`` should be structured as follows::

      PARAM_MAP = {STEP_ID: PARAM_DICT, ...}
      PARAM_DICT = {NAME: VALUE, ...}

    For backwards compatibility, the following (deprecated) format is
    also supported for ``param_map``::

      PARAM_MAP = {TOOL_ID: PARAM_DICT, ...}

    in which case PARAM_DICT affects all steps with the given tool id.
    If both by-tool-id and by-step-id specifications are used, the
    latter takes precedence.

    Finally (again, for backwards compatibility), PARAM_DICT can also
    be specified as::

      PARAM_DICT = {'param': NAME, 'value': VALUE}

    Note that this format allows only one parameter to be set per step.
    """
    param_dict = param_map.get(step.tool_id, {}).copy()
    param_dict.update(param_map.get(str(step.id), {}))
    if param_dict:
        if 'param' in param_dict and 'value' in param_dict:
            param_dict[param_dict['param']] = param_dict['value']
        step.state.inputs.update(param_dict)


class WorkflowsAPIController(BaseAPIController, UsesStoredWorkflowMixin):

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
            rval.append(item)
        for wf_sa in trans.sa_session.query( trans.app.model.StoredWorkflowUserShareAssociation ).filter_by(
                user=trans.user ).join( 'stored_workflow' ).filter(
                trans.app.model.StoredWorkflow.deleted == False ).order_by(
                desc( trans.app.model.StoredWorkflow.update_time ) ).all():
            item = wf_sa.stored_workflow.to_dict( value_mapper={ 'id': trans.security.encode_id  })
            encoded_id = trans.security.encode_id(wf_sa.stored_workflow.id)
            item['url'] = url_for( 'workflow', id=encoded_id )
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

        We're not creating workflows from the api.  Just execute for now.

        However, we will import them if installed_repository_file is specified
        """

        # Pull parameters out of payload.
        workflow_id = payload['workflow_id']
        param_map = payload.get('parameters', {})
        ds_map = payload['ds_map']
        add_to_history = 'no_add_to_history' not in payload
        history_param = payload['history']

        # Get/create workflow.
        if not workflow_id:
            # create new
            if 'installed_repository_file' in payload:
                workflow_controller = trans.webapp.controllers[ 'workflow' ]
                result = workflow_controller.import_workflow( trans=trans,
                                                              cntrller='api',
                                                              **payload)
                return result
            trans.response.status = 403
            return "Either workflow_id or installed_repository_file must be specified"
        if 'installed_repository_file' in payload:
            trans.response.status = 403
            return "installed_repository_file may not be specified with workflow_id"

        # Get workflow + accessibility check.
        stored_workflow = trans.sa_session.query(self.app.model.StoredWorkflow).get(
                        trans.security.decode_id(workflow_id))
        if stored_workflow.user != trans.user and not trans.user_is_admin():
            if trans.sa_session.query(trans.app.model.StoredWorkflowUserShareAssociation).filter_by(user=trans.user, stored_workflow=stored_workflow).count() == 0:
                trans.response.status = 400
                return("Workflow is not owned by or shared with current user")
        workflow = stored_workflow.latest_workflow

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
                if add_to_history and  hda.history != history:
                    hda = hda.copy()
                    history.add_dataset(hda)
                ds_map[k]['hda'] = hda
            except AssertionError:
                trans.response.status = 400
                return "Invalid Dataset '%s' Specified" % ds_map[k]['id']

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

        # Build the state for each step
        rval = {}
        for step in workflow.steps:
            step_errors = None
            input_connections_by_name = {}
            for conn in step.input_connections:
                input_name = conn.input_name
                if not input_name in input_connections_by_name:
                    input_connections_by_name[input_name] = []
                input_connections_by_name[input_name].append(conn)
            step.input_connections_by_name = input_connections_by_name

            if step.type == 'tool' or step.type is None:
                step.module = module_factory.from_workflow_step( trans, step )
                # Check for missing parameters
                step.upgrade_messages = step.module.check_and_update_state()
                # Any connected input needs to have value DummyDataset (these
                # are not persisted so we need to do it every time)
                step.module.add_dummy_datasets( connections=step.input_connections )
                step.state = step.module.state
                _update_step_parameters(step, param_map)
                if step.tool_errors:
                    trans.response.status = 400
                    return "Workflow cannot be run because of validation errors in some steps: %s" % step_errors
                if step.upgrade_messages:
                    trans.response.status = 400
                    return "Workflow cannot be run because of step upgrade messages: %s" % step.upgrade_messages
            else:
                # This is an input step.  Make sure we have an available input.
                if step.type == 'data_input' and str(step.id) not in ds_map:
                    trans.response.status = 400
                    return "Workflow cannot be run because an expected input step '%s' has no input dataset." % step.id
                step.module = module_factory.from_workflow_step( trans, step )
                step.state = step.module.get_runtime_state()

        # Run each step, connecting outputs to inputs
        outputs = util.odict.odict()
        rval['history'] = trans.security.encode_id(history.id)
        rval['outputs'] = []

        replacement_dict = payload.get('replacement_params', {})

        outputs = invoke(
            trans=trans,
            workflow=workflow,
            target_history=history,
            replacement_dict=replacement_dict,
            ds_map=ds_map,
        )
        trans.sa_session.flush()

        # Build legacy output - should probably include more information from
        # outputs.
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
        if workflow_id == None:
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
