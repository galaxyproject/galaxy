"""Integration tests for maximum workflow invocation duration configuration option."""

import os
import re
import string
import tempfile
import time
from json import dumps

from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
WORKFLOW_HANDLER_CONFIGURATION_JOB_CONF = os.path.join(SCRIPT_DIRECTORY, "workflow_handler_configuration_job_conf.xml")

WORKFLOW_HANDLER_JOB_CONFIG_TEMPLATE = string.Template(
    """
<job_conf>
    <plugins>
        <plugin id="local" type="runner" load="galaxy.jobs.runners.local:LocalJobRunner" workers="2"/>
    </plugins>

    <handlers default="handlers"  $assign_with>
        <handler id="handler0" tags="handlers"/>
        <handler id="handler1" tags="handlers"/>
        <handler id="handler2" tags="handlers" />
        <handler id="handler3" tags="handlers" />
        <handler id="handler4" tags="handlers" />
        <handler id="handler5" tags="handlers" />
        <handler id="handler6" tags="handlers" />
        <handler id="handler7" tags="handlers" />
        <handler id="handler8" tags="handlers" />
        <handler id="handler9" tags="handlers" />
    </handlers>

    <destinations default="local">
        <destination id="local" runner="local">
        </destination>
    </destinations>
</job_conf>
"""
)

POOL_JOB_CONFIG_TEMPLATE = string.Template(
    """<job_conf>
    <plugins>
        <plugin id="local" type="runner" load="galaxy.jobs.runners.local:LocalJobRunner" workers="2"/>
    </plugins>
    <handlers $assign_with>
    </handlers>
    <destinations default="local">
        <destination id="local" runner="local">
        </destination>
    </destinations>
</job_conf>
"""
)

WORKFLOW_SCHEDULERS_CONFIG_TEMPLATE = string.Template(
    """
<workflow_schedulers default="core">
  <core id="core" />
  <handlers default="workflow_handlers" $assign_with>
    <handler id="work1" tags="workflow_handlers" />
    <handler id="work2" tags="workflow_handlers" />
  </handlers>
</workflow_schedulers>
"""
)
JOB_HANDLER_PATTERN = re.compile(r"handler\d")
WORKFLOW_SCHEDULER_HANDLER_PATTERN = re.compile(r"work\d")

PAUSE_WORKFLOW = """
class: GalaxyWorkflow
steps:
- label: test_input
  type: input
- label: the_pause
  type: pause
  connect:
    input:
    - test_input
"""


def config_file(template, assign_with=""):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", prefix="workflow_handler_config_", delete=False
    ) as config:
        if assign_with:
            assign_with = f'assign_with="{assign_with}"'
        config.write(template.substitute(assign_with=assign_with))
    return config.name


class BaseWorkflowHandlerConfigurationTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True
    assign_with = ""

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)
        self.history_id = self.dataset_populator.new_history()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["job_config_file"] = config_file(WORKFLOW_HANDLER_JOB_CONFIG_TEMPLATE, assign_with=cls.assign_with)

    def _invoke_n_workflows(self, n):
        workflow_id = self.workflow_populator.upload_yaml_workflow(PAUSE_WORKFLOW)
        history_id = self.history_id
        hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
        index_map = {"0": dict(src="hda", id=hda1["id"])}
        request = {}
        request["history"] = "hist_id=%s" % history_id
        request["inputs"] = dumps(index_map)
        request["inputs_by"] = "step_index"
        url = "workflows/%s/invocations" % (workflow_id)
        for _ in range(n):
            self._post(url, data=request)

    def _get_workflow_invocations(self):
        # Consider exposing handler via the API to reduce breaking
        # into Galaxy's internal state.
        app = self._app
        history_id = app.security.decode_id(self.history_id)
        sa_session = app.model.context.current
        history = sa_session.query(app.model.History).get(history_id)
        workflow_invocations = history.workflow_invocations
        return workflow_invocations

    @property
    def is_app_workflow_scheduler(self):
        return self._app.workflow_scheduling_manager.request_monitor is not None


class HistoryRestrictionConfigurationTestCase(BaseWorkflowHandlerConfigurationTestCase):

    # Assign with db-preassign. Would also work with grabbing assignment, but we don't start grabber.
    assign_with = "db-preassign"

    def test_history_to_handler_restriction(self):
        self._invoke_n_workflows(10)
        workflow_invocations = self._get_workflow_invocations()
        assert len(workflow_invocations) == 10
        # Verify all 10 assigned to same handler - there would be a
        # 1 in 10^10 chance for this to occur randomly.
        for workflow_invocation in workflow_invocations:
            assert workflow_invocation.handler == workflow_invocations[0].handler

        assert JOB_HANDLER_PATTERN.match(workflow_invocations[0].handler)


class HistoryParallelConfigurationTestCase(BaseWorkflowHandlerConfigurationTestCase):

    # Assign with db-preassign. Would also work with grabbing assignment, but we don't start grabber.
    assign_with = "db-preassign"

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["parallelize_workflow_scheduling_within_histories"] = True

    def test_workflows_spread_across_multiple_handlers(self):
        self._invoke_n_workflows(20)
        workflow_invocations = self._get_workflow_invocations()
        assert len(workflow_invocations) == 20
        handlers = set()
        for workflow_invocation in workflow_invocations:
            handlers.add(workflow_invocation.handler)
            assert JOB_HANDLER_PATTERN.match(workflow_invocation.handler)

        # Assert at least 2 of 20 invocations were assigned to different handlers.
        assert len(handlers) >= 1, handlers


