import datetime

from celery import Task

from galaxy.model import CeleryUserRateLimit
from galaxy.model.scoped_session import galaxy_scoped_session


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


class GalaxyTaskUserRateLimitBeforeStart(GalaxyTaskBeforeStart):
    """
    Used when we wish to enforce a user rate limit based on
    celery_user_rate_limit config setting.
    The user_rate_limit constructor parameter is a class instance
    that implements logic specific to the type of database
    configured. i.e. For postgres we take advantage of efficiencies
    in its dialect.
    We limit executions by keeping track of the last scheduled
    time for the execution of a task by user. When a new task
    is to be executed we schedule it a certain time interval
    after the last scheduled execution of a task by this user
    by doing a task.retry.
    If the last scheduled execution was far enough in the past
    then we allow the task to run immediately.
    """

    user_rate_limit: CeleryUserRateLimit

    def __init__(
        self,
        tasks_per_user_per_sec: float,
        user_rate_limit: CeleryUserRateLimit,
        ga_scoped_session: galaxy_scoped_session,
    ):
        self.user_rate_limit = user_rate_limit
        self.task_exec_countdown_secs = 1 / tasks_per_user_per_sec
        self.ga_scoped_session = ga_scoped_session

    def __call__(self, task: Task, task_id, args, kwargs):
        if task.request.retries > 0:
            return
        usr = kwargs.get("task_user_id")
        if not usr:
            return
        now = datetime.datetime.now()
        sa_session = None
        try:
            sa_session = self.ga_scoped_session
            next_scheduled_time = self.user_rate_limit.calculate_task_start_time(
                usr, sa_session, self.task_exec_countdown_secs, now
            )
        finally:
            if sa_session:
                sa_session.remove()
        if next_scheduled_time > now:
            count_down = next_scheduled_time - now
            task.retry(countdown=count_down.total_seconds())
