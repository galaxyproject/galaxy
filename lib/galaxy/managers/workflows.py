from galaxy import model
from galaxy import exceptions
from galaxy.workflow import modules


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
