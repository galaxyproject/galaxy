from .workflow_support import MockTrans

from galaxy import model
from galaxy.workflow.run_request import normalize_step_parameters


def test_normalize_parameters_empty():
    normalized_params = __normalize_parameters_against_fixture( {} )
    assert normalized_params == {}


def test_normalize_parameters_by_tool():
    normalized_params = __normalize_parameters_against_fixture( {
        'cat1': { 'foo': 'bar' }
    } )
    # Tool specified parameters are expanded out.
    assert normalized_params[ 3 ] == { 'foo': 'bar' }
    assert normalized_params[ 4 ] == { 'foo': 'bar' }
    assert len( normalized_params.keys() ) == 2


def test_step_parameters():
    normalized_params = __normalize_parameters_against_fixture( {
        '1': { 'foo': 'bar' }
    } )
    assert normalized_params[ 1 ] == { 'foo': 'bar' }
    assert len( normalized_params.keys() ) == 1


def test_step_parameters_legacy():
    normalized_params = __normalize_parameters_against_fixture( {
        '1': { 'param': 'foo', 'value': 'bar' }
    } )
    assert normalized_params[ 1 ] == { 'foo': 'bar' }, normalized_params
    assert len( normalized_params.keys() ) == 1


def __normalize_parameters_against_fixture( params ):
    trans = MockTrans()
    workflow = __workflow_fixure( trans )
    normalized_params = normalize_step_parameters( workflow.steps, params )
    return normalized_params


def __workflow_fixure( trans ):
    user = model.User(
        email="testworkflow_params@bx.psu.edu",
        password="pass"
    )
    stored_workflow = model.StoredWorkflow()
    stored_workflow.user = user
    workflow = model.Workflow()
    workflow.stored_workflow = stored_workflow

    def add_step( **kwds ):
        workflow_step = model.WorkflowStep()
        for key, value in kwds.iteritems():
            setattr(workflow_step, key, value)
        workflow.steps.append( workflow_step )

    trans.app.model.context.add(
        workflow,
    )

    add_step(
        type="input",
        order_index=0,
    )
    add_step(
        type="input",
        order_index=1,
    )
    add_step(
        type="tool",
        tool_id="cat1",
        order_index=2,
    )
    add_step(
        type="tool",
        tool_id="cat1",
        order_index=4,
    )
    trans.app.model.context.flush()
    return workflow
