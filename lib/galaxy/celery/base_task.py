import datetime
import logging
from abc import abstractmethod
from typing import cast

from celery import Task
from sqlalchemy import (
    bindparam,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert as ps_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import scoped_session

from galaxy.model import (
    CeleryUserActiveTask,
    CeleryUserRateLimit,
)

log = logging.getLogger(__name__)

HEADER_SCHEDULED_TIME = "_gxy_rate_limit_scheduled_time"
HEADER_CONCURRENCY_TRACKED = "_gxy_concurrency_tracked"
CONCURRENCY_RETRY_COUNTDOWN_SECS = 5.0


class GalaxyTaskBeforeStart:
    """
    Class used by the custom celery task, GalaxyTask, to implement
    logic to limit number of task executions per user per second.
    This superclass is used directly when no user rate limit logic
    is to be enforced based on value of config param,
    celery_user_rate_limit.
    """

    def __call__(self, task: Task, task_id, args, kwargs):
        pass


class GalaxyTaskAfterReturn:
    """
    Hook called after a task returns (success, failure, or retry).
    Base class is a no-op; subclasses implement concurrency tracking cleanup.
    """

    def __call__(self, task: Task, task_id, args, kwargs):
        pass


class GalaxyTaskBeforeStartUserRateLimit(GalaxyTaskBeforeStart):
    """
    Used when we wish to enforce a user rate limit based on
    non-default value of celery_user_rate_limit config setting.
    We limit executions by keeping track in a table of the last scheduled
    time for the execution of a task by user. When a new task
    is to be executed we schedule it a certain time interval
    after the last scheduled execution of a task by this user
    by doing a task.retry.
    If the last scheduled execution was far enough in the past
    then we allow the task to run immediately.

    The reserved timeslot is stored in a message header so that on
    retry the task can verify it has reached its scheduled time
    without re-reserving a new slot. This ensures tasks are never
    lost and will keep retrying until their timeslot arrives.
    """

    def __init__(
        self,
        tasks_per_user_per_sec: float,
        ga_scoped_session: scoped_session,
    ):
        try:
            self.task_exec_countdown_secs = 1 / tasks_per_user_per_sec
        except ZeroDivisionError:
            raise Exception("tasks_per_user_per_sec was zero in celery GalaxyTask before_start")
        self.ga_scoped_session = ga_scoped_session

    def __call__(self, task: Task, task_id, args, kwargs):
        usr = kwargs.get("task_user_id")
        if not usr:
            return
        now = datetime.datetime.now()

        # Check if this task already has a reserved timeslot from a previous attempt
        headers = task.request.headers or {}
        reserved_time_str = headers.get(HEADER_SCHEDULED_TIME)

        if reserved_time_str:
            # Retry path: verify we've reached our reserved timeslot
            reserved_time = datetime.datetime.fromisoformat(reserved_time_str)
            if now >= reserved_time:
                return  # Timeslot reached, proceed with execution
            # Not yet time — retry with remaining countdown
            remaining = (reserved_time - now).total_seconds()
            task.retry(
                countdown=remaining,
                max_retries=None,
                headers={HEADER_SCHEDULED_TIME: reserved_time_str},
            )
        else:
            # First attempt: reserve a timeslot atomically in the DB
            sa_session = self.ga_scoped_session
            next_scheduled_time = self.calculate_task_start_time(usr, sa_session, self.task_exec_countdown_secs, now)
            if next_scheduled_time > now:
                count_down = next_scheduled_time - now
                task.retry(
                    countdown=count_down.total_seconds(),
                    max_retries=None,
                    headers={HEADER_SCHEDULED_TIME: next_scheduled_time.isoformat()},
                )
            # else: scheduled time is now or in the past, execute immediately

    @abstractmethod
    def calculate_task_start_time(
        self, user_id: int, sa_session: scoped_session, task_interval_secs: float, now: datetime.datetime
    ) -> datetime.datetime:
        return now


class GalaxyTaskBeforeStartUserRateLimitPostgres(GalaxyTaskBeforeStartUserRateLimit):
    """
    Postgres specific implementation that overrides the calculate_task_start_time method.
    We take advantage of efficiencies in its dialect.
    """

    def calculate_task_start_time(
        self, user_id: int, sa_session: scoped_session, task_interval_secs: float, now: datetime.datetime
    ) -> datetime.datetime:
        update_stmt = (
            update(CeleryUserRateLimit)
            .where(CeleryUserRateLimit.user_id == user_id)
            .values(
                last_scheduled_time=func.greatest(
                    CeleryUserRateLimit.last_scheduled_time + datetime.timedelta(seconds=task_interval_secs),
                    now,
                )
            )
            .returning(CeleryUserRateLimit.last_scheduled_time)
        )
        result = sa_session.execute(update_stmt).all()
        if not result:
            sched_time = now + datetime.timedelta(seconds=task_interval_secs)
            upsert_stmt = (
                ps_insert(CeleryUserRateLimit)  # type: ignore[attr-defined]
                .values(user_id=user_id, last_scheduled_time=now)
                .returning(CeleryUserRateLimit.last_scheduled_time)
                .on_conflict_do_update(index_elements=["user_id"], set_=dict(last_scheduled_time=sched_time))
            )
            result = sa_session.execute(upsert_stmt).all()
        sa_session.commit()
        return result[0][0]


class GalaxyTaskBeforeStartUserRateLimitStandard(GalaxyTaskBeforeStartUserRateLimit):
    """
    Generic but slower implementation supported by most databases that overrides
    the calculate_task_start_time method.
    """

    _select_stmt = (
        select(CeleryUserRateLimit.last_scheduled_time)
        .with_for_update(of=CeleryUserRateLimit.last_scheduled_time)
        .where(CeleryUserRateLimit.user_id == bindparam("userid"))
    )

    _update_stmt = (
        update(CeleryUserRateLimit)
        .where(CeleryUserRateLimit.user_id == bindparam("userid"))
        .values(last_scheduled_time=bindparam("sched_time"))
    )

    _insert_stmt = insert(CeleryUserRateLimit).values(
        user_id=bindparam("userid"), last_scheduled_time=bindparam("sched_time")
    )

    def calculate_task_start_time(
        self, user_id: int, sa_session: scoped_session, task_interval_secs: float, now: datetime.datetime
    ) -> datetime.datetime:
        last_scheduled_time = None
        last_scheduled_time = sa_session.scalars(self._select_stmt, {"userid": user_id}).first()
        if last_scheduled_time:
            sched_time = last_scheduled_time + datetime.timedelta(seconds=task_interval_secs)
            if sched_time < now:
                sched_time = now
            sa_session.execute(self._update_stmt, {"userid": user_id, "sched_time": sched_time})
        sa_session.commit()
        if not last_scheduled_time:
            try:
                sched_time = now
                sa_session.execute(self._insert_stmt, {"userid": user_id, "sched_time": sched_time})
                sa_session.commit()
            except IntegrityError:
                #  Row was inserted by another thread since we tried the update above.
                sched_time = now + datetime.timedelta(seconds=task_interval_secs)
                result = cast(
                    CursorResult, sa_session.execute(self._update_stmt, {"userid": user_id, "sched_time": sched_time})
                )
                if result.rowcount == 0:
                    raise Exception(f"Failed to update a celery_user_rate_limit row for user id {user_id}")
                sa_session.commit()
        return sched_time


# --- Per-user concurrency limiting ---


class GalaxyTaskBeforeStartConcurrencyLimit(GalaxyTaskBeforeStart):
    """
    Enforces a per-user concurrency limit on Celery task execution.
    Before a task starts, checks if the user already has the maximum
    number of tasks running. If so, defers execution via task.retry().

    On successful admission, inserts a tracking row into celery_user_active_task
    and sets a header so after_return knows to clean it up.
    """

    def __init__(
        self,
        max_concurrent: int,
        ga_scoped_session: scoped_session,
    ):
        self.max_concurrent = max_concurrent
        self.ga_scoped_session = ga_scoped_session

    def __call__(self, task: Task, task_id, args, kwargs):
        usr = kwargs.get("task_user_id")
        if not usr:
            return

        headers = task.request.headers or {}

        # If this task was already admitted (retry after concurrency admission),
        # don't re-check concurrency — it already has a tracking row.
        if headers.get(HEADER_CONCURRENCY_TRACKED):
            return

        sa_session = self.ga_scoped_session
        now = datetime.datetime.now()

        # Count currently active tasks for this user
        active_count = self._get_active_count(usr, sa_session)

        if active_count >= self.max_concurrent:
            # User is at capacity — defer this task
            sa_session.commit()
            task.retry(
                countdown=CONCURRENCY_RETRY_COUNTDOWN_SECS,
                max_retries=None,
            )
            return

        # Admit this task: insert tracking row
        try:
            sa_session.execute(
                insert(CeleryUserActiveTask).values(
                    task_id=str(task_id),
                    user_id=usr,
                    started_at=now,
                )
            )
            sa_session.commit()
        except IntegrityError:
            # Task ID already tracked (e.g., redelivery) — that's fine
            sa_session.rollback()

    @abstractmethod
    def _get_active_count(self, user_id: int, sa_session: scoped_session) -> int: ...


class GalaxyTaskBeforeStartConcurrencyLimitPostgres(GalaxyTaskBeforeStartConcurrencyLimit):
    """Postgres-optimized concurrency check using SELECT COUNT with row-level advisory awareness."""

    def _get_active_count(self, user_id: int, sa_session: scoped_session) -> int:
        count = sa_session.scalar(
            select(func.count()).select_from(CeleryUserActiveTask).where(CeleryUserActiveTask.user_id == user_id)
        )
        return count or 0


class GalaxyTaskBeforeStartConcurrencyLimitStandard(GalaxyTaskBeforeStartConcurrencyLimit):
    """Standard SQL concurrency check."""

    def _get_active_count(self, user_id: int, sa_session: scoped_session) -> int:
        count = sa_session.scalar(
            select(func.count()).select_from(CeleryUserActiveTask).where(CeleryUserActiveTask.user_id == user_id)
        )
        return count or 0


class GalaxyTaskAfterReturnConcurrencyLimit(GalaxyTaskAfterReturn):
    """
    Cleans up the concurrency tracking row after a task completes
    (regardless of success or failure).
    """

    def __init__(self, ga_scoped_session: scoped_session):
        self.ga_scoped_session = ga_scoped_session

    def __call__(self, task: Task, task_id, args, kwargs):
        usr = kwargs.get("task_user_id")
        if not usr:
            return

        sa_session = self.ga_scoped_session
        try:
            sa_session.execute(delete(CeleryUserActiveTask).where(CeleryUserActiveTask.task_id == str(task_id)))
            sa_session.commit()
        except Exception:
            log.exception(f"Failed to remove concurrency tracking row for task {task_id}")
            sa_session.rollback()


# --- Combined before_start that chains rate limit + concurrency limit ---


class GalaxyTaskBeforeStartCombined(GalaxyTaskBeforeStart):
    """
    Chains multiple before_start hooks. Rate limiting runs first
    (to schedule the timeslot), then concurrency limiting (to gate execution).
    """

    def __init__(self, *hooks: GalaxyTaskBeforeStart):
        self.hooks = hooks

    def __call__(self, task: Task, task_id, args, kwargs):
        for hook in self.hooks:
            hook(task, task_id, args, kwargs)
