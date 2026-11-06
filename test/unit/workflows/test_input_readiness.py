"""Workflow-level regressions for input waits that must not replay unchanged work."""

from typing import cast

import pytest

from galaxy import model
from galaxy.app_unittest_utils.galaxy_mock import MockTrans
from galaxy.model.unittest_utils.model_testing_utils import create_and_drop_database
from galaxy.tool_util.parser import get_tool_source
from galaxy.tools import create_tool_from_source
from galaxy.work.context import WorkRequestContext
from galaxy.workflow import modules
from .workflow_support import (
    MockToolbox,
    SchedulingHarness,
)


@pytest.fixture
def harness(url_factory):
    database = url_factory()
    with create_and_drop_database(database):
        harness = SchedulingHarness(database_connection=database)
        try:
            yield harness
        finally:
            harness.session.remove()
            harness.app.model.engine.dispose()


def collection_input(harness, states=("running", "ok"), extension="txt", nested=False):
    leaves = model.DatasetCollection(collection_type="list")
    datasets = []
    for i, state in enumerate(states):
        dataset = model.Dataset(state=state)
        hda = model.HistoryDatasetAssociation(dataset=dataset, extension=extension, history=harness.history)
        model.DatasetCollectionElement(collection=leaves, element=hda, element_index=i, element_identifier=str(i))
        datasets.append(hda)
    collection = leaves
    if nested:
        collection = model.DatasetCollection(collection_type="list:list")
        model.DatasetCollectionElement(
            collection=collection, element=leaves, element_index=0, element_identifier="child"
        )
        empty = model.DatasetCollection(collection_type="list")
        model.DatasetCollectionElement(
            collection=collection, element=empty, element_index=1, element_identifier="empty"
        )
    hdca = model.HistoryDatasetCollectionAssociation(collection=collection, history=harness.history)
    hdca.hid = len(datasets) + 1
    harness.persist(hdca)
    return hdca, datasets


def real_workflow_scheduler(
    harness, hdca, step_count=2, second_hdca=None, tool_file="filter_empty_collection_1.1.0.xml"
):
    """Prepare a real core invocation, also used by the reproducible benchmark."""
    from galaxy.managers.collections import DatasetCollectionManager
    from galaxy.workflow.run_request import (
        workflow_run_config_to_request,
        WorkflowRunConfig,
    )
    from galaxy.workflow.schedulers.core import CoreWorkflowSchedulingPlugin

    harness.app.config.log_events = False
    tool = create_tool_from_source(harness.app, get_tool_source(f"lib/galaxy/tools/{tool_file}"))
    toolbox = MockToolbox()
    toolbox.tools[tool.id] = tool
    harness.app._toolbox = toolbox
    harness.app.dataset_collection_manager = harness.app[DatasetCollectionManager]
    trans = cast(WorkRequestContext, MockTrans(app=harness.app, history=harness.history))
    workflow = model.Workflow()
    tool_count = 2 if second_hdca is not None else 1
    for index in range(step_count - tool_count):
        step = model.WorkflowStep()
        step.type = "data_collection_input"
        step.order_index = index
        step.tool_inputs = {"name": f"input{index}", "collection_type": hdca.collection.collection_type}
        step.workflow = workflow
    input_steps = list(workflow.steps)
    for index in range(tool_count):
        tool_step = model.WorkflowStep()
        tool_step.type = "tool"
        tool_step.order_index = len(workflow.steps)
        tool_step.tool_id = tool.id
        tool_step.tool_version = tool.version
        tool_step.tool_inputs = {"replacement": None} if "replacement" in tool.inputs else {}
        tool_step.workflow = workflow
        tool_step.add_connection("input", "output", input_steps[index])
    harness.persist(workflow)
    inputs = {
        step.id: second_hdca if second_hdca is not None and index == 1 else hdca
        for index, step in enumerate(input_steps)
    }
    config = WorkflowRunConfig(harness.history, inputs=inputs)
    modules.populate_module_and_state(trans, workflow, {})
    invocation = workflow_run_config_to_request(trans, config, workflow)
    invocation.workflow = workflow
    invocation.state = invocation.states.READY
    harness.persist(invocation)
    harness.invocation_id = invocation.id

    class RecordingCoreScheduler(CoreWorkflowSchedulingPlugin):
        scheduled = 0

        def schedule(self, invocation):
            self.scheduled += 1
            return super().schedule(invocation)

    scheduler = RecordingCoreScheduler()
    scheduler.startup(harness.app)
    return scheduler


