"""Report attention and completion once per requested tool or workflow run."""

import logging
from dataclasses import dataclass
from threading import (
    Event,
    Lock,
)
from typing import Literal

from sqlalchemy import (
    func,
    or_,
    select,
    text,
    union_all,
    update,
)

from galaxy.managers.notification import NotificationManager
from galaxy.managers.run_notification_queries import (
    eligible_run_notifications_stmt,
    FINISHED_INVOCATION_STATES,
    FINISHED_JOB_STATES,
)
from galaxy.model import (
    ImplicitCollectionJobs,
    ImplicitCollectionJobsJobAssociation,
    Job,
    RunNotificationRequest,
    WorkflowInvocation,
    WorkflowInvocationStep,
    WorkflowInvocationToSubworkflowInvocationAssociation,
)
from galaxy.schema.notifications import (
    InternalNotificationCreateData,
    NotificationCreateRequest,
    NotificationRecipients,
    NotificationVariant,
    PersonalNotificationCategory,
    ToolCompletionNotificationContent,
    WorkflowCompletionNotificationContent,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.util.task import IntervalTask

log = logging.getLogger(__name__)


@dataclass
class RunStatus:
    needs_attention: bool
    counts: dict[str, int]
    population_failed: bool = False


class RunNotificationManager:
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
                    log.exception("Error delivering run notification %d", request_id)
        except Exception:
            log.exception("Error polling run notifications")
        finally:
            self.app.model.context.remove()

    def poll_pending_notifications(self, after_id: int = 0, limit: int = 100) -> list[int]:
        if not (self.app.config.enable_notification_system or self.app.config.smtp_server):
            return []
        session = self.app.model.context
        # Most polls find nothing pending, so skip the eligibility query for them.
        pending = session.scalar(
            select(RunNotificationRequest.id)
            .where(RunNotificationRequest.completed.is_(False), RunNotificationRequest.id > after_id)
            .limit(1)
        )
        if pending is None:
            return []
        if session.get_bind().dialect.name == "postgresql":
            # The planner overestimates this query by orders of magnitude, so PostgreSQL JIT-compiles it on
            # every poll. Compiling takes seconds of database CPU; the query itself runs in about a millisecond.
            session.execute(text("SET LOCAL jit = off"))
        return list(session.scalars(eligible_run_notifications_stmt(after_id, limit)))

    def check_and_notify(self, request_id: int) -> bool:
        session = self.app.model.context
        try:
            request = session.scalar(
                select(RunNotificationRequest)
                .where(RunNotificationRequest.id == request_id, RunNotificationRequest.completed.is_(False))
                .with_for_update(skip_locked=True)
            )
            if request is None:
                return False
            status = (
                self._workflow_status(request)
                if request.workflow_invocation_id is not None
                else self._tool_status(request)
            )
            if status is None:
                return False
            notification = self._build_notification(request, status)
            claim = update(RunNotificationRequest).where(
                RunNotificationRequest.id == request_id, RunNotificationRequest.completed.is_(False)
            )
            if status.needs_attention:
                claim = claim.where(RunNotificationRequest.attention_sent.is_(False)).values(attention_sent=True)
            else:
                claim = claim.values(completed=True)
            # Protect SQLite too, where FOR UPDATE is ignored. The marker and
            # notification (or SMTP queue entry) commit together.
            if session.scalar(claim.returning(RunNotificationRequest.id)) is None:
                return False
            self.notification_manager.send_completion_notification(notification)
            return True
        finally:
            session.rollback()

    def _tool_status(self, request: RunNotificationRequest) -> RunStatus | None:
        if collection_jobs := request.implicit_collection_jobs:
            needs_attention = not request.attention_sent and collection_jobs.has_job_in_states([Job.states.PAUSED])
            if not needs_attention and (
                collection_jobs.populated_state == collection_jobs.populated_states.NEW
                or collection_jobs.has_job_not_in_states(FINISHED_JOB_STATES)
            ):
                return None
            return RunStatus(
                needs_attention,
                collection_jobs.job_state_counts(),
                collection_jobs.populated_state == collection_jobs.populated_states.FAILED,
            )
        job = request.job
        if job is None:
            return None
        needs_attention = not request.attention_sent and job.state == Job.states.PAUSED
        if not needs_attention and job.state not in FINISHED_JOB_STATES:
            return None
        return RunStatus(needs_attention, {str(job.state): 1})

    def _workflow_status(self, request: RunNotificationRequest) -> RunStatus | None:
        session = self.app.model.context
        invocation = request.workflow_invocation
        assert invocation is not None and invocation.state is not None
        # Include nested invocations without loading their steps or constituent jobs.
        invocations = (
            select(WorkflowInvocation.id)
            .where(WorkflowInvocation.id == request.workflow_invocation_id)
            .cte("notification_invocations", recursive=True)
        )
        association = WorkflowInvocationToSubworkflowInvocationAssociation
        invocations = invocations.union_all(
            select(association.subworkflow_invocation_id).join(
                invocations, association.workflow_invocation_id == invocations.c.id
            )
        )
        invocation_ids = select(invocations.c.id)
        steps = (
            select(WorkflowInvocationStep)
            .where(WorkflowInvocationStep.workflow_invocation_id.in_(invocation_ids))
            .subquery()
        )
        jobs = union_all(
            select(Job.state).join(steps, steps.c.job_id == Job.id),
            select(Job.state)
            .join(ImplicitCollectionJobsJobAssociation)
            .join(
                steps,
                steps.c.implicit_collection_jobs_id == ImplicitCollectionJobsJobAssociation.implicit_collection_jobs_id,
            ),
        ).subquery()
        needs_attention = not request.attention_sent and bool(
            session.scalar(select(select(jobs.c.state).where(jobs.c.state == Job.states.PAUSED).exists()))
        )
        if not needs_attention:
            if session.scalar(select(select(jobs.c.state).where(jobs.c.state.not_in(FINISHED_JOB_STATES)).exists())):
                return None
            # A terminated root will not schedule its remaining descendants.
            if invocation.state not in (
                WorkflowInvocation.states.FAILED,
                WorkflowInvocation.states.CANCELLED,
            ):
                if session.scalar(
                    select(
                        select(WorkflowInvocation.id)
                        .where(
                            WorkflowInvocation.id.in_(invocation_ids),
                            WorkflowInvocation.state.not_in(FINISHED_INVOCATION_STATES),
                        )
                        .exists()
                    )
                ):
                    return None
                # Failed/cancelled invocations can have unscheduled steps or abandoned
                # population, but their already-created jobs must still finish above.
                unfinished_steps = (
                    select(steps.c.id)
                    .join(WorkflowInvocation, WorkflowInvocation.id == steps.c.workflow_invocation_id)
                    .outerjoin(ImplicitCollectionJobs, ImplicitCollectionJobs.id == steps.c.implicit_collection_jobs_id)
                    .where(
                        WorkflowInvocation.state.in_(
                            (WorkflowInvocation.states.SCHEDULED, WorkflowInvocation.states.COMPLETED)
                        ),
                        or_(
                            steps.c.state != WorkflowInvocationStep.states.SCHEDULED,
                            ImplicitCollectionJobs.populated_state == ImplicitCollectionJobs.populated_states.NEW,
                        ),
                    )
                )
                if session.scalar(select(unfinished_steps.exists())):
                    return None
        counts = dict(session.execute(select(jobs.c.state, func.count()).group_by(jobs.c.state)).tuples().all())
        return RunStatus(needs_attention, counts)

    def _build_notification(self, request: RunNotificationRequest, status: RunStatus) -> NotificationCreateRequest:
        encode_id = self.app.security.encode_id
        galaxy_url = self.app.config.galaxy_infrastructure_url
        event: Literal["needs_attention", "completed"] = "needs_attention" if status.needs_attention else "completed"
        outcome = "needs attention" if status.needs_attention else "completed"
        warning = status.needs_attention or bool(status.counts.get("error")) or status.population_failed
        content: ToolCompletionNotificationContent | WorkflowCompletionNotificationContent
        if invocation := request.workflow_invocation:
            stored_workflow = invocation.workflow.stored_workflow
            name = stored_workflow.name if stored_workflow else "Unknown Workflow"
            if not status.needs_attention and invocation.state in (
                invocation.states.FAILED,
                invocation.states.CANCELLED,
            ):
                outcome = "cancelled" if invocation.state == invocation.states.CANCELLED else "failed"
                warning = True
            message = f"Your workflow **{name}** {('needs attention' if status.needs_attention else 'has ' + outcome)}."
            if status.counts:
                message += "\n\n**Job Summary:**\n\n" + "\n".join(
                    f"- {state}: {count}" for state, count in sorted(status.counts.items())
                )
            if status.needs_attention:
                message += "\n\nSome jobs are paused. Review the run to continue."
            link = f"{galaxy_url or ''}/workflows/invocations/{encode_id(invocation.id)}"
            content = WorkflowCompletionNotificationContent(
                invocation_id=encode_id(invocation.id),
                event=event,
                subject=f"Workflow '{name}' {outcome}",
                message=f"{message}\n\n[View Invocation Details]({link})",
            )
            category = PersonalNotificationCategory.workflow_execution_completed
        else:
            job = (
                request.implicit_collection_jobs.representative_job
                if request.implicit_collection_jobs and status.counts
                else request.job
            )
            summary = ", ".join(f"{count} {state}" for state, count in sorted(status.counts.items())) or "0 jobs"
            if status.population_failed:
                summary += "; some jobs could not be created"
            message = f"Your tool run {('needs attention' if status.needs_attention else 'has completed')} ({summary})."
            if status.needs_attention:
                message += "\n\nSome jobs are paused. Review the run to continue."
            link = f"{galaxy_url or ''}/histories/view?id={encode_id(request.history_id)}"
            content = ToolCompletionNotificationContent(
                job_id=encode_id(request.job_id) if request.job_id is not None else None,
                implicit_collection_jobs_id=(
                    encode_id(request.implicit_collection_jobs_id)
                    if request.implicit_collection_jobs_id is not None
                    else None
                ),
                event=event,
                subject=f"{self._tool_name(job)} {outcome}",
                message=f"{message}\n\n[View history]({link})",
            )
            category = PersonalNotificationCategory.tool_execution_completed
        return NotificationCreateRequest(
            recipients=NotificationRecipients(user_ids=[request.user_id]),
            notification=InternalNotificationCreateData(
                source="galaxy",
                category=category,
                variant=NotificationVariant.warning if warning else NotificationVariant.info,
                content=content,
            ),
            galaxy_url=galaxy_url,
            dispatch_now=True,
        )

    def _tool_name(self, job: Job | None) -> str:
        if job is None or not job.tool_id:
            return "Tool run"
        tool = self.app.toolbox.get_tool(
            job.tool_id,
            tool_version=job.tool_version,
            tool_uuid=job.dynamic_tool.uuid if job.dynamic_tool is not None else None,
            user=job.user,
        )
        return f"Tool '{tool.name if tool else job.tool_id}'"


class RunNotificationMonitor:
    """Run the global run notification queue on the elected config watcher."""

    def __init__(self, manager: RunNotificationManager):
        self.manager = manager
        self._task: IntervalTask | None = None
        self._email_task: IntervalTask | None = None
        self._lock = Lock()

    def on_role_change(self, is_leader: bool) -> None:
        with self._lock:
            if is_leader and self._task is None:
                task: IntervalTask = IntervalTask(
                    func=lambda: self.manager.monitor(task.event),
                    name="RunNotificationMonitor",
                    interval=self.manager.app.config.workflow_completion_monitor_sleep,
                )
                self._task = task
                task.start()
                log.info("Started run notification monitor on elected web process")
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
                log.info("Stopped run notification monitor")

    def shutdown(self) -> None:
        self.on_role_change(False)
