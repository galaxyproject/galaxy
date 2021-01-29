from galaxy import model
from galaxy.security.idencoding import IdEncodingHelper

from .unittest_utils.galaxy_mock import MockApp

from galaxy.schema.database_models import (
    WorkflowInvocationInDb,
    WorkflowInvocation,
    WorkflowInvocationElementInDb,
)
from galaxy.schema.fields import (
    DatabaseIdField,
    EncodedDatabaseIdField,
)

ID_SECRET = 'abcdefg'

def _get_invocation():
    app = MockApp()
    model.set_id_encoding_helper(IdEncodingHelper(id_secret=ID_SECRET))
    sa_session = app.model.context
    invocation = model.WorkflowInvocation()
    invocation_step = model.WorkflowInvocationStep()
    job = model.Job()
    invocation_step.job = job
    invocation_step.workflow_id = 1
    invocation_step.workflow_step_id = 1
    invocation.steps.append(invocation_step)
    history = model.History()
    workflow = model.Workflow()
    invocation.history = history
    invocation.workflow = workflow
    invocation.state = 'new'
    sa_session.add(invocation)
    sa_session.flush()
    return invocation


def test_workflow_invocation_model():
    invocation = _get_invocation()
    invocation_model = WorkflowInvocationInDb.from_orm(invocation)
    invocation_model_dict = invocation_model.dict()
    assert invocation_model_dict['id'] == invocation_model.id == invocation.id
    assert isinstance(invocation_model.id, DatabaseIdField)


def test_invocation_to_encoded_invocation():
    invocation = _get_invocation()
    invocation_model = WorkflowInvocationInDb.from_orm(invocation)
    assert isinstance(invocation_model.id, DatabaseIdField)
    serialized_invocation = WorkflowInvocation(**invocation_model.dict())
    assert isinstance(serialized_invocation.id, EncodedDatabaseIdField)
    assert isinstance(WorkflowInvocationInDb(**serialized_invocation.dict()).id, DatabaseIdField)

def test_workflow_invocation_element_model():
    invocation = _get_invocation()
    invocation_model = WorkflowInvocationElementInDb.from_orm(invocation)
    assert invocation_model.dict() == ''