# Setup an explicit workflow handler and make sure this is assigned to that.
class WorkflowSchedulerHandlerAssignment(BaseWorkflowHandlerConfigurationTestCase):

    # Assign with db-preassign. Would also work with grabbing assignment, but we don't start grabber.
    assign_with = "db-preassign"

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["workflow_schedulers_config_file"] = config_file(
            WORKFLOW_SCHEDULERS_CONFIG_TEMPLATE, assign_with=cls.assign_with
        )

    def test_handler_assignment(self):
        self._invoke_n_workflows(1)
        workflow_invocations = self._get_workflow_invocations()
        assert WORKFLOW_SCHEDULER_HANDLER_PATTERN.match(workflow_invocations[0].handler)


# Following 8 classes test 8 different ways Galaxy processes can be workflow schedulers or not.
#  - In single process mode, the process is a workflow scheduler.
#  - If no workflow schedulers conf is configured and the process is a job handler, it is a workflow scheduler as well.
#  - If no workflow schedulers conf is configured and the process is a job handler, it is a workflow scheduler as well (with db-dkip-locked).
#  - If no workflow schedulers conf is configured and the process is not a job handler, it is not a workflow scheduler as well.
#  - If a workflow scheduler conf is defined and the process is listed as a handler, it is workflow scheduler.
#  - If a workflow scheduler conf is defined and assign_with is set to db-skip-locked, invocation handler is correctly set
#  - If a workflow scheduler conf is defined and assign_with is set to db-transaction-isolation, invocation handler is correctly set
#  - If a workflow scheduler conf is defined and the process is not listed as a handler, it is not workflow scheduler.
class DefaultWorkflowHandlerOnTestCase(BaseWorkflowHandlerConfigurationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        # Override so we don't setup a job conf like in the base class.
        pass

    def test_default_main_process_is_handler(self):
        assert self.is_app_workflow_scheduler


class DefaultWorkflowHandlerIfJobHandlerOnTestCase(BaseWorkflowHandlerConfigurationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["server_name"] = "handler0"

    def test_default_job_handler_is_workflow_handler(self):
        assert self.is_app_workflow_scheduler


class JobHandlerAsWorkflowHandlerWithDbSkipLocked(BaseWorkflowHandlerConfigurationTestCase):

    assign_with = "db-skip-locked"

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["server_name"] = "handler0"

    def test_handler_assignment(self):
        self._invoke_n_workflows(1)
        time.sleep(2)
        workflow_invocations = self._get_workflow_invocations()
        assert JOB_HANDLER_PATTERN.match(workflow_invocations[0].handler)

    def test_default_job_handler_is_workflow_handler(self):
        assert self.is_app_workflow_scheduler


class JobHandlerAsWorkflowHandlerWithDbSkipLockedAttachToPool(JobHandlerAsWorkflowHandlerWithDbSkipLocked):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["job_config_file"] = config_file(POOL_JOB_CONFIG_TEMPLATE, assign_with=cls.assign_with)
        config["server_name"] = "handler0"
        config["attach_to_pools"] = ["job-handlers"]


class DefaultWorkflowHandlerIfJobHandlerOffTestCase(BaseWorkflowHandlerConfigurationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["server_name"] = "web0"

    def test_default_job_handler_is_not_workflow_handler(self):
        assert not self.is_app_workflow_scheduler


class ExplicitWorkflowHandlersOnTestCase(BaseWorkflowHandlerConfigurationTestCase):

    assign_with = ""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["workflow_schedulers_config_file"] = config_file(
            WORKFLOW_SCHEDULERS_CONFIG_TEMPLATE, assign_with=cls.assign_with
        )
        config["server_name"] = "work1"

    def test_app_is_workflow_scheduler(self):
        assert self.is_app_workflow_scheduler


@integration_util.skip_unless_postgres()
class WorkflowSchedulerHandlerAssignmentDbSkipLocked(ExplicitWorkflowHandlersOnTestCase):

    assign_with = "db-skip-locked"

    def test_handler_assignment(self):
        self._invoke_n_workflows(1)
        time.sleep(2)
        workflow_invocations = self._get_workflow_invocations()
        assert WORKFLOW_SCHEDULER_HANDLER_PATTERN.match(workflow_invocations[0].handler)


@integration_util.skip_unless_postgres()
class WorkflowSchedulerHandlerAssignmentDbTransactionIsolation(WorkflowSchedulerHandlerAssignmentDbSkipLocked):

    assign_with = "db-transaction-isolation"


class ExplicitWorkflowHandlersOffTestCase(BaseWorkflowHandlerConfigurationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["workflow_schedulers_config_file"] = config_file(
            WORKFLOW_SCHEDULERS_CONFIG_TEMPLATE, assign_with=cls.assign_with
        )
        config["server_name"] = "handler0"  # Configured as a job handler but not a workflow handler.

    def test_app_is_not_workflow_scheduler(self):
        assert not self.is_app_workflow_scheduler


class ExplicitWorkflowHandlersOffPoolTestCase(BaseWorkflowHandlerConfigurationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["workflow_schedulers_config_file"] = config_file(
            WORKFLOW_SCHEDULERS_CONFIG_TEMPLATE, assign_with=cls.assign_with
        )
        config["server_name"] = "handler0"  # Configured as a job handler but not a workflow handler.
        config["attach_to_pools"] = ["job-handlers"]

    def test_app_is_not_workflow_scheduler(self):
        assert not self.is_app_workflow_scheduler
