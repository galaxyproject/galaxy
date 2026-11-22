import pytest

from galaxy import model
from galaxy.managers import change_events
from galaxy.managers.change_events import ChangeEventPublisher
from galaxy.model import mapping
from galaxy.model.pending_changes import (
    InvocationUpdate,
    JobUpdate,
)
from galaxy.schema.invocation import InvocationCancellationUserRequest

States = model.WorkflowInvocation.states


class RecordingDispatcher:
    def __init__(self) -> None:
        self.calls: list[list[InvocationUpdate]] = []
        self.job_calls: list[tuple[list[JobUpdate], list[int] | None, list[int] | None, list[int] | None]] = []

    def invocation_update(self, updates: list[InvocationUpdate], event_id: str | None = None) -> None:
        self.calls.append(updates)

    def job_update(
        self, updates, resync_user_ids=None, resync_session_ids=None, resync_history_ids=None, event_id=None
    ) -> None:
        self.job_calls.append((updates, resync_user_ids, resync_session_ids, resync_history_ids))


class BrokenDispatcher:
    def invocation_update(self, updates, event_id=None):
        raise RuntimeError("broker down")

    def job_update(
        self, updates, resync_user_ids=None, resync_session_ids=None, resync_history_ids=None, event_id=None
    ):
        raise RuntimeError("broker down")


@pytest.fixture
def galaxy_model():
    return mapping.init("/tmp", "sqlite:///:memory:", create_tables=True)


@pytest.fixture
def dispatcher(galaxy_model) -> RecordingDispatcher:
    dispatcher = RecordingDispatcher()
    ChangeEventPublisher(dispatcher).register(galaxy_model.session)  # type: ignore[arg-type]
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
    assert dispatcher.calls == [
        [
            {
                "user_id": user.id,
                "history_id": invocation.history_id,
                "invocation_id": invocation.id,
                "state": "scheduled",
            }
        ]
    ]


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
        {"user_id": user.id, "history_id": parent.history_id, "invocation_id": parent.id, "state": "scheduled"},
        {"user_id": user.id, "history_id": child.history_id, "invocation_id": child.id, "state": "scheduled"},
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
    assert dispatcher.calls == [
        [
            {
                "user_id": user.id,
                "history_id": invocation.history_id,
                "invocation_id": invocation.id,
                "state": "scheduled",
            }
        ]
    ]


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
    assert dispatcher.calls == [
        [{"user_id": user.id, "history_id": published.history_id, "invocation_id": published.id, "state": "scheduled"}]
    ]


def test_message_is_published_with_the_current_state(session, dispatcher):
    user = _user(session)
    invocation = _invocation(session, user)
    dispatcher.calls.clear()

    invocation.add_message(InvocationCancellationUserRequest(reason="user_request"))
    session.commit()
    assert dispatcher.calls == [
        [{"user_id": user.id, "history_id": invocation.history_id, "invocation_id": invocation.id, "state": "ready"}]
    ]


def test_invocation_in_an_ownerless_history_is_published_for_its_viewers(session, dispatcher):
    invocation = _invocation(session, None, workflow_owner=_user(session))
    dispatcher.calls.clear()
    invocation.set_state(States.SCHEDULED)
    session.commit()
    assert dispatcher.calls == [
        [{"user_id": None, "history_id": invocation.history_id, "invocation_id": invocation.id, "state": "scheduled"}]
    ]


def test_dispatch_failure_does_not_fail_commit(galaxy_model):
    ChangeEventPublisher(BrokenDispatcher()).register(galaxy_model.session)  # type: ignore[arg-type]
    session = galaxy_model.session
    invocation = _invocation(session, _user(session))
    invocation.set_state(States.SCHEDULED)
    session.commit()
    session.refresh(invocation)
    assert invocation.state == States.SCHEDULED


def _job(
    session,
    user: model.User | None = None,
    galaxy_session: model.GalaxySession | None = None,
    history: model.History | None = None,
) -> model.Job:
    job = model.Job()
    job.tool_id = "cat1"
    job.user = user
    job.galaxy_session = galaxy_session
    job.history = history
    job.set_state(model.Job.states.QUEUED)
    session.add(job)
    return job


def test_job_state_change_is_published_only_once_committed(session, dispatcher):
    user = _user(session)
    job = _job(session, user)
    session.flush()
    assert dispatcher.job_calls == []
    session.commit()
    assert dispatcher.job_calls == [
        (
            [{"job_id": job.id, "state": "queued", "user_id": user.id, "session_id": None, "history_id": None}],
            [],
            [],
            [],
        )
    ]

    dispatcher.job_calls.clear()
    job.set_state(model.Job.states.RUNNING)
    session.commit()
    assert dispatcher.job_calls == [
        (
            [{"job_id": job.id, "state": "running", "user_id": user.id, "session_id": None, "history_id": None}],
            [],
            [],
            [],
        )
    ]


def test_job_state_assignment_is_published_with_the_state_at_commit(session, dispatcher):
    user = _user(session)
    job = _job(session, user)
    session.commit()
    dispatcher.job_calls.clear()

    # mark_deleted assigns the state without adding a JobStateHistory row.
    job.mark_deleted()
    session.commit()
    assert dispatcher.job_calls == [
        (
            [{"job_id": job.id, "state": "deleted", "user_id": user.id, "session_id": None, "history_id": None}],
            [],
            [],
            [],
        )
    ]

    dispatcher.job_calls.clear()
    skipped = _job(session, user)
    skipped.state = model.Job.states.SKIPPED
    session.commit()
    assert dispatcher.job_calls == [
        (
            [{"job_id": skipped.id, "state": "skipped", "user_id": user.id, "session_id": None, "history_id": None}],
            [],
            [],
            [],
        )
    ]


def test_anonymous_job_is_routed_to_its_session(session, dispatcher):
    galaxy_session = model.GalaxySession()
    session.add(galaxy_session)
    session.commit()
    job = _job(session, galaxy_session=galaxy_session)
    session.commit()
    assert dispatcher.job_calls == [
        (
            [
                {
                    "job_id": job.id,
                    "state": "queued",
                    "user_id": None,
                    "session_id": galaxy_session.id,
                    "history_id": None,
                }
            ],
            [],
            [],
            [],
        )
    ]


def test_too_many_job_changes_for_one_recipient_become_a_resync(session, dispatcher, monkeypatch):
    monkeypatch.setattr(change_events, "MAX_JOBS_PER_EVENT", 2)
    busy_user = _user(session)
    busy_history = model.History(user=busy_user)
    other_user = _user(session, email="other@example.org")
    for _ in range(3):
        _job(session, busy_user, history=busy_history)
    other_job = _job(session, other_user)
    session.commit()
    assert dispatcher.job_calls == [
        (
            [
                {
                    "job_id": other_job.id,
                    "state": "queued",
                    "user_id": other_user.id,
                    "session_id": None,
                    "history_id": None,
                }
            ],
            [busy_user.id],
            [],
            [busy_history.id],
        )
    ]
