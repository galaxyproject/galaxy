"""User defined tools with the default user_defined_tool_allowed_containers setting."""

import json
from typing import Any
from uuid import uuid4

from galaxy.model import Job
from galaxy_test.base.api_mixins import TestsTools
from galaxy_test.base.populators import (
    DatasetPopulator,
    TOOL_WITH_SHELL_COMMAND,
)
from galaxy_test.driver import integration_util

BIOCONTAINERS_TOOL = {**TOOL_WITH_SHELL_COMMAND, "container": "quay.io/biocontainers/coreutils:9.5"}
PULSAR_JOB_CONFIG = {
    "runners": {
        "local": {"load": "galaxy.jobs.runners.local:LocalJobRunner"},
        "pulsar_embed": {
            "load": "galaxy.jobs.runners.pulsar:PulsarEmbeddedJobRunner",
            "pulsar_app_config": {"tool_dependency_dir": "none", "conda_auto_init": False, "conda_auto_install": False},
        },
    },
    "execution": {
        "default": "pulsar_embed",
        "environments": {
            "local": {"runner": "local"},
            "pulsar_embed": {
                "runner": "pulsar_embed",
                "remote_metadata": True,
                "resubmit": [{"condition": "any_failure", "environment": "local"}],
            },
        },
    },
    "tools": [{"class": "local", "environment": "local"}],
}


class BaseUserDefinedToolContainerAllowlist(integration_util.IntegrationTestCase, TestsTools):
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config.pop("user_defined_tool_allowed_containers", None)

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def _run_stored_disallowed_tool(self) -> str:
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            # A tool stored before the allowlist excluded its image.
            uuid = self._store_tool_row(TOOL_WITH_SHELL_COMMAND)
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc", wait=True)
            response = self._run(
                history_id=history_id,
                tool_uuid=uuid,
                inputs={"input": {"src": "hda", "id": dataset["id"]}},
                wait_for_job=True,
                assert_ok=True,
            )
            job_id = response["jobs"][0]["id"]
            job = self.dataset_populator.get_job_details(job_id).json()
            assert job["state"] == "error"
            output = self.dataset_populator.get_history_dataset_details(
                history_id, dataset_id=response["outputs"][0]["id"], assert_ok=False
            )
            assert "Container 'busybox' is not allowed for user defined tools" in output["misc_info"]
            return job_id

    def _store_tool_row(self, representation: dict[str, Any]) -> str:
        user_id = self._app.security.decode_id(self.dataset_populator.user_id())
        return integration_util.store_user_tool_row(self._app, user_id, representation)


class TestUserDefinedToolContainerAllowlist(BaseUserDefinedToolContainerAllowlist):
    def test_create_rejects_container_outside_allowlist(self):
        with self.dataset_populator.user_tool_execute_permissions():
            assert TOOL_WITH_SHELL_COMMAND["container"] == "busybox"
            response = self.dataset_populator.create_unprivileged_tool_raw(TOOL_WITH_SHELL_COMMAND)
            assert response.status_code == 400, response.text
            message = response.json()["err_msg"]
            assert "Container 'busybox' is not allowed" in message
            assert "quay.io/biocontainers/*" in message

            created = self.dataset_populator.create_unprivileged_tool(BIOCONTAINERS_TOOL)
            assert created["active"]

    def test_job_of_stored_tool_with_disallowed_container_fails(self):
        self._run_stored_disallowed_tool()

    def test_import_workflow_embedding_disallowed_tool_is_rejected(self):
        workflow = {
            "a_galaxy_workflow": "true",
            "name": "wf embedding a busybox user tool",
            "format-version": "0.1",
            "steps": {
                "0": {
                    "id": 0,
                    "type": "tool",
                    "tool_state": "{}",
                    "input_connections": {},
                    "uuid": str(uuid4()),
                    "tool_representation": TOOL_WITH_SHELL_COMMAND,
                },
            },
        }
        with self.dataset_populator.user_tool_execute_permissions():
            workflows_before = self._get("workflows").json()
            tools_before = self.dataset_populator.get_unprivileged_tools()
            response = self._post("workflows", data={"workflow": json.dumps(workflow)})
            assert response.status_code == 400, response.text
            assert "Container 'busybox' is not allowed" in response.json()["err_msg"]
            assert self._get("workflows").json() == workflows_before
            assert self.dataset_populator.get_unprivileged_tools() == tools_before


class TestUserDefinedToolContainerAllowlistPulsar(BaseUserDefinedToolContainerAllowlist):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config"] = PULSAR_JOB_CONFIG

    def test_job_of_stored_tool_with_disallowed_container_fails_without_resubmission(self):
        job_id = self._run_stored_disallowed_tool()
        job = self._app.model.session.get(Job, self._app.security.decode_id(job_id))
        assert job is not None
        assert job.destination_id == "pulsar_embed"
