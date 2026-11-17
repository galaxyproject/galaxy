"""Select runs that can produce a notification before applying the polling limit."""

from collections.abc import Sequence

from sqlalchemy import (
    case,
    func,
    literal,
    or_,
    select,
    union_all,
)
from sqlalchemy.sql import (
    ColumnElement,
    Select,
)
from sqlalchemy.sql.selectable import CTE

from galaxy.model import (
    ImplicitCollectionJobs,
    ImplicitCollectionJobsJobAssociation,
    Job,
    RunNotificationRequest,
    WorkflowInvocation,
    WorkflowInvocationStep,
    WorkflowInvocationToSubworkflowInvocationAssociation,
)

# Paused jobs need intervention but must not consume the final notification.
FINISHED_JOB_STATES = tuple(state for state in Job.settled_states if state != Job.states.PAUSED)
UNFINISHED_JOB_STATES = tuple(state for state in Job.states if state not in FINISHED_JOB_STATES)
FINISHED_INVOCATION_STATES = (
    WorkflowInvocation.states.SCHEDULED,
    WorkflowInvocation.states.COMPLETED,
    WorkflowInvocation.states.FAILED,
    WorkflowInvocation.states.CANCELLED,
)


def _job_matches(sources: CTE, states: Sequence[str]) -> ColumnElement[bool]:
    # Scalar probes preserve LIMIT 1 on PostgreSQL and also work on SQLite.
    # A group with a million paused jobs needs only one matching job here.
    job = (
        select(literal(1))
        .select_from(Job)
        .where(Job.id == sources.c.job_id, Job.state.in_(states))
        .correlate(sources)
        .limit(1)
        .scalar_subquery()
    )
    group = (
        select(literal(1))
        .select_from(ImplicitCollectionJobsJobAssociation)
        .join(Job)
        .where(
            ImplicitCollectionJobsJobAssociation.implicit_collection_jobs_id == sources.c.implicit_collection_jobs_id,
            Job.state.in_(states),
        )
        .correlate(sources)
        .limit(1)
        .scalar_subquery()
    )
    return case((sources.c.job_id.is_not(None), job), else_=group).is_not(None)


def _any(condition: ColumnElement[bool]) -> ColumnElement[int]:
    """Portable boolean aggregation over invocation steps, not constituent jobs."""
    return func.max(case((condition, 1), else_=0))


