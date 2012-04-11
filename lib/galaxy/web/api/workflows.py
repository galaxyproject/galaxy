"""
API operations for Workflows
"""

import logging
from sqlalchemy import desc
from galaxy import util
from galaxy import web
from galaxy.tools.parameters import visit_input_values, DataToolParameter
from galaxy.web.base.controller import BaseAPIController, url_for
from galaxy.workflow.modules import module_factory
from galaxy.jobs.actions.post import ActionBox

log = logging.getLogger(__name__)

class WorkflowsAPIController(BaseAPIController):
    @web.expose_api
    def index(self, trans, **kwd):
        """
        GET /api/workflows

        Displays a collection of workflows.
        """
        rval = []
        for wf in trans.sa_session.query(trans.app.model.StoredWorkflow).filter_by(
                user=trans.user, deleted=False).order_by(
                desc(trans.app.model.StoredWorkflow.table.c.update_time)).all():
            item = wf.get_api_value(value_mapper={'id':trans.security.encode_id})
            encoded_id = trans.security.encode_id(wf.id)
            item['url'] = url_for('workflow', id=encoded_id)
            rval.append(item)
        for wf_sa in trans.sa_session.query( trans.app.model.StoredWorkflowUserShareAssociation ).filter_by(
                user=trans.user ).join( 'stored_workflow' ).filter(
                trans.app.model.StoredWorkflow.deleted == False ).order_by(
                desc( trans.app.model.StoredWorkflow.update_time ) ).all():
            item = wf_sa.stored_workflow.get_api_value(value_mapper={'id':trans.security.encode_id})
            encoded_id = trans.security.encode_id(wf_sa.stored_workflow.id)
            item['url'] = url_for('workflow', id=encoded_id)
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
            if stored_workflow.user != trans.user and not trans.user_is_admin():
                if trans.sa_session.query(trans.app.model.StoredWorkflowUserShareAssociation).filter_by(user=trans.user, stored_workflow=stored_workflow).count() == 0:
                    trans.response.status = 400
                    return("Workflow is not owned by or shared with current user")
        except:
            trans.response.status = 400
            return "That workflow does not exist."
        item = stored_workflow.get_api_value(view='element', value_mapper={'id':trans.security.encode_id})
        item['url'] = url_for('workflow', id=workflow_id)
        latest_workflow = stored_workflow.latest_workflow
        inputs = {}
        for step in latest_workflow.steps:
            if step.type == 'data_input':
                inputs[step.id] = {'label':step.tool_inputs['name'], 'value':""}
            else:
                pass
                # Eventually, allow regular tool parameters to be inserted and modified at runtime.
                # p = step.get_required_parameters()
        item['inputs'] = inputs
        return item

    @web.expose_api
    def create(self, trans, payload, **kwd):
        """
        POST /api/workflows

        We're not creating workflows from the api.  Just execute for now.

        However, we will import them if installed_repository_file is specified
        """
        if 'workflow_id' not in payload:
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
        stored_workflow = trans.sa_session.query(self.app.model.StoredWorkflow).get(
                        trans.security.decode_id(payload['workflow_id']))
        if stored_workflow.user != trans.user and not trans.user_is_admin():
            if trans.sa_session.query(trans.app.model.StoredWorkflowUserShareAssociation).filter_by(user=trans.user, stored_workflow=stored_workflow).count() == 0:
                trans.response.status = 400
                return("Workflow is not owned by or shared with current user")
        workflow = stored_workflow.latest_workflow
        if payload['history'].startswith('hist_id='):
            #Passing an existing history to use.
            history = trans.sa_session.query(self.app.model.History).get(
                    trans.security.decode_id(payload['history'][8:]))
            if history.user != trans.user and not trans.user_is_admin():
                trans.response.status = 400
                return "Invalid History specified."
        else:
            history = self.app.model.History(name=payload['history'], user=trans.user)
            trans.sa_session.add(history)
            trans.sa_session.flush()
        ds_map = payload['ds_map']
        add_to_history = 'no_add_to_history' not in payload
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
                    if add_to_history and  hda.history != history:
                        history.add_dataset(hda)
                else:
                    trans.response.status = 400
                    return "Unknown dataset source '%s' specified." % ds_map[k]['src']
                ds_map[k]['hda'] = hda
            except AssertionError:
                trans.response.status = 400
                return "Invalid Dataset '%s' Specified" % ds_map[k]['id']
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
            if step.type == 'tool' or step.type is None:
                step.module = module_factory.from_workflow_step( trans, step )
                # Check for missing parameters
                step.upgrade_messages = step.module.check_and_update_state()
                # Any connected input needs to have value DummyDataset (these
                # are not persisted so we need to do it every time)
                step.module.add_dummy_datasets( connections=step.input_connections )
                step.state = step.module.state
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
            step.input_connections_by_name = dict( ( conn.input_name, conn ) for conn in step.input_connections )
        # Run each step, connecting outputs to inputs
        workflow_invocation = self.app.model.WorkflowInvocation()
        workflow_invocation.workflow = workflow
        outputs = util.odict.odict()
        rval['history'] = trans.security.encode_id(history.id)
        rval['outputs'] = []
        for i, step in enumerate( workflow.steps ):
            job = None
            if step.type == 'tool' or step.type is None:
                tool = self.app.toolbox.get_tool( step.tool_id )
                def callback( input, value, prefixed_name, prefixed_label ):
                    if isinstance( input, DataToolParameter ):
                        if prefixed_name in step.input_connections_by_name:
                            conn = step.input_connections_by_name[ prefixed_name ]
                            return outputs[ conn.output_step.id ][ conn.output_name ]
                visit_input_values( tool.inputs, step.state.inputs, callback )
                job, out_data = tool.execute( trans, step.state.inputs, history=history)
                outputs[ step.id ] = out_data
                for pja in step.post_job_actions:
                    if pja.action_type in ActionBox.immediate_actions:
                        ActionBox.execute(self.app, trans.sa_session, pja, job, replacement_dict=None)
                    else:
                        job.add_post_job_action(pja)
                for v in out_data.itervalues():
                    rval['outputs'].append(trans.security.encode_id(v.id))
            else:
                #This is an input step.  Use the dataset inputs from ds_map.
                job, out_data = step.module.execute( trans, step.state)
                outputs[step.id] = out_data
                outputs[step.id]['output'] = ds_map[str(step.id)]['hda']
            workflow_invocation_step = self.app.model.WorkflowInvocationStep()
            workflow_invocation_step.workflow_invocation = workflow_invocation
            workflow_invocation_step.workflow_step = step
            workflow_invocation_step.job = job
        trans.sa_session.add( workflow_invocation )
        trans.sa_session.flush()
        return rval

