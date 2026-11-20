import json

import pytest

from galaxy import model
from galaxy.managers.invocation_events import InvocationEventPublisher
from galaxy.managers.sse import (
    SSEConnectionManager,
    SSEEvent,
)
from galaxy.model import mapping
from galaxy.queue_worker import (
    invocation_update,
    InvocationUpdate,
)
from galaxy.schema.invocation import InvocationCancellationUserRequest
from galaxy.security.idencoding import IdEncodingHelper

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


def test_new_invocation_is_published_after_commit(session, dispatcher):
    user = _user(session)
    invocation = _invocation(session, user, state=States.NEW)
    assert dispatcher.calls == [[{"user_id": user.id, "invocation_id": invocation.id, "state": "new"}]]


def test_set_state_is_published_only_once_committed(session, dispatcher):
    user = _user(session)
    invocation = _invocation(session, user)
    dispatcher.calls.clear()

    invocation.set_state(States.SCHEDULED)
    assert dispatcher.calls == []
    session.commit()
    assert dispatcher.calls == [[{"user_id": user.id, "invocation_id": invocation.id, "state": "scheduled"}]]


def test_attribute_assignment_is_published(session, dispatcher):
    user = _user(session)
    invocation = _invocation(session, user, state=States.SCHEDULED)
    dispatcher.calls.clear()

    invocation.state = States.COMPLETED
    session.commit()
    assert dispatcher.calls == [[{"user_id": user.id, "invocation_id": invocation.id, "state": "completed"}]]


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

    # Stays ready on every scheduling iteration that leaves steps delayed.
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


def test_step_and_message_changes_are_published_with_the_current_state(session, dispatcher):
    user = _user(session)
    invocation = _invocation(session, user)
    workflow_step = model.WorkflowStep()
    workflow_step.order_index = 0
    workflow_step.workflow = invocation.workflow
    session.add(workflow_step)
    session.commit()
    dispatcher.calls.clear()

    step = model.WorkflowInvocationStep()
    step.workflow_invocation = invocation
    step.workflow_step = workflow_step
    step.state = "new"
    session.add(step)
    session.commit()
    expected = [[{"user_id": user.id, "invocation_id": invocation.id, "state": "ready"}]]
    assert dispatcher.calls == expected

    step.state = "scheduled"
    session.commit()
    assert dispatcher.calls == expected * 2

    invocation.add_message(InvocationCancellationUserRequest(reason="user_request"))
    session.commit()
    assert dispatcher.calls == expected * 3


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


class RecordingSSEManager:
    def __init__(self) -> None:
        self.pushed: list[tuple[int, SSEEvent]] = []

    def push_to_user(self, user_id: int, event: SSEEvent) -> None:
        self.pushed.append((user_id, event))


class FakeApp:
    def __init__(self) -> None:
        self.sse_manager = RecordingSSEManager()
        self.security = IdEncodingHelper(id_secret="1234567890abcdef")

    def __getitem__(self, key):
        assert key is SSEConnectionManager
        return self.sse_manager


def test_invocation_update_task_pushes_one_event_per_owner():
    app = FakeApp()
    invocation_update(
        app,  # type: ignore[arg-type]
        updates=[
            {"user_id": 1, "invocation_id": 10, "state": "scheduled"},
            {"user_id": 2, "invocation_id": 20, "state": "cancelled"},
            {"user_id": 1, "invocation_id": 11, "state": "scheduled"},
        ],
        event_id="e1",
    )

    encode = app.security.encode_id
    pushed = {user_id: (event.event, event.id, json.loads(event.data)) for user_id, event in app.sse_manager.pushed}
    assert len(app.sse_manager.pushed) == 2
    assert pushed == {
        1: (
            "invocation_update",
            "e1",
            {
                "invocations": [
                    {"id": encode(10), "state": "scheduled"},
                    {"id": encode(11), "state": "scheduled"},
                ]
            },
        ),
        2: ("invocation_update", "e1", {"invocations": [{"id": encode(20), "state": "cancelled"}]}),
    }
