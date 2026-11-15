"""Transaction and polling boundaries for tool completion notifications."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import (
    Barrier,
    Event,
)
from typing import cast

import pytest
from sqlalchemy import (
    event,
    select,
    update,
)
from sqlalchemy.orm import object_session

from galaxy import (
    model,
    util,
)
from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.managers.notification import NotificationManager
from galaxy.managers.tool_completion import (
    ToolCompletionManager,
    ToolCompletionMonitor,
)
from galaxy.model.database_heartbeat import (
    DatabaseHeartbeat,
    WEBAPP,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.structured_app import MinimalManagerApp
from galaxy.util import now
from galaxy.util.unittest_utils import read_mock_emails
from galaxy.web_stack import application_stack_instance
from galaxy_test.base.populators import wait_on


@pytest.fixture
def app_factory(tmp_path):
    apps = []

    def create_app():
        app = cast(MinimalManagerApp, MockApp(database_connection=f"sqlite:///{tmp_path / 'notifications.sqlite'}"))
        app.config.galaxy_infrastructure_url = "https://galaxy.example.org"
        app[NotificationManager] = NotificationManager(app[galaxy_scoped_session], app.config)
        apps.append(app)
        return app

    yield create_app
    for app in apps:
        app.model.context.remove()
        app.model.engine.dispose()


@pytest.fixture
def app(app_factory):
    return app_factory()


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


@pytest.mark.parametrize("notifications_enabled", [True, False])
def test_failed_delivery_rolls_back_marker_and_notification(app, manager, history, notifications_enabled):
    app.config.enable_notification_system = notifications_enabled
    app.config.smtp_server = "smtp.example.org"
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


def test_only_elected_monitor_polls_and_failover_resumes_empty_map(app, app_factory, history):
    request, _ = request_notification(history, [], mapped=True, populated="new")
    collection_id = request.implicit_collection_jobs_id
    apps = [app, *(app_factory() for _ in range(3))]
    heartbeats = []
    monitors = []
    polled = [Event() for _ in apps]
    email_polled = [Event() for _ in apps]
    listeners = []
    for index, worker in enumerate(apps):
        worker.config.server_name = f"web_{index}"
        worker.config.attach_to_pools = False
        worker.config.workflow_completion_monitor_sleep = 0.01
        heartbeat = DatabaseHeartbeat(application_stack_instance(app=worker), app_type=WEBAPP)
        monitor = worker[ToolCompletionMonitor]
        heartbeat.add_change_callback(monitor.on_role_change)
        heartbeats.append(heartbeat)
        monitors.append(monitor)
        app.model.context.add(
            model.WorkerProcess(server_name=worker.config.server_name, hostname=heartbeat.hostname, app_type=WEBAPP)
        )

        def record_poll(
            conn,
            cursor,
            statement,
            parameters,
            context,
            executemany,
            signal=polled[index],
            email_signal=email_polled[index],
        ):
            if statement.startswith("SELECT tool_completion_notification.id"):
                signal.set()
            if statement.startswith("SELECT notification.id") and "WHERE notification.email_only" in statement:
                email_signal.set()

        event.listen(worker.model.engine, "before_cursor_execute", record_poll)
        listeners.append(record_poll)
    app.model.context.commit()
    try:
        for heartbeat in heartbeats:
            heartbeat.update_watcher_designation()
        assert polled[3].wait(timeout=5)
        assert email_polled[3].wait(timeout=5)
        assert not any(signal.is_set() for signal in [*polled[:3], *email_polled[:3]])

        # Simulate losing the elected process while map population is incomplete.
        monitors[3].shutdown()
        app.model.context.execute(
            update(model.WorkerProcess)
            .where(model.WorkerProcess.server_name == "web_3")
            .values(update_time=now() - timedelta(minutes=2))
        )
        app.model.context.execute(
            update(model.ImplicitCollectionJobs)
            .where(model.ImplicitCollectionJobs.id == collection_id)
            .values(populated_state="ok")
        )
        app.model.context.commit()
        for heartbeat in heartbeats[:3]:
            heartbeat.update_watcher_designation()
        assert polled[2].wait(timeout=5)
        assert email_polled[2].wait(timeout=5)
        assert not any(signal.is_set() for signal in [*polled[:2], *email_polled[:2]])

        def notifications():
            app.model.context.remove()
            return app.model.context.scalars(select(model.Notification)).all() or None

        [notification] = wait_on(notifications, "notification after monitor failover")
        assert "0 jobs" in notification.content["message"]

        # The same process can lose and regain the role without reusing a stopped thread.
        monitors[2].shutdown()
        polled[2].clear()
        email_polled[2].clear()
        monitors[2].on_role_change(True)
        assert polled[2].wait(timeout=5)
        assert email_polled[2].wait(timeout=5)
        assert len(notifications()) == 1
    finally:
        for worker, monitor, listener in zip(apps, monitors, listeners):
            monitor.shutdown()
            event.remove(worker.model.engine, "before_cursor_execute", listener)


def test_smtp_outbox_retries_after_failure_and_worker_restart(
    app, app_factory, manager, history, tmp_path, monkeypatch
):
    app.config.enable_notification_system = False
    app.config.enable_celery_tasks = False
    email_dir = tmp_path / "emails"
    email_dir.mkdir()
    app.config.smtp_server = f"mock_emails_to_path://{email_dir}"
    # A category mute applies to in-app notifications, not an explicit SMTP-only request.
    history.user.preferences["notifications"] = '{"tool_execution_completed":{"enabled":false}}'
    request, _ = request_notification(history, ["ok"])
    request_id, user_id = request.id, history.user_id
    assert manager.check_and_notify(request_id)
    notifications = app[NotificationManager]
    [queued] = app.model.context.scalars(select(model.Notification)).all()
    queued_id = queued.id
    assert notifications.get_user_notifications(history.user) == []
    assert notifications.get_user_total_unread_notification_count(history.user) == 0

    def failed_send(*args, **kwds):
        # Network I/O must not hold the worker's database transaction open.
        assert not app.model.context().in_transaction()
        raise OSError("SMTP unavailable")

    with monkeypatch.context() as patcher:
        patcher.setattr(util, "send_mail", failed_send)
        notifications.dispatch_completion_emails()
    assert app.model.context.get(model.ToolCompletionNotification, request_id).completed
    assert app.model.context.get(model.Notification, queued_id).email_claimed_at is not None
    app.model.context.remove()

    replacement = app_factory()
    replacement.config.smtp_server = app.config.smtp_server
    replacement.config.enable_notification_system = False
    replacement.config.enable_celery_tasks = False
    dispatcher = replacement[NotificationManager]
    # A new owner must honor the outstanding lease; then recover the failed send.
    dispatcher.dispatch_completion_emails()
    assert read_mock_emails(email_dir) == []
    # Already queued emails still drain if the administrator enables notifications.
    replacement.config.enable_notification_system = True
    replacement.model.context.execute(
        update(model.Notification)
        .where(model.Notification.id == queued_id)
        .values(email_claimed_at=now() - timedelta(minutes=6))
    )
    replacement.model.context.commit()
    dispatcher.dispatch_completion_emails()
    [email] = read_mock_emails(email_dir)
    assert email["to"] == "user@example.org"
    assert "1 ok" in email["body"]
    assert replacement.model.context.get(model.Notification, queued_id) is None
    assert (
        list(
            replacement.model.context.scalars(
                select(model.UserNotificationAssociation).where(model.UserNotificationAssociation.user_id == user_id)
            )
        )
        == []
    )
    dispatcher.dispatch_completion_emails()
    assert len(read_mock_emails(email_dir)) == 1
