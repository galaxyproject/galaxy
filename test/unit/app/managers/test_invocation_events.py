import pytest

from galaxy import model
from galaxy.managers.invocation_events import InvocationEventPublisher
from galaxy.model import mapping
from galaxy.queue_worker import InvocationUpdate
from galaxy.schema.invocation import InvocationCancellationUserRequest

States = model.WorkflowInvocation.states


class RecordingDispatcher:
    def __init__(self) -> None:
        self.calls: list[list[InvocationUpdate]] = []

    def invocation_update(self, updates: list[InvocationUpdate], event_id: str | None = None) -> None:
        self.calls.append(updates)


class BrokenDispatcher:
    def invocation_update(self, updates, event_id=None):
        raise RuntimeError("broker down")


@pytest.fixture
def galaxy_model():
    return mapping.init("/tmp", "sqlite:///:memory:", create_tables=True)


@pytest.fixture
def dispatcher(galaxy_model) -> RecordingDispatcher:
    dispatcher = RecordingDispatcher()
    InvocationEventPublisher(dispatcher).register(galaxy_model.session)  # type: ignore[arg-type]
    return dispatcher


@pytest.fixture
def session(galaxy_model, dispatcher):
    return galaxy_model.session


def _user(session, email="owner@example.org") -> model.User:
    user = model.User(email=email, password="password")
    session.add(user)
    session.commit()
    return user


def _invocation(
    session, user: model.User | None, state=States.READY, workflow_owner: model.User | None = None
) -> model.WorkflowInvocation:
    history = model.History(user=user)
    workflow = model.Workflow()
    workflow.stored_workflow = model.StoredWorkflow(user=workflow_owner or user)
    invocation = model.WorkflowInvocation()
    invocation.history = history
    invocation.workflow = workflow
    invocation.state = state
    session.add_all([history, workflow, invocation])
    session.commit()
    return invocation


def test_set_state_is_published_only_once_committed(session, dispatcher):
    user = _user(session)
    invocation = _invocation(session, user)
    dispatcher.calls.clear()

    invocation.set_state(States.SCHEDULED)
    assert dispatcher.calls == []
    session.commit()
    assert dispatcher.calls == [[{"user_id": user.id, "invocation_id": invocation.id, "state": "scheduled"}]]


def test_rolled_back_change_is_not_published(session, dispatcher):
    user = _user(session)
    invocation = _invocation(session, user)
    dispatcher.calls.clear()

    invocation.set_state(States.SCHEDULED)
    invocation.cancel()
    session.flush()
    session.rollback()
    session.commit()
    assert dispatcher.calls == []


def test_unchanged_state_is_not_published(session, dispatcher):
    user = _user(session)
    invocation = _invocation(session, user)
    completed = _invocation(session, user, state=States.COMPLETED)
    dispatcher.calls.clear()

    # Stays ready on every scheduling iteration that schedules nothing new.
    invocation.set_state(States.READY)
    # set_state never reverts a completed invocation.
    completed.set_state(States.SCHEDULED)
    session.commit()
    assert dispatcher.calls == []
    session.refresh(completed)
    assert completed.state == States.COMPLETED


def test_changes_of_one_transaction_are_sent_together(session, dispatcher):
    user = _user(session)
    parent = _invocation(session, user)
    child = _invocation(session, user)
    dispatcher.calls.clear()

    child.set_state(States.SCHEDULED)
    parent.set_state(States.SCHEDULED)
    session.commit()
    assert len(dispatcher.calls) == 1
    assert sorted(dispatcher.calls[0], key=lambda u: u["invocation_id"]) == [
        {"user_id": user.id, "invocation_id": parent.id, "state": "scheduled"},
        {"user_id": user.id, "invocation_id": child.id, "state": "scheduled"},
    ]


def test_released_savepoint_is_published_with_the_root_transaction(session, dispatcher):
    user = _user(session)
    invocation = _invocation(session, user, state=States.NEW)
    dispatcher.calls.clear()

    invocation.set_state(States.READY)
    with session.begin_nested():
        session.add(model.User(email="other@example.org", password="password"))
    assert dispatcher.calls == []
    invocation.set_state(States.SCHEDULED)
    session.commit()
    assert dispatcher.calls == [[{"user_id": user.id, "invocation_id": invocation.id, "state": "scheduled"}]]


def test_rolled_back_savepoint_is_not_published(session, dispatcher):
    user = _user(session)
    published = _invocation(session, user)
    rolled_back = _invocation(session, user)
    dispatcher.calls.clear()

    published.set_state(States.SCHEDULED)
    savepoint = session.begin_nested()
    rolled_back.set_state(States.SCHEDULED)
    savepoint.rollback()
    session.commit()
    assert dispatcher.calls == [[{"user_id": user.id, "invocation_id": published.id, "state": "scheduled"}]]


def test_message_is_published_with_the_current_state(session, dispatcher):
    user = _user(session)
    invocation = _invocation(session, user)
    dispatcher.calls.clear()

    invocation.add_message(InvocationCancellationUserRequest(reason="user_request"))
    session.commit()
    assert dispatcher.calls == [[{"user_id": user.id, "invocation_id": invocation.id, "state": "ready"}]]


def test_anonymous_invocation_is_not_published(session, dispatcher):
    invocation = _invocation(session, None, workflow_owner=_user(session))
    invocation.set_state(States.SCHEDULED)
    session.commit()
    assert dispatcher.calls == []


def test_dispatch_failure_does_not_fail_commit(galaxy_model):
    InvocationEventPublisher(BrokenDispatcher()).register(galaxy_model.session)  # type: ignore[arg-type]
    session = galaxy_model.session
    invocation = _invocation(session, _user(session))
    invocation.set_state(States.SCHEDULED)
    session.commit()
    session.refresh(invocation)
    assert invocation.state == States.SCHEDULED
