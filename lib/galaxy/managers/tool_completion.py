"""Deliver tool completion summaries outside job finishing transactions."""

import logging
from threading import (
    Event,
    Lock,
)

from sqlalchemy import (
    select,
    update,
)

from galaxy.managers.notification import NotificationManager
from galaxy.model import (
    Job,
    ToolCompletionNotification,
)
from galaxy.schema.notifications import (
    InternalNotificationCreateData,
    NotificationCreateRequest,
    NotificationRecipients,
    NotificationVariant,
    PersonalNotificationCategory,
    ToolCompletionNotificationContent,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.util.task import IntervalTask

log = logging.getLogger(__name__)


class ToolCompletionManager:
    def __init__(self, app: MinimalManagerApp, notification_manager: NotificationManager):
        self.app = app
        self.notification_manager = notification_manager
        self._last_pending_id = 0

    def monitor(self, stop_event: Event | None = None) -> None:
        try:
            pending_ids = self.poll_pending_notifications(self._last_pending_id)
            self._last_pending_id = pending_ids[-1] if pending_ids else 0
            for request_id in pending_ids:
                if stop_event is not None and stop_event.is_set():
                    break
                try:
                    self.check_and_notify(request_id)
                except Exception:
                    log.exception("Error delivering tool completion notification %d", request_id)
        except Exception:
            log.exception("Error polling tool completion notifications")
        finally:
            self.app.model.context.remove()

    def poll_pending_notifications(self, after_id: int = 0, limit: int = 100) -> list[int]:
        if not (self.app.config.enable_notification_system or self.app.config.smtp_server):
            return []
        stmt = (
            select(ToolCompletionNotification.id)
            .where(ToolCompletionNotification.completed.is_(False), ToolCompletionNotification.id > after_id)
            .order_by(ToolCompletionNotification.id)
            .limit(limit)
        )
        return list(self.app.model.context.scalars(stmt))

    def check_and_notify(self, request_id: int) -> bool:
        session = self.app.model.context
        try:
            # Different scheduler processes may monitor tool runs. Lock the request,
            # then commit its marker together with the notification and recipients.
            request = session.scalar(
                select(ToolCompletionNotification)
                .where(ToolCompletionNotification.id == request_id, ToolCompletionNotification.completed.is_(False))
                .with_for_update(skip_locked=True)
            )
            if request is None:
                return False
            population_failed = False
            if collection_jobs := request.implicit_collection_jobs:
                if collection_jobs.populated_state == collection_jobs.populated_states.NEW:
                    return False
                if collection_jobs.has_job_not_in_states(Job.settled_states):
                    return False
                counts = collection_jobs.job_state_counts()
                job = collection_jobs.representative_job if counts else None
                population_failed = collection_jobs.populated_state == collection_jobs.populated_states.FAILED
            else:
                job = request.job
                if job is None or not job.is_terminal:
                    return False
                counts = {str(job.state): 1}
            summary = ", ".join(f"{count} {state}" for state, count in sorted(counts.items())) or "0 jobs"
            if population_failed:
                summary += "; some jobs could not be created"
            history_id = self.app.security.encode_id(request.history_id)
            galaxy_url = self.app.config.galaxy_infrastructure_url
            link = f"{galaxy_url or ''}/histories/view?id={history_id}"
            notification_request = NotificationCreateRequest(
                recipients=NotificationRecipients(user_ids=[request.user_id]),
                notification=InternalNotificationCreateData(
                    source="galaxy",
                    category=PersonalNotificationCategory.tool_execution_completed,
                    variant=(
                        NotificationVariant.warning
                        if counts.get("error") or population_failed
                        else NotificationVariant.info
                    ),
                    content=ToolCompletionNotificationContent(
                        job_id=self.app.security.encode_id(request.job_id) if request.job_id is not None else None,
                        implicit_collection_jobs_id=(
                            self.app.security.encode_id(request.implicit_collection_jobs_id)
                            if request.implicit_collection_jobs_id is not None
                            else None
                        ),
                        subject=self._notification_subject(job),
                        message=f"Your tool run has completed ({summary}).\n\n[View history]({link})",
                    ),
                ),
                galaxy_url=galaxy_url,
                dispatch_now=True,
            )
            # The conditional update also protects SQLite, where FOR UPDATE is
            # ignored, if two monitors both read the same unfinished request.
            claimed = session.scalar(
                update(ToolCompletionNotification)
                .where(ToolCompletionNotification.id == request_id, ToolCompletionNotification.completed.is_(False))
                .values(completed=True)
                .returning(ToolCompletionNotification.id)
            )
            if claimed is None:
                return False
            self.notification_manager.send_completion_notification(notification_request)
            return True
        finally:
            # Release locks for unfinished runs; on failure also roll back the marker.
            session.rollback()

    def _notification_subject(self, job: Job | None) -> str:
        if job is None or not job.tool_id:
            return "Tool run completed"
        tool = self.app.toolbox.get_tool(
            job.tool_id,
            tool_version=job.tool_version,
            tool_uuid=job.dynamic_tool.uuid if job.dynamic_tool is not None else None,
            user=job.user,
        )
        return f"Tool '{tool.name if tool else job.tool_id}' completed"


class ToolCompletionMonitor:
    """Run the global tool completion queue on the elected config watcher."""

    def __init__(self, manager: ToolCompletionManager):
        self.manager = manager
        self._task: IntervalTask | None = None
        self._email_task: IntervalTask | None = None
        self._lock = Lock()

    def on_role_change(self, is_leader: bool) -> None:
        with self._lock:
            if is_leader and self._task is None:
                task: IntervalTask = IntervalTask(
                    func=lambda: self.manager.monitor(task.event),
                    name="ToolCompletionMonitor",
                    interval=self.manager.app.config.workflow_completion_monitor_sleep,
                )
                self._task = task
                task.start()
                log.info("Started tool completion monitor on elected web process")
                if self.manager.app.config.smtp_server:
                    email_task: IntervalTask = IntervalTask(
                        func=lambda: self.manager.notification_manager.dispatch_completion_emails(email_task.event),
                        name="CompletionEmailDispatcher",
                        interval=self.manager.app.config.workflow_completion_monitor_sleep,
                    )
                    self._email_task = email_task
                    email_task.start()
            elif not is_leader and self._task is not None:
                if self._email_task is not None:
                    self._email_task.shutdown()
                    self._email_task = None
                self._task.shutdown()
                self._task = None
                log.info("Stopped tool completion monitor")

    def shutdown(self) -> None:
        self.on_role_change(False)
