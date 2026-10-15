import pytest

from galaxy import model


@pytest.fixture(scope="module")
def init_model(engine):
    model.Base.metadata.create_all(engine)


@pytest.mark.parametrize("state", ["new", "ready", "requires_materialization", "cancelling"])
@pytest.mark.parametrize("filter_handler", [False, True])
def test_child_invocations_are_scheduled_through_their_parent(session, make_workflow_invocation, state, filter_handler):
    parent = make_workflow_invocation(state=state, handler="mapping-test", scheduler="mapping-test")
    child = make_workflow_invocation(state=state, handler="mapping-test", scheduler="mapping-test")
    grandchild = make_workflow_invocation(state=state, handler="mapping-test", scheduler="mapping-test")
    unrelated = make_workflow_invocation(state=state, handler="other", scheduler="other")
    session.add_all(
        [
            model.WorkflowInvocationToSubworkflowInvocationAssociation(
                parent_workflow_invocation=parent, subworkflow_invocation=child
            ),
            model.WorkflowInvocationToSubworkflowInvocationAssociation(
                parent_workflow_invocation=child, subworkflow_invocation=grandchild
            ),
        ]
    )
    session.commit()

    options = {"handler": "mapping-test", "scheduler": "mapping-test"} if filter_handler else {}
    active_ids = model.WorkflowInvocation.poll_active_workflow_ids(session.bind, **options)

    assert parent.id in active_ids
    assert (unrelated.id in active_ids) is (not filter_handler)
    assert (child.id in active_ids) is (state == "cancelling")
    assert (grandchild.id in active_ids) is (state == "cancelling")
