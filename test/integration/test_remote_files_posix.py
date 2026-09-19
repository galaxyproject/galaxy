import os

from sqlalchemy import select

from galaxy.model import Dataset
from galaxy_test.base import api_asserts
from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.base.workflow_fixtures import WORKFLOW_SIMPLE_CAT_TWICE
from galaxy_test.driver import integration_util
from galaxy_test.driver.integration_setup import (
    GROUP_A,
    GROUP_B,
    PosixFileSourceSetup,
    REQUIRED_GROUP_EXPRESSION,
    REQUIRED_ROLE_EXPRESSION,
)


class TestPosixFileSourceIntegration(PosixFileSourceSetup, integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True
    required_role_expression = REQUIRED_ROLE_EXPRESSION
    required_group_expression = REQUIRED_GROUP_EXPRESSION

    def setUp(self):
        super().setUp()
        self._write_file_fixtures()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_plugin_config(self):
        # Default user has required role but not required group, so cannot see plugin
        plugin_config_response = self.galaxy_interactor.get("remote_files/plugins")
        api_asserts.assert_status_code_is_ok(plugin_config_response)
        plugins = plugin_config_response.json()
        assert len(plugins) == 0
        # Admins can see plugins
        plugin_config_response = self.galaxy_interactor.get("remote_files/plugins", admin=True)
        api_asserts.assert_status_code_is_ok(plugin_config_response)
        plugins = plugin_config_response.json()
        assert len(plugins) == 1
        assert plugins[0]["type"] == "posix"
        assert plugins[0]["uri_root"] == "gxfiles://posix_test"
        assert plugins[0]["writable"] is True
        assert plugins[0]["requires_roles"] == REQUIRED_ROLE_EXPRESSION
        assert plugins[0]["requires_groups"] == REQUIRED_GROUP_EXPRESSION

    def test_allow_admin_access(self):
        data = {"target": "gxfiles://posix_test"}
        list_response = self.galaxy_interactor.get("remote_files", data, admin=True)
        self._assert_list_response_matches_fixtures(list_response)

    def test_user_access(self):
        data = {"target": "gxfiles://posix_test"}
        group_a_id = self._create_group(GROUP_A)
        group_b_id = self._create_group(GROUP_B)

        # User has role but not group
        list_response = self.galaxy_interactor.get("remote_files", data)
        self._assert_access_forbidden_response(list_response)

        # User has role and group A
        user_id = self.dataset_populator.user_id()
        self._add_user_to_group(group_a_id, user_id)
        list_response = self.galaxy_interactor.get("remote_files", data)
        self._assert_list_response_matches_fixtures(list_response)

        # Remove User from group A and add to group B
        self._remove_user_from_group(group_a_id, user_id)
        self._add_user_to_group(group_b_id, user_id)
        list_response = self.galaxy_interactor.get("remote_files", data)
        self._assert_list_response_matches_fixtures(list_response)

    def test_workflow_input_materialized_from_group_file_source(self):
        # Ensure the default non-admin user is in the required group so the
        # file source is accessible.
        group_a_id = self._ensure_group(GROUP_A)
        self._add_user_to_group(group_a_id, self.dataset_populator.user_id())

        with self.dataset_populator.test_history() as history_id:
            # Pass the workflow input as a URL at invocation time so the scheduler
            # creates a deferred HDA and then materializes it from the
            # group-restricted file source (requires_materialization path in
            # galaxy.workflow.run_request).
            workflow_id, response = self._invoke_gxfiles_posix_test_workflow(history_id)
            invocation_id = response.json()["id"]
            self.workflow_populator.wait_for_workflow(workflow_id, invocation_id, history_id, assert_ok=True)

            # The input was materialized from gxfiles://posix_test/a; its fixture
            # content is "a\n", so cat of it concatenated with itself is "a\na\n".
            input_hda = self.dataset_populator.get_history_dataset_details(history_id, hid=1)
            assert input_hda["state"] == "ok", input_hda
            cat_output = self.dataset_populator.get_history_dataset_content(history_id, hid=2)
            assert cat_output == "a\na\n", cat_output

    def test_workflow_input_materialization_denied_without_group(self):
        # Counterpart to test_workflow_input_materialized_from_group_file_source:
        # a user who is not a member of any of the groups required by posix_test
        # cannot see the file source, and any workflow invocation that tries to
        # materialize a gxfiles://posix_test/... input must fail rather than
        # silently leak data across the group boundary.
        with self._different_user("wf_no_fs_access_user@bx.psu.edu"):
            # The restricted plugin is not advertised to this user.
            plugin_config_response = self.galaxy_interactor.get("remote_files/plugins")
            api_asserts.assert_status_code_is_ok(plugin_config_response)
            plugins = plugin_config_response.json()
            assert all(p["uri_root"] != "gxfiles://posix_test" for p in plugins), plugins

            # And direct access to the file source is forbidden.
            list_response = self.galaxy_interactor.get("remote_files", {"target": "gxfiles://posix_test"})
            self._assert_access_forbidden_response(list_response)

            # Invoking a workflow with a gxfiles://posix_test/... input must not
            # result in the file being materialized into this user's history.
            with self.dataset_populator.test_history() as history_id:
                workflow_id, response = self._invoke_gxfiles_posix_test_workflow(history_id)
                invocation_id = response.json()["id"]
                # Wait for the invocation to reach a terminal state; materialization
                # should fail because the file source is not accessible to this user.
                self.workflow_populator.wait_for_invocation(workflow_id, invocation_id, assert_ok=False)
                invocation = self.workflow_populator.get_invocation(invocation_id)
                assert invocation["state"] == "failed", invocation
                # The scheduler records a `dataset_failed` message pointing at the
                # HDA whose materialization failed. The ItemAccessibilityException
                # from _check_user_access is surfaced on that HDA's `info` field.
                messages = invocation["messages"]
                dataset_failed = [m for m in messages if m["reason"] == "dataset_failed"]
                assert dataset_failed, messages
                failed_hda = self.dataset_populator.get_history_dataset_details(history_id, hid=1, assert_ok=False)
                assert failed_hda["state"] == "error", failed_hda
                assert "no access to file source" in failed_hda["misc_info"], failed_hda

    def _invoke_gxfiles_posix_test_workflow(self, history_id: str):
        """Submit WORKFLOW_SIMPLE_CAT_TWICE with a single gxfiles://posix_test/a
        URL input and return (workflow_id, raw invocation response)."""
        workflow_id = self.workflow_populator.upload_yaml_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        workflow_request = {
            "history": f"hist_id={history_id}",
            "inputs": {
                "input1": {
                    "src": "url",
                    "url": "gxfiles://posix_test/a",
                    "ext": "txt",
                    "deferred": False,
                },
            },
            "inputs_by": "name",
        }
        return workflow_id, self.workflow_populator.invoke_workflow_raw(workflow_id, workflow_request, assert_ok=True)

    def _ensure_group(self, group_name: str) -> str:
        """Idempotent: return the id of an existing group with this name, or create it."""
        groups_response = self._get("groups", admin=True)
        api_asserts.assert_status_code_is_ok(groups_response)
        for group in groups_response.json():
            if group["name"] == group_name:
                return group["id"]
        return self._create_group(group_name)

    def _create_group(self, group_name: str):
        payload = {
            "name": group_name,
            "user_ids": [],
        }
        response = self._post("groups", payload, admin=True, json=True)
        self._assert_status_code_is(response, 200)
        group = response.json()[0]  # POST /api/groups returns a list
        return group["id"]

    def _add_user_to_group(self, group_id, user_id):
        update_response = self._put(f"groups/{group_id}/users/{user_id}", admin=True)
        self._assert_status_code_is_ok(update_response)

    def _remove_user_from_group(self, group_id, user_id):
        update_response = self._delete(f"groups/{group_id}/users/{user_id}", admin=True)
        self._assert_status_code_is_ok(update_response)

    def _assert_list_response_matches_fixtures(self, list_response):
        api_asserts.assert_status_code_is_ok(list_response)
        remote_files = list_response.json()
        assert len(remote_files) == 2
        if remote_files[0]["class"] == "Directory":
            dir = remote_files[0]
            file = remote_files[1]
        else:
            dir = remote_files[1]
            file = remote_files[0]
        assert file["name"] == "a"
        assert dir["name"] == "subdir1"

    def _assert_access_forbidden_response(self, response):
        api_asserts.assert_status_code_is(response, 403)


class TestPreferLinksPosixFileSourceIntegration(PosixFileSourceSetup, integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True
    prefer_links = True

    def setUp(self):
        super().setUp()
        self._write_file_fixtures()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_links_by_default(self):
        with self.dataset_populator.test_history() as history_id:
            element = dict(src="url", url="gxfiles://linking_source/a")
            target = {
                "destination": {"type": "hdas"},
                "elements": [element],
            }
            targets = [target]
            payload = {
                "history_id": history_id,
                "targets": targets,
            }
            new_dataset = self.dataset_populator.fetch(payload, assert_ok=True).json()["outputs"][0]
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=new_dataset)
            assert content == "a\n", content
            stmt = select(Dataset).order_by(Dataset.create_time.desc()).limit(1)
            dataset = self._app.model.session.execute(stmt).unique().scalar_one()
            assert dataset.external_filename is not None
            assert dataset.external_filename.endswith("/root/a")
            assert os.path.exists(dataset.external_filename)
            assert open(dataset.external_filename).read() == "a\n"
            payload = self.dataset_populator.run_tool(
                tool_id="cat",
                inputs={
                    "input1": {"src": "hda", "id": new_dataset["id"]},
                },
                history_id=history_id,
            )
            derived_dataset = payload["outputs"][0]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            derived_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=derived_dataset)
            assert derived_content.strip() == "a"
