"""User defined tools with the default user_defined_tool_allowed_containers setting."""

from uuid import uuid4

from galaxy.model import (
    DynamicTool,
    UserDynamicToolAssociation,
)
from galaxy_test.api.test_tools import TestsTools
from galaxy_test.base.populators import (
    DatasetPopulator,
    TOOL_WITH_SHELL_COMMAND,
)
from galaxy_test.driver import integration_util

BIOCONTAINERS_TOOL = {**TOOL_WITH_SHELL_COMMAND, "container": "quay.io/biocontainers/coreutils:9.5"}


class TestUserDefinedToolContainerAllowlist(integration_util.IntegrationTestCase, TestsTools):
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config.pop("user_defined_tool_allowed_containers", None)

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

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
            job = self.dataset_populator.get_job_details(response["jobs"][0]["id"]).json()
            assert job["state"] == "error"
            output = self.dataset_populator.get_history_dataset_details(
                history_id, dataset_id=response["outputs"][0]["id"], assert_ok=False
            )
            assert "Container 'busybox' is not allowed for user defined tools" in output["misc_info"]

    def _store_tool_row(self, representation) -> str:
        user_id = self._app.security.decode_id(self.dataset_populator.user_id())
        session = self._app.model.session
        dynamic_tool = DynamicTool(
            tool_format="GalaxyUserTool",
            tool_id=representation["id"],
            tool_version=representation["version"],
            uuid=uuid4(),
            value=representation,
            public=False,
            active=True,
        )
        session.add(dynamic_tool)
        session.flush()
        session.add(UserDynamicToolAssociation(user_id=user_id, dynamic_tool_id=dynamic_tool.id))
        session.commit()
        return str(dynamic_tool.uuid)
