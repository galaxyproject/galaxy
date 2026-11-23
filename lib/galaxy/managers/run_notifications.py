"""Report attention and completion once per requested tool or workflow run."""

import heapq
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from threading import (
    Event,
    Lock,
)
from time import monotonic
from typing import Literal

from sqlalchemy import (
    func,
    or_,
    select,
    union_all,
    update,
)

from galaxy.managers.notification import NotificationManager
from galaxy.model import (
    History,
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

# Paused jobs need intervention but must not consume the final notification.
FINISHED_JOB_STATES = tuple(state for state in Job.settled_states if state != Job.states.PAUSED)
FINISHED_INVOCATION_STATES = (
    WorkflowInvocation.states.SCHEDULED,
    WorkflowInvocation.states.COMPLETED,
    WorkflowInvocation.states.FAILED,
    WorkflowInvocation.states.CANCELLED,
)
# An unfinished run is checked again after a tenth of the time it has been pending: a finished run is noticed
# within about 10% of its runtime, and a run that takes hours costs a few checks per hour.
CHECK_INTERVAL_FRACTION = 0.1
MAX_CHECK_INTERVAL = 300
# Once told about paused jobs, the user must act before the run can finish, and most paused runs are never
# resumed. Their checks back off again from the attention notification, up to hourly: a run resumed soon after
# is still noticed quickly, and the ever-growing backlog of abandoned ones stays cheap.
WAITING_CHECK_INTERVAL = 3600
# New requests are found by id, but they can commit out of id order and other processes can complete them.
RELOAD_INTERVAL = 300


# What a check did, and so when the request needs checking again.
CheckResult = Literal["pending", "waiting", "attention_sent", "completed", "closed"]


@dataclass
class RunStatus:
    needs_attention: bool
    counts: dict[str, int]
    population_failed: bool = False


class CheckSchedule:
    """When to check each pending request next, kept in memory by the elected monitor."""

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self.max_id = 0
        self.reload_at = 0.0
        self._heap: list[tuple[float, int]] = []
        # Request id to (backoff start, next check); heap entries that disagree are stale.
        self._pending: dict[int, tuple[float, float]] = {}

    def add(self, request_ids: Iterable[int], now: float, first_seen: float | None = None) -> None:
        for request_id in request_ids:
            self.max_id = max(self.max_id, request_id)
            if request_id not in self._pending:
                self._pending[request_id] = (now if first_seen is None else first_seen, now)
                heapq.heappush(self._heap, (now, request_id))

    def reload(self, request_ids: Iterable[int], now: float) -> None:
        request_ids = set(request_ids)
        for request_id in self._pending.keys() - request_ids:
            del self._pending[request_id]
        # Requests found after an election may have been pending for days: check them once, then at the
        # longest interval, rather than at the shortest interval all at once.
        unknown_age = None if self.reload_at else now - WAITING_CHECK_INTERVAL / CHECK_INTERVAL_FRACTION
        self.add(request_ids, now, first_seen=unknown_age)
        self.reload_at = now + RELOAD_INTERVAL

    def pop_due(self, now: float) -> int | None:
        while self._heap and self._heap[0][0] <= now:
            check_at, request_id = heapq.heappop(self._heap)
            if request_id in self._pending and self._pending[request_id][1] == check_at:
                return request_id
        return None

    def reschedule(self, request_id: int, now: float, waiting: bool = False, restart: bool = False) -> None:
        since = now if restart else self._pending[request_id][0]
        longest = WAITING_CHECK_INTERVAL if waiting else MAX_CHECK_INTERVAL
        interval = min(longest, max(self.min_interval, (now - since) * CHECK_INTERVAL_FRACTION))
        self._pending[request_id] = (since, now + interval)
        heapq.heappush(self._heap, (now + interval, request_id))

    def discard(self, request_id: int) -> None:
        self._pending.pop(request_id, None)


class RunNotificationManager:
    def __init__(self, app: MinimalManagerApp, notification_manager: NotificationManager):
        self.app = app
        self.notification_manager = notification_manager
        self._schedule: CheckSchedule | None = None

    def reset_schedule(self) -> None:
        """Forget the schedule of a previous term as leader; requests may have changed meanwhile."""
        self._schedule = None

    def monitor(self, stop_event: Event | None = None) -> None:
        if not (self.app.config.enable_notification_system or self.app.config.smtp_server):
            return
        if self._schedule is None:
            self._schedule = CheckSchedule(self.app.config.workflow_completion_monitor_sleep)
        schedule = self._schedule
        try:
            self._load_pending(schedule)
            now = monotonic()
            while not (stop_event is not None and stop_event.is_set()):
                request_id = schedule.pop_due(now)
                if request_id is None:
                    break
                result: CheckResult = "pending"
                try:
                    result = self._notify(request_id)
                except Exception:
                    log.exception("Error delivering run notification %d", request_id)
                if result in ("completed", "closed"):
                    schedule.discard(request_id)
                else:
                    schedule.reschedule(
                        request_id,
                        monotonic(),
                        waiting=result in ("waiting", "attention_sent"),
                        restart=result == "attention_sent",
                    )
        except Exception:
            log.exception("Error polling run notifications")
        finally:
            self.app.model.context.remove()

    def _load_pending(self, schedule: CheckSchedule) -> None:
        session = self.app.model.context
        pending = select(RunNotificationRequest.id).where(RunNotificationRequest.completed.is_(False))
        now = monotonic()
        if now >= schedule.reload_at:
            schedule.reload(session.scalars(pending), now)
        else:
            schedule.add(session.scalars(pending.where(RunNotificationRequest.id > schedule.max_id)), now)
        session.rollback()

    def check_and_notify(self, request_id: int) -> bool:
        return self._notify(request_id) in ("attention_sent", "completed")

    def _notify(self, request_id: int) -> CheckResult:
        """Send the notification the request is ready for, if any."""
        session = self.app.model.context
        try:
            row = session.execute(
                select(RunNotificationRequest, History.deleted)
                .join(History, History.id == RunNotificationRequest.history_id)
                .where(RunNotificationRequest.id == request_id, RunNotificationRequest.completed.is_(False))
                .with_for_update(skip_locked=True, of=RunNotificationRequest)
            ).first()
            if row is None:
                return "pending"
            request, history_deleted = row
            if history_deleted:
                # Nobody is waiting for a run in a deleted history, and its paused jobs stay paused forever.
                request.completed = True
                session.commit()
                return "closed"
            status = (
                self._workflow_status(request)
                if request.workflow_invocation_id is not None
                else self._tool_status(request)
            )
            if status is None:
                return "waiting" if request.attention_sent else "pending"
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
                return "pending"
            self.notification_manager.send_completion_notification(notification)
            return "attention_sent" if status.needs_attention else "completed"
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
        # Fetch the ids: PostgreSQL cannot estimate a recursive CTE and would join every mapped-over job first.
        invocation_ids = session.scalars(select(invocations.c.id)).all()
        step = WorkflowInvocationStep
        in_workflow = step.workflow_invocation_id.in_(invocation_ids)
        jobs = union_all(
            select(Job.state).join(step, step.job_id == Job.id).where(in_workflow),
            select(Job.state)
            .join(ImplicitCollectionJobsJobAssociation)
            .join(
                step,
                step.implicit_collection_jobs_id == ImplicitCollectionJobsJobAssociation.implicit_collection_jobs_id,
            )
            # Implied by the join, but without it PostgreSQL scans every mapped-over job for workflows without any.
            .where(in_workflow, step.implicit_collection_jobs_id.is_not(None)),
        ).subquery()
        needs_attention = not request.attention_sent and bool(
            session.scalar(select(select(jobs.c.state).where(jobs.c.state == Job.states.PAUSED).exists()))
        )
        if not needs_attention:
            # A terminated root will not schedule its remaining descendants.
            terminated = invocation.state in (WorkflowInvocation.states.FAILED, WorkflowInvocation.states.CANCELLED)
            # Most unfinished runs are still scheduling, which is the cheapest check.
            if not terminated and session.scalar(
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
            if session.scalar(select(select(jobs.c.state).where(jobs.c.state.not_in(FINISHED_JOB_STATES)).exists())):
                return None
            # Failed/cancelled invocations can have unscheduled steps or abandoned
            # population, but their already-created jobs must still finish above.
            unfinished_steps = (
                select(step.id)
                .join(WorkflowInvocation, WorkflowInvocation.id == step.workflow_invocation_id)
                .outerjoin(ImplicitCollectionJobs, ImplicitCollectionJobs.id == step.implicit_collection_jobs_id)
                .where(
                    in_workflow,
                    WorkflowInvocation.state.in_(
                        (WorkflowInvocation.states.SCHEDULED, WorkflowInvocation.states.COMPLETED)
                    ),
                    or_(
                        step.state != step.states.SCHEDULED,
                        ImplicitCollectionJobs.populated_state == ImplicitCollectionJobs.populated_states.NEW,
                    ),
                )
            )
            if not terminated and session.scalar(select(unfinished_steps.exists())):
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
                self.manager.reset_schedule()
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
