# Test tools API.
from uuid import uuid4

from galaxy.tool_util_models import UserToolSource
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    TOOL_WITH_SHELL_COMMAND,
)
from ._framework import ApiTestCase
from .test_tools import TestsTools


class TestUnprivilegedToolsApi(ApiTestCase, TestsTools):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_admin_cannot_create_public_galaxy_user_tool(self):
        # GalaxyUserTool would land as public=True and bypass role+ownership.
        payload = {"representation": TOOL_WITH_SHELL_COMMAND}
        response = self.dataset_populator._post("dynamic_tools", data=payload, admin=True, json=True)
        assert response.status_code == 400, response.text
        assert "GalaxyUserTool" in response.text

    def test_create_unprivileged_requires_execute_role(self):
        dynamic_tool = self.dataset_populator.create_unprivileged_tool(
            UserToolSource(**TOOL_WITH_SHELL_COMMAND), assert_ok=False
        )
        assert dynamic_tool["err_msg"] == "User is not allowed to run unprivileged tools"

    def test_create_unprivileged(self):
        # Create a new dynamic tool.
        with self.dataset_populator.user_tool_execute_permissions():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            assert dynamic_tool["uuid"], "Dynamic tool UUID not found in response"
            assert dynamic_tool["representation"]["name"] == TOOL_WITH_SHELL_COMMAND["name"]

    def test_create_unprivileged_with_group_inherited_role(self):
        # Regression: USER_TOOL_EXECUTE granted via group membership must also allow access,
        # not only direct UserRoleAssociation.
        with self.dataset_populator.user_tool_execute_permissions_via_group():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            assert dynamic_tool["uuid"], "Dynamic tool UUID not found in response"
            assert dynamic_tool["representation"]["name"] == TOOL_WITH_SHELL_COMMAND["name"]

    def test_list_unprivileged(self):
        with self.dataset_populator.user_tool_execute_permissions():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            dynamic_tools = self.dataset_populator.get_unprivileged_tools()
        assert any(
            dynamic_tool["uuid"] == t["uuid"] for t in dynamic_tools
        ), f"Newly created dynamic tool {dynamic_tool['uuid']} not in dynamic tools list {dynamic_tools}"

    def test_show(self):
        with self.dataset_populator.user_tool_execute_permissions():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            show_response = self.dataset_populator.show_unprivileged_tool(dynamic_tool["uuid"])
        assert show_response["representation"]["name"]

    def test_build(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            response = self.dataset_populator.build_unprivileged_tool(
                UserToolSource(**TOOL_WITH_SHELL_COMMAND), history_id=history_id
            )
        assert response

    def test_build_runtime_model(self):
        with self.dataset_populator.user_tool_execute_permissions():
            response = self.dataset_populator.build_runtime_model_for_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            assert response
            assert response["openapi"] == "3.1.0"
            assert response["components"]["schemas"]["inputs"]

    def test_run(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            # Create a new dynamic tool.
            # This is a shell command tool that will echo the input dataset.
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            # Run tool.
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc")
            self._run(
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
                inputs={"input": {"src": "hda", "id": dataset["id"]}},
            )

            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            output_content = self.dataset_populator.get_history_dataset_content(history_id)
            assert output_content == "abc\n"

    def test_rerun_private_udt_denied_for_non_owner_with_execute_role(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc")
            run_response = self._run(
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
                inputs={"input": {"src": "hda", "id": dataset["id"]}},
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            job_id = run_response.json()["jobs"][0]["id"]
            tool_uuid = dynamic_tool["uuid"]
            self.dataset_populator.make_public(history_id)

            other_email = f"udt_non_owner_{uuid4()}@bx.psu.edu"
            with self._different_user(email=other_email):
                with self.dataset_populator.user_tool_execute_permissions():
                    # Import A's published history into B's account so B holds a
                    # legitimate copy of the data; rerun must still be denied.
                    copy_response = self.dataset_populator.copy_history(history_id)
                    copy_response.raise_for_status()

                    rerun_response = self.dataset_populator._get(f"jobs/{job_id}/build_for_rerun")
                    assert rerun_response.status_code == 403, rerun_response.text

                    tool_response = self.dataset_populator._get(f"tools/{tool_uuid}")
                    assert tool_response.status_code in (403, 404), tool_response.text

    def test_rerun_private_udt_denied_for_user_without_execute_role(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc")
            run_response = self._run(
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
                inputs={"input": {"src": "hda", "id": dataset["id"]}},
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            job_id = run_response.json()["jobs"][0]["id"]
            self.dataset_populator.make_public(history_id)

            other_email = f"udt_no_role_{uuid4()}@bx.psu.edu"
            with self._different_user(email=other_email):
                # Import A's published history into B's account so B holds a
                # legitimate copy of the data; rerun must still be denied.
                copy_response = self.dataset_populator.copy_history(history_id)
                copy_response.raise_for_status()

                rerun_response = self.dataset_populator._get(f"jobs/{job_id}/build_for_rerun")
                assert rerun_response.status_code == 403, rerun_response.text

    def test_deactivate(self):
        with self.dataset_populator.user_tool_execute_permissions():
            # Create a new dynamic tool.
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            # Deactivate the tool.
            self.dataset_populator.deactivate_unprivileged_tool(dynamic_tool["uuid"])
            # Check that the tool is deactivated.
            dynamic_tools = self.dataset_populator.get_unprivileged_tools()
            assert not any(
                dynamic_tool["uuid"] == t["uuid"] for t in dynamic_tools
            ), f"Dynamic tool {dynamic_tool['uuid']} still in dynamic tools list {dynamic_tools}"
