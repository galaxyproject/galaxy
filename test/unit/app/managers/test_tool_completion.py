"""Transaction and polling boundaries for tool completion notifications."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import cast

import pytest
from sqlalchemy import (
    event,
    select,
    update,
)
from sqlalchemy.orm import object_session

from galaxy import model
from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.managers.notification import NotificationManager
from galaxy.managers.tool_completion import ToolCompletionManager
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.structured_app import MinimalManagerApp


@pytest.fixture
def app(tmp_path):
    app = cast(MinimalManagerApp, MockApp(database_connection=f"sqlite:///{tmp_path / 'notifications.sqlite'}"))
    app.config.galaxy_infrastructure_url = "https://galaxy.example.org"
    app[NotificationManager] = NotificationManager(app[galaxy_scoped_session], app.config)
    yield app
    app.model.context.remove()
    app.model.engine.dispose()


@pytest.fixture
def manager(app):
    return app[ToolCompletionManager]


@pytest.fixture
def history(app):
    history = model.History(user=model.User(email="user@example.org", password="password", username="user"))
    app.model.context.add(history)
    app.model.context.commit()
    return history


def request_notification(history, states, mapped=False, populated="ok"):
    session = object_session(history)
    assert session is not None
    jobs = []
    collection_jobs = model.ImplicitCollectionJobs(populated_state=populated) if mapped else None
    for index, state in enumerate(states):
        job = model.Job()
        job.user = history.user
        job.history = history
        job.state = state
        jobs.append(job)
        if collection_jobs is not None:
            association = model.ImplicitCollectionJobsJobAssociation()
            association.job = job
            association.order_index = index
            collection_jobs.jobs.append(association)
    request = model.ToolCompletionNotification(
        user=history.user,
        history=history,
        job=jobs[0] if collection_jobs is None else None,
        implicit_collection_jobs=collection_jobs,
    )
    session.add(request)
    session.commit()
    return request, jobs


def test_map_over_loads_only_one_representative_job_after_completion(app, manager, history):
    request, jobs = request_notification(history, ["ok"] * 999 + ["running"], mapped=True)
    request_id, last_job_id = request.id, jobs[-1].id
    session = app.model.context
    session.expunge_all()
    loaded_jobs = []

    def record_job_load(session, instance):
        if isinstance(instance, model.Job):
            loaded_jobs.append(instance.id)

    event.listen(session(), "loaded_as_persistent", record_job_load)
    try:
        assert not manager.check_and_notify(request_id)
        assert loaded_jobs == []
        session.execute(update(model.Job).where(model.Job.id == last_job_id).values(state="error"))
        session.commit()
        assert manager.check_and_notify(request_id)
        assert len(loaded_jobs) == 1
        [notification] = session.scalars(select(model.Notification)).all()
        assert "999 ok" in notification.content["message"]
        assert "1 error" in notification.content["message"]
    finally:
        event.remove(session(), "loaded_as_persistent", record_job_load)


@pytest.mark.parametrize("population", ["ok", "failed"])
def test_empty_map_waits_for_population_and_links_to_the_requested_history(app, manager, history, population):
    request, _ = request_notification(history, [], mapped=True, populated="new")
    request_id = request.id
    history_id = app.security.encode_id(history.id)
    assert not manager.check_and_notify(request_id)
    request.implicit_collection_jobs.populated_state = population
    app.model.context.commit()
    assert manager.check_and_notify(request_id)
    [notification] = app.model.context.scalars(select(model.Notification)).all()
    assert notification.content["subject"] == "Tool run completed"
    assert "0 jobs" in notification.content["message"]
    assert f"https://galaxy.example.org/histories/view?id={history_id}" in notification.content["message"]
    assert ("some jobs could not be created" in notification.content["message"]) is (population == "failed")
    assert notification.variant == ("warning" if population == "failed" else "info")


def test_failed_delivery_rolls_back_marker_and_notification(app, manager, history):
    request, _ = request_notification(history, ["ok"])
    request_id = request.id

    def fail_recipient_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO user_notification_association"):
            raise RuntimeError("database unavailable")

    event.listen(app.model.engine, "before_cursor_execute", fail_recipient_insert)
    try:
        with pytest.raises(RuntimeError, match="database unavailable"):
            manager.check_and_notify(request_id)
    finally:
        event.remove(app.model.engine, "before_cursor_execute", fail_recipient_insert)
    assert not app.model.context.get(model.ToolCompletionNotification, request_id).completed
    assert app.model.context.scalars(select(model.Notification)).all() == []
    assert manager.check_and_notify(request_id)
    assert len(app.model.context.scalars(select(model.UserNotificationAssociation)).all()) == 1


def test_concurrent_monitors_create_one_notification(app, history):
    request, _ = request_notification(history, ["ok"])
    request_id = request.id
    sessions = app.model.context
    sessions.remove()
    barrier = Barrier(2)

    def synchronize_claims(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE tool_completion_notification"):
            barrier.wait(timeout=10)

    def notify():
        try:
            return app[ToolCompletionManager].check_and_notify(request_id)
        finally:
            sessions.remove()

    event.listen(app.model.engine, "before_cursor_execute", synchronize_claims)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: notify(), range(2)))
        assert sorted(results) == [False, True]
        assert len(sessions.scalars(select(model.UserNotificationAssociation)).all()) == 1
        assert len(sessions.scalars(select(model.Notification)).all()) == 1
    finally:
        event.remove(app.model.engine, "before_cursor_execute", synchronize_claims)


def test_monitor_reaches_later_requests_and_revisits_unfinished_jobs(app, manager, history):
    requests = [request_notification(history, ["running"])[0] for _ in range(100)]
    ready, _ = request_notification(history, ["ok"])
    first_id, ready_id = requests[0].id, ready.id
    session = app.model.context
    manager.monitor()
    assert not session.get(model.ToolCompletionNotification, ready_id).completed
    manager.monitor()
    assert session.get(model.ToolCompletionNotification, ready_id).completed
    manager.monitor()
    first = session.get(model.ToolCompletionNotification, first_id)
    first.job.state = "ok"
    session.commit()
    manager.monitor()
    assert session.get(model.ToolCompletionNotification, first_id).completed
