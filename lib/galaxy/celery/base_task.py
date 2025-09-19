import datetime
from abc import abstractmethod

from celery import Task
from sqlalchemy import (
    bindparam,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import insert as ps_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import scoped_session

from galaxy.model import CeleryUserRateLimit


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
        if task.request.retries > 0:
            return
        usr = kwargs.get("task_user_id")
        if not usr:
            return
        now = datetime.datetime.now()
        sa_session = self.ga_scoped_session
        next_scheduled_time = self.calculate_task_start_time(usr, sa_session, self.task_exec_countdown_secs, now)
        if next_scheduled_time > now:
            count_down = next_scheduled_time - now
            task.retry(countdown=count_down.total_seconds())

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
            .values(last_scheduled_time=text("greatest(last_scheduled_time + ':interval second', :now)"))
            .returning(CeleryUserRateLimit.last_scheduled_time)
        )
        result = sa_session.execute(update_stmt, {"interval": task_interval_secs, "now": now}).all()
        if not result:
            sched_time = now + datetime.timedelta(seconds=task_interval_secs)
            upsert_stmt = (
                ps_insert(CeleryUserRateLimit)  # type:ignore[attr-defined]
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
                result = sa_session.execute(self._update_stmt, {"userid": user_id, "sched_time": sched_time})
                if result.rowcount == 0:
                    raise Exception(f"Failed to update a celery_user_rate_limit row for user id {user_id}")
                sa_session.commit()
        return sched_time