def eligible_run_notifications_stmt(after_id: int = 0, limit: int = 100) -> Select[tuple[int]]:
    pending = (
        select(
            RunNotificationRequest.id,
            RunNotificationRequest.attention_sent,
            RunNotificationRequest.job_id,
            RunNotificationRequest.implicit_collection_jobs_id,
            RunNotificationRequest.workflow_invocation_id,
        )
        .where(RunNotificationRequest.completed.is_(False), RunNotificationRequest.id > after_id)
        .cte("pending_run_notifications")
    )
    # Expand the pending roots together; unrelated invocation trees are never visited.
    invocations = (
        select(pending.c.id.label("request_id"), WorkflowInvocation.id, WorkflowInvocation.state)
        .join(WorkflowInvocation, WorkflowInvocation.id == pending.c.workflow_invocation_id)
        .cte("notification_invocations", recursive=True)
    )
    association = WorkflowInvocationToSubworkflowInvocationAssociation
    invocations = invocations.union_all(
        select(invocations.c.request_id, WorkflowInvocation.id, WorkflowInvocation.state)
        .select_from(invocations)
        .join(association, association.workflow_invocation_id == invocations.c.id)
        .join(WorkflowInvocation, WorkflowInvocation.id == association.subworkflow_invocation_id)
    )
    steps = (
        select(
            invocations.c.request_id,
            invocations.c.state.label("invocation_state"),
            WorkflowInvocationStep.state,
            WorkflowInvocationStep.job_id,
            WorkflowInvocationStep.implicit_collection_jobs_id,
        )
        .join(WorkflowInvocationStep, WorkflowInvocationStep.workflow_invocation_id == invocations.c.id)
        .cte("notification_steps")
    )
    sources = union_all(
        select(
            pending.c.id.label("request_id"),
            pending.c.attention_sent,
            steps.c.job_id,
            steps.c.implicit_collection_jobs_id,
        )
        .join(steps, steps.c.request_id == pending.c.id)
        .where(or_(steps.c.job_id.is_not(None), steps.c.implicit_collection_jobs_id.is_not(None))),
        select(pending.c.id, pending.c.attention_sent, pending.c.job_id, pending.c.implicit_collection_jobs_id).where(
            pending.c.implicit_collection_jobs_id.is_not(None)
        ),
    ).cte("notification_job_sources")
    job_flags = (
        select(
            sources.c.request_id,
            _any(_job_matches(sources, UNFINISHED_JOB_STATES)).label("unfinished"),
            # A running job found by the first probe must not hide a later paused job.
            _any(
                case((sources.c.attention_sent.is_(False), _job_matches(sources, [Job.states.PAUSED])), else_=False)
            ).label("paused"),
        )
        .group_by(sources.c.request_id)
        .cte("notification_job_flags")
    )
    invocation_flags = (
        select(
            invocations.c.request_id,
            _any(invocations.c.state.not_in(FINISHED_INVOCATION_STATES)).label("unfinished"),
        )
        .group_by(invocations.c.request_id)
        .cte("notification_invocation_flags")
    )
    step_flags = (
        select(
            steps.c.request_id,
            _any(
                steps.c.invocation_state.in_((WorkflowInvocation.states.SCHEDULED, WorkflowInvocation.states.COMPLETED))
                & or_(
                    steps.c.state != WorkflowInvocationStep.states.SCHEDULED,
                    ImplicitCollectionJobs.populated_state == ImplicitCollectionJobs.populated_states.NEW,
                )
            ).label("unfinished"),
        )
        .outerjoin(ImplicitCollectionJobs, ImplicitCollectionJobs.id == steps.c.implicit_collection_jobs_id)
        .group_by(steps.c.request_id)
        .cte("notification_step_flags")
    )
    workflow_requests = (
        select(pending.c.id)
        .join(WorkflowInvocation, WorkflowInvocation.id == pending.c.workflow_invocation_id)
        .outerjoin(job_flags, job_flags.c.request_id == pending.c.id)
        .outerjoin(invocation_flags, invocation_flags.c.request_id == pending.c.id)
        .outerjoin(step_flags, step_flags.c.request_id == pending.c.id)
        .where(
            or_(
                job_flags.c.paused == 1,
                (func.coalesce(job_flags.c.unfinished, 0) == 0)
                & or_(
                    WorkflowInvocation.state.in_(
                        (WorkflowInvocation.states.FAILED, WorkflowInvocation.states.CANCELLED)
                    ),
                    (func.coalesce(invocation_flags.c.unfinished, 0) == 0)
                    & (func.coalesce(step_flags.c.unfinished, 0) == 0),
                ),
            )
        )
    )
    tool_requests = (
        select(pending.c.id)
        .join(Job, Job.id == pending.c.job_id)
        .where(
            or_(
                Job.state.in_(FINISHED_JOB_STATES),
                pending.c.attention_sent.is_(False) & (Job.state == Job.states.PAUSED),
            )
        )
    )
    mapped_requests = (
        select(pending.c.id)
        .join(ImplicitCollectionJobs, ImplicitCollectionJobs.id == pending.c.implicit_collection_jobs_id)
        .outerjoin(job_flags, job_flags.c.request_id == pending.c.id)
        .where(
            or_(
                job_flags.c.paused == 1,
                (func.coalesce(job_flags.c.unfinished, 0) == 0)
                & (ImplicitCollectionJobs.populated_state != ImplicitCollectionJobs.populated_states.NEW),
            )
        )
    )
    eligible = union_all(workflow_requests, tool_requests, mapped_requests).subquery()
    return select(eligible.c.id).order_by(eligible.c.id).limit(limit)
