from datetime import timedelta
from typing import cast

from sqlalchemy import (
    delete,
    insert,
)

from galaxy import model
from galaxy.app_unittest_utils.galaxy_mock import (
    MockApp,
    MockAppConfig,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.util import now
from galaxy.util.bunch import Bunch
from galaxy.workflow.scheduling_manager import (
    WorkflowRequestMonitor,
    WorkflowSchedulingManager,
)


class RecordingScheduler:
    def __init__(self):
        self.scheduled = 0

    def schedule(self, workflow_invocation):
        self.scheduled += 1


def _set_history_update_time(session, history_id, update_time):
    session.execute(delete(model.HistoryAudit).where(model.HistoryAudit.history_id == history_id))
    session.execute(insert(model.HistoryAudit).values(history_id=history_id, update_time=update_time))
    session.commit()


def test_reschedules_when_history_update_committed_after_attempt_started():
    app = MockApp(
        config=MockAppConfig(maximum_workflow_invocation_duration=0, history_local_serial_workflow_scheduling=False)
    )
    app.job_config = Bunch(self_handler_tags=[])
    monitor = WorkflowRequestMonitor(
        cast(MinimalManagerApp, app),
        cast(WorkflowSchedulingManager, Bunch(default_handler_id="main", handler_assignment_methods=[])),
    )
    attempt_schedule = monitor._WorkflowRequestMonitor__attempt_schedule  # type: ignore[attr-defined]

    session = app.model.context
    history = model.History()
    invocation = model.WorkflowInvocation()
    invocation.history = history
    invocation.workflow = model.Workflow()
    invocation.state = model.WorkflowInvocation.states.READY
    session.add(invocation)
    session.commit()
    history_id, invocation_id = history.id, invocation.id
    _set_history_update_time(session, history_id, now() - timedelta(seconds=60))

    scheduler = RecordingScheduler()
    attempt_schedule(invocation_id, scheduler)
    assert scheduler.scheduled == 1

    attempt_schedule(invocation_id, scheduler)
    assert scheduler.scheduled == 1

    # A transaction that flushed before the last attempt started but committed after it.
    _set_history_update_time(app.model.context, history_id, now() - timedelta(seconds=30))
    attempt_schedule(invocation_id, scheduler)
    assert scheduler.scheduled == 2
