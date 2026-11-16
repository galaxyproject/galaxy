"""Transaction and polling boundaries for tool and workflow run notifications."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from smtplib import SMTPRecipientsRefused
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
from galaxy.managers.run_notifications import (
    RunNotificationManager,
    RunNotificationMonitor,
)
from galaxy.managers.workflow_completion import WorkflowCompletionManager
from galaxy.model.database_heartbeat import (
    DatabaseHeartbeat,
    WEBAPP,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.structured_app import MinimalManagerApp
from galaxy.util import now
from galaxy.util.unittest_utils import read_mock_emails
from galaxy.util.wait import wait_on
from galaxy.web_stack import application_stack_instance


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
    return app[RunNotificationManager]


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
    request = model.RunNotificationRequest(
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
    assert notification.content["implicit_collection_jobs_id"] == app.security.encode_id(
        request.implicit_collection_jobs_id
    )
    assert notification.content["job_id"] is None
    assert notification.content["subject"] == "Tool run completed"
    assert "0 jobs" in notification.content["message"]
    assert f"https://galaxy.example.org/histories/view?id={history_id}" in notification.content["message"]
    assert ("some jobs could not be created" in notification.content["message"]) is (population == "failed")
    assert notification.variant == ("warning" if population == "failed" else "info")


@pytest.mark.parametrize("state", ["paused", "ok"])
@pytest.mark.parametrize("notifications_enabled", [True, False])
def test_failed_delivery_rolls_back_marker_and_notification(app, manager, history, notifications_enabled, state):
    app.config.enable_notification_system = notifications_enabled
    app.config.smtp_server = "smtp.example.org"
    request, _ = request_notification(history, [state])
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
    persisted = app.model.context.get(model.RunNotificationRequest, request_id)
    assert not persisted.completed
    assert not persisted.attention_sent
    assert app.model.context.scalars(select(model.Notification)).all() == []
    assert manager.check_and_notify(request_id)
    assert len(app.model.context.scalars(select(model.UserNotificationAssociation)).all()) == 1


@pytest.mark.parametrize("state", ["paused", "ok"])
@pytest.mark.parametrize("notifications_enabled", [True, False])
def test_concurrent_monitors_create_one_notification(app, history, tmp_path, notifications_enabled, state):
    app.config.enable_notification_system = notifications_enabled
    email_dir = tmp_path / "emails"
    email_dir.mkdir()
    app.config.smtp_server = f"mock_emails_to_path://{email_dir}"
    request, _ = request_notification(history, [state])
    request_id = request.id
    sessions = app.model.context
    sessions.remove()
    barrier = Barrier(2)

    def synchronize_claims(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith(("UPDATE run_notification_request", "UPDATE notification")):
            barrier.wait(timeout=10)

    def notify():
        try:
            return app[RunNotificationManager].check_and_notify(request_id)
        finally:
            sessions.remove()

    event.listen(app.model.engine, "before_cursor_execute", synchronize_claims)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: notify(), range(2)))
        assert sorted(results) == [False, True]
        assert len(sessions.scalars(select(model.UserNotificationAssociation)).all()) == 1
        assert len(sessions.scalars(select(model.Notification)).all()) == 1
        if not notifications_enabled:
            sessions.remove()
            dispatchers = [NotificationManager(app[galaxy_scoped_session], app.config) for _ in range(2)]
            with ThreadPoolExecutor(max_workers=2) as executor:
                list(executor.map(lambda dispatcher: dispatcher.dispatch_completion_emails(), dispatchers))
            assert len(read_mock_emails(email_dir)) == 1
            assert list(sessions.scalars(select(model.Notification))) == []
    finally:
        event.remove(app.model.engine, "before_cursor_execute", synchronize_claims)


def test_monitor_reaches_later_requests_and_revisits_unfinished_jobs(app, manager, history):
    requests = [request_notification(history, ["running"])[0] for _ in range(100)]
    ready, _ = request_notification(history, ["ok"])
    first_id, ready_id = requests[0].id, ready.id
    session = app.model.context
    manager.monitor()
    assert not session.get(model.RunNotificationRequest, ready_id).completed
    manager.monitor()
    assert session.get(model.RunNotificationRequest, ready_id).completed
    manager.monitor()
    first = session.get(model.RunNotificationRequest, first_id)
    first.job.state = "ok"
    session.commit()
    manager.monitor()
    assert session.get(model.RunNotificationRequest, first_id).completed


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
        monitor = worker[RunNotificationMonitor]
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
            if statement.startswith("SELECT run_notification_request.id"):
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

        [notification] = wait_on(notifications, "notification after monitor failover", timeout=10)
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


@pytest.mark.parametrize(
    "smtp_error", [SMTPRecipientsRefused({"user@example.org": (550, b"Rejected")}), OSError("SMTP unavailable")]
)
def test_smtp_failure_is_not_retried_and_does_not_block_later_emails(
    app, app_factory, manager, history, tmp_path, monkeypatch, caplog, smtp_error
):
    app.config.enable_notification_system = False
    app.config.enable_celery_tasks = False
    email_dir = tmp_path / "emails"
    email_dir.mkdir()
    app.config.smtp_server = f"mock_emails_to_path://{email_dir}"
    history.user.preferences["notifications"] = '{"tool_execution_completed":{"enabled":false}}'
    paused_request, paused_jobs = request_notification(history, ["paused"])
    paused_request_id, paused_job_id = paused_request.id, paused_jobs[0].id
    assert manager.check_and_notify(paused_request_id)
    request, _ = request_notification(history, ["ok"])
    assert manager.check_and_notify(request.id)
    notifications = app[NotificationManager]
    assert notifications.get_user_notifications(history.user) == []
    assert notifications.get_user_total_unread_notification_count(history.user) == 0

    send_mail = util.send_mail
    attempts = []

    def fail_first_send(*args, **kwds):
        assert not app.model.context().in_transaction()
        attempts.append(kwds)
        if len(attempts) == 1:
            raise smtp_error
        return send_mail(*args, **kwds)

    with monkeypatch.context() as patcher:
        patcher.setattr(util, "send_mail", fail_first_send)
        notifications.dispatch_completion_emails()
        notifications.dispatch_completion_emails()
        # A failed attention email does not consume the final completion event.
        resumed_job = app.model.context.get(model.Job, paused_job_id)
        resumed_job.resume()
        resumed_job.state = "ok"
        app.model.context.commit()
        assert manager.check_and_notify(paused_request_id)
        notifications.dispatch_completion_emails()
        # Neither restarting the dispatcher nor enabling notifications retries a failed send.
        replacement = app_factory()
        replacement.config.smtp_server = app.config.smtp_server
        replacement[NotificationManager].dispatch_completion_emails()
    assert len(attempts) == 3
    assert "needs attention" in attempts[0]["subject"]
    assert caplog.text.count("will not retry") == 1
    emails = read_mock_emails(email_dir)
    assert len(emails) == 2
    assert all(email["to"] == "user@example.org" and "1 ok" in email["body"] for email in emails)
    assert list(app.model.context.scalars(select(model.Notification))) == []
    assert list(app.model.context.scalars(select(model.UserNotificationAssociation))) == []
    assert [request.completed for request in app.model.context.scalars(select(model.RunNotificationRequest))] == [
        True,
        True,
    ]


@pytest.mark.parametrize("mapped", [False, True])
def test_pause_resume_cycles_send_one_attention_and_one_completion(app, app_factory, manager, history, mapped):
    request, jobs = request_notification(
        history, ["paused", "running"] if mapped else ["paused"], mapped=mapped, populated="new" if mapped else "ok"
    )
    request_id = request.id
    assert manager.check_and_notify(request_id)
    [attention] = app.model.context.scalars(select(model.Notification)).all()
    assert attention.content["event"] == "needs_attention"
    assert attention.variant == "warning"
    assert not request.completed
    assert request.attention_sent
    assert not manager.check_and_notify(request_id)

    # Actual resume paths require no notification writes or resets.
    jobs[0].resume()
    assert not manager.check_and_notify(request_id)
    jobs[0].state = "paused"
    app.model.context.commit()
    assert not manager.check_and_notify(request_id)
    jobs[0].resume()
    for job in jobs:
        job.state = "ok"
    app.model.context.commit()
    if mapped:
        assert not manager.check_and_notify(request_id)  # Population still owns the map.
        request.implicit_collection_jobs.populated_state = "ok"
        app.model.context.commit()
    app.model.context.remove()
    # A replacement process retains the attention marker and sends only the final event.
    replacement = app_factory()
    replacement_manager = replacement[RunNotificationManager]
    assert replacement_manager.check_and_notify(request_id)
    assert not replacement_manager.check_and_notify(request_id)
    notifications = replacement.model.context.scalars(select(model.Notification).order_by(model.Notification.id)).all()
    assert [notification.content["event"] for notification in notifications] == ["needs_attention", "completed"]
    assert f"{len(jobs)} ok" in notifications[-1].content["message"]


def request_workflow_notification(history, states):
    request, jobs = request_notification(history, states, mapped=True)
    group = request.implicit_collection_jobs
    session = object_session(history)
    assert session is not None
    child_workflow = model.Workflow()
    child_step = model.WorkflowStep()
    child_step.type = "tool"
    child_step.order_index = 0
    child_workflow.steps.append(child_step)
    child = model.WorkflowInvocation(workflow=child_workflow, history=history, state="ready")
    child.steps.append(
        model.WorkflowInvocationStep(workflow_step=child_step, state="scheduled", implicit_collection_jobs=group)
    )
    root_workflow = model.Workflow()
    root_step = model.WorkflowStep()
    root_step.type = "subworkflow"
    root_step.order_index = 0
    root_step.subworkflow = child_workflow
    root_workflow.steps.append(root_step)
    root = model.WorkflowInvocation(workflow=root_workflow, history=history, state="ready")
    root.steps.append(model.WorkflowInvocationStep(workflow_step=root_step, state="scheduled"))
    root.attach_subworkflow_invocation_for_step(root_step, child)
    request.implicit_collection_jobs = None
    request.workflow_invocation = root
    session.add(root)
    session.commit()
    return request, jobs, root, child


@pytest.mark.parametrize("state", ["failed", "cancelled"])
def test_terminated_workflow_waits_for_created_jobs_but_not_unscheduled_descendants(app, manager, history, state):
    request, jobs, root, child = request_workflow_notification(history, ["running"])
    request_id = request.id
    root.state = state
    child.state = "new"
    app.model.context.commit()
    assert not manager.check_and_notify(request_id)
    jobs[0].state = "error"
    app.model.context.commit()
    assert manager.check_and_notify(request_id)
    [notification] = app.model.context.scalars(select(model.Notification)).all()
    assert notification.content["event"] == "completed"
    assert state in notification.content["subject"]
    assert notification.variant == "warning"


def test_nested_workflow_watch_outlives_completion_record_without_loading_mapped_jobs(app, manager, history):
    request, jobs, root, child = request_workflow_notification(history, ["paused"] + ["running"] * 999)
    session = app.model.context
    request_id, root_id, child_id, paused_job_id, history_id = request.id, root.id, child.id, jobs[0].id, history.id
    session.expunge_all()

    def reject_job_load(session, instance):
        assert not isinstance(instance, model.Job), "Run notifications must aggregate workflow jobs in SQL"

    event.listen(session(), "loaded_as_persistent", reject_job_load)
    try:
        assert manager.check_and_notify(request_id)  # Scheduling has not finished yet.
        assert not manager.check_and_notify(request_id)
        session.execute(
            update(model.Job)
            .where(model.Job.history_id == history_id, model.Job.id != paused_job_id)
            .values(state="ok")
        )
        session.execute(
            update(model.WorkflowInvocation)
            .where(model.WorkflowInvocation.id.in_([root_id, child_id]))
            .values(state="scheduled")
        )
        session.commit()
        completions = WorkflowCompletionManager(app)
        assert completions.check_and_record_completion(child_id) is not None
        completion = completions.check_and_record_completion(root_id)
        assert completion is not None
        completion.hooks_executed = ["send_notification", "export_to_file_source"]
        session.commit()
        completion_id = completion.id
        assert completion.job_state_summary == {"ok": 999, "paused": 1}
        assert not manager.check_and_notify(request_id)

        session.execute(update(model.Job).where(model.Job.id == paused_job_id).values(state="running"))
        session.commit()
        assert not manager.check_and_notify(request_id)
        session.execute(update(model.Job).where(model.Job.id == paused_job_id).values(state="paused"))
        session.commit()
        assert not manager.check_and_notify(request_id)
        session.execute(update(model.Job).where(model.Job.id == paused_job_id).values(state="ok"))
        session.commit()
        assert manager.check_and_notify(request_id)
        assert not manager.check_and_notify(request_id)
        notifications = session.scalars(select(model.Notification).order_by(model.Notification.id)).all()
        assert [n.content["event"] for n in notifications] == ["needs_attention", "completed"]
        assert "ok: 1000" in notifications[-1].content["message"]
        assert notifications[-1].content["invocation_id"] == app.security.encode_id(root_id)
        # Completion hooks and their original snapshot are untouched.
        assert completions.check_and_record_completion(root_id) is None
        preserved = completions.get_completion(root_id)
        assert preserved is not None
        assert preserved.id == completion_id
        assert preserved.hooks_executed == ["send_notification", "export_to_file_source"]
        assert preserved.job_state_summary == {"ok": 999, "paused": 1}
    finally:
        event.remove(session(), "loaded_as_persistent", reject_job_load)
