import logging
from datetime import timedelta
from typing import cast

from sqlalchemy import (
    delete,
    insert,
    update,
)

from galaxy import model
from galaxy.app_unittest_utils.galaxy_mock import (
    MockApp,
    MockAppConfig,
)
from galaxy.model.dataset_collections.readiness import dataset_readiness
from galaxy.structured_app import MinimalManagerApp
from galaxy.util import now
from galaxy.util.bunch import Bunch
from galaxy.workflow.scheduling_dependencies import (
    DependencyType,
    SchedulingDependencies,
    SchedulingDependency,
)
from galaxy.workflow.scheduling_manager import (
    WorkflowRequestMonitor,
    WorkflowSchedulingManager,
)
from .workflow_support import SchedulingHarness

NOTHING_PENDING = SchedulingDependencies(tracked=frozenset(), untracked=(), more_work=False)


def pending(*dependencies: SchedulingDependency, untracked=(), more_work=False) -> SchedulingDependencies:
    return SchedulingDependencies(tracked=frozenset(dependencies), untracked=tuple(untracked), more_work=more_work)


class RecordingScheduler:
    def __init__(self, *results: SchedulingDependencies):
        self.results = list(results) or [NOTHING_PENDING]
        self.scheduled = 0

    def schedule(self, workflow_invocation):
        self.scheduled += 1
        return self.results.pop(0) if len(self.results) > 1 else self.results[0]


def test_waits_for_tracked_job_to_finish():
    harness = SchedulingHarness()
    job = model.Job()
    job.state = model.Job.states.QUEUED
    job_id = harness.persist(job)
    scheduler = RecordingScheduler(pending(SchedulingDependency(DependencyType.JOB, job_id)))

    assert harness.attempt(scheduler) == 1
    assert harness.attempt(scheduler) == 1

    job.state = model.Job.states.DELETING
    harness.persist(job)
    assert harness.attempt(scheduler) == 2


def test_failed_collection_population_reschedules():
    harness = SchedulingHarness()
    collection = model.DatasetCollection(collection_type="list", populated=False)
    collection_id = harness.persist(collection)
    scheduler = RecordingScheduler(pending(SchedulingDependency(DependencyType.DATASET_COLLECTION, collection_id)))

    assert harness.attempt(scheduler) == 1
    assert harness.attempt(scheduler) == 1

    collection.populated_state = model.DatasetCollection.populated_states.FAILED
    harness.persist(collection)
    assert harness.attempt(scheduler) == 2


def test_pending_dataset_becoming_ready_reschedules():
    harness = SchedulingHarness()
    dataset = model.Dataset()
    dataset.state = model.Dataset.states.RUNNING
    hda = model.HistoryDatasetAssociation(dataset=dataset)
    hda.history = harness.history
    hda_id = harness.persist(hda)
    scheduler = RecordingScheduler(pending(SchedulingDependency(DependencyType.HDA, hda_id)))

    assert harness.attempt(scheduler) == 1
    assert harness.attempt(scheduler) == 1

    dataset.state = model.Dataset.states.ERROR
    harness.persist(dataset)
    assert harness.attempt(scheduler) == 2


def test_untracked_delay_reschedules_every_iteration(caplog):
    harness = SchedulingHarness()
    scheduler = RecordingScheduler(pending(untracked=["tool [special] inputs are not ready"]))

    with caplog.at_level(logging.WARNING, logger="galaxy.workflow.scheduling_manager"):
        assert harness.attempt(scheduler) == 1
        assert harness.attempt(scheduler) == 2
        assert harness.attempt(scheduler) == 3
    warnings = [r for r in caplog.records if "cannot be tracked" in r.getMessage()]
    assert len(warnings) == 1
    assert "tool [special] inputs are not ready" in warnings[0].getMessage()


def test_more_work_reschedules_without_waiting():
    harness = SchedulingHarness()
    scheduler = RecordingScheduler(pending(more_work=True), NOTHING_PENDING)

    assert harness.attempt(scheduler) == 1
    assert harness.attempt(scheduler) == 2
    assert harness.attempt(scheduler) == 2


def test_history_change_committed_after_attempt_started_reschedules():
    harness = SchedulingHarness()
    scheduler = RecordingScheduler(NOTHING_PENDING)

    assert harness.attempt(scheduler) == 1
    assert harness.attempt(scheduler) == 1

    # A transaction that flushed before the last attempt started but committed after it.
    harness.set_history_update_time(now() - timedelta(seconds=30))
    assert harness.attempt(scheduler) == 2


def test_reschedules_after_backfill_interval_without_changes():
    harness = SchedulingHarness()
    job = model.Job()
    job.state = model.Job.states.QUEUED
    job_id = harness.persist(job)
    scheduler = RecordingScheduler(pending(SchedulingDependency(DependencyType.JOB, job_id)))

    assert harness.attempt(scheduler) == 1
    assert harness.attempt(scheduler) == 1

    tracking = harness.monitor.update_time_tracking_dict[harness.invocation_id]
    stale = tracking.schedule_time - harness.monitor.timedelta - timedelta(seconds=1)
    harness.monitor.update_time_tracking_dict[harness.invocation_id] = tracking._replace(schedule_time=stale)
    assert harness.attempt(scheduler) == 2
    assert harness.attempt(scheduler) == 2


def _readiness_dependency(harness):
    hda = model.HistoryDatasetAssociation(dataset=model.Dataset(state=model.Dataset.states.RUNNING))
    hda.history = harness.history
    harness.persist(hda)
    return hda, SchedulingDependency(DependencyType.HDA, hda.id, dataset_readiness(hda))


def test_readiness_snapshot_ignores_moves_between_non_ready_states():
    harness = SchedulingHarness()
    hda, dependency = _readiness_dependency(harness)
    scheduler = RecordingScheduler(pending(dependency))

    assert harness.attempt(scheduler) == 1
    for state in ("queued", "setting_metadata", "ok"):
        harness.session.execute(update(model.Dataset).where(model.Dataset.id == hda.dataset_id).values(state=state))
        harness.session.commit()
        harness.attempt(scheduler)
    assert scheduler.scheduled == 2


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