def assert_waiting_without_replays(harness, scheduler):
    # Initial input-step writes can cause a timestamp wakeup. Measure after
    # those writes have settled; the exact number of initial attempts is incidental.
    harness.attempt(scheduler)
    harness.attempt(scheduler)
    attempts = scheduler.scheduled
    for _ in range(3):
        assert harness.attempt(scheduler) == attempts
    invocation = harness.session.get(model.WorkflowInvocation, harness.invocation_id)
    assert invocation.state == invocation.states.READY
    return attempts


@pytest.mark.parametrize(
    "tool_file,extension,nested,outcome",
    [
        ("filter_empty_collection_1.1.0.xml", "txt", False, "ok"),
        ("filter_empty_collection_1.1.0.xml", "auto", True, "ok"),
        ("filter_empty_collection_1.1.0.xml", "_sniff_", False, "ok"),
        ("filter_empty_collection_1.1.0.xml", "txt", False, "error"),
        ("filter_empty_collection_1.1.0.xml", "auto", False, "error"),
        ("keep_success_collection.xml", "txt", False, "ok"),
    ],
)
def test_waiting_collection_is_retried_only_after_input_changes(harness, tool_file, extension, nested, outcome):
    hdca, datasets = collection_input(harness, states=("running",), extension=extension, nested=nested)
    dataset_id, hda_id = datasets[0].dataset_id, datasets[0].id
    scheduler = real_workflow_scheduler(harness, hdca, tool_file=tool_file)
    attempts = assert_waiting_without_replays(harness, scheduler)

    if extension in ("auto", "_sniff_") and outcome == "ok":
        # Datatype resolution can precede job completion. It must wake the
        # datatype wait even though this particular internal tool still needs data.
        harness.session.query(model.HistoryDatasetAssociation).filter_by(id=hda_id).update({"extension": "txt"})
        harness.session.commit()
        harness.attempt(scheduler)
        assert scheduler.scheduled > attempts
        assert_waiting_without_replays(harness, scheduler)

    harness.session.query(model.Dataset).filter_by(id=dataset_id).update({"state": outcome})
    harness.session.commit()
    harness.attempt(scheduler)
    invocation = harness.session.get(model.WorkflowInvocation, harness.invocation_id)
    expected = invocation.states.SCHEDULED if outcome == "ok" else invocation.states.FAILED
    assert invocation.state == expected


def test_paused_input_override_does_not_replay_and_resumes_when_cleared(harness):
    hdca, datasets = collection_input(harness, states=("running",), extension="auto")
    dataset_id, hda_id = datasets[0].dataset_id, datasets[0].id
    datasets[0]._state = model.Dataset.states.PAUSED
    harness.persist(datasets[0])
    scheduler = real_workflow_scheduler(harness, hdca)
    attempts = assert_waiting_without_replays(harness, scheduler)

    harness.session.query(model.Dataset).filter_by(id=dataset_id).update({"state": model.Dataset.states.OK})
    harness.session.commit()
    assert harness.attempt(scheduler) == attempts
    harness.session.query(model.HistoryDatasetAssociation).filter_by(id=hda_id).update(
        {"_state": None, "extension": "txt"}
    )
    harness.session.commit()
    harness.attempt(scheduler)
    invocation = harness.session.get(model.WorkflowInvocation, harness.invocation_id)
    assert invocation.state == invocation.states.SCHEDULED


def test_independent_workflow_branch_can_progress_while_another_waits(harness):
    first, first_datasets = collection_input(harness, states=("running",))
    second, _ = collection_input(harness, states=("running",))
    dataset_id = first_datasets[0].dataset_id
    scheduler = real_workflow_scheduler(harness, first, step_count=4, second_hdca=second)
    assert_waiting_without_replays(harness, scheduler)

    harness.session.query(model.Dataset).filter_by(id=dataset_id).update({"state": model.Dataset.states.OK})
    harness.session.commit()
    harness.attempt(scheduler)
    invocation = harness.session.get(model.WorkflowInvocation, harness.invocation_id)
    tool_steps = [step for step in invocation.steps if step.workflow_step.type == "tool"]
    assert tool_steps[0].state == "scheduled"
    assert tool_steps[1].state != "scheduled"
    assert invocation.state == invocation.states.READY
