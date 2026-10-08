from typing import Optional

from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from galaxy_test.driver import integration_util


class TestDefaultPermissionsIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    new_user_dataset_access_role_default_private: Optional[bool] = None
    expected_access_status_code = 200

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        if cls.new_user_dataset_access_role_default_private is not None:
            config["new_user_dataset_access_role_default_private"] = cls.new_user_dataset_access_role_default_private

    def test_setting(self, history_id: str) -> None:
        hda = self.dataset_populator.new_dataset(history_id, wait=True)
        with self._different_user():
            details_response = self.dataset_populator.get_history_dataset_details_raw(
                history_id=history_id, dataset_id=hda["id"]
            )
            assert details_response.status_code == self.expected_access_status_code, details_response.content


class TestPrivateDefaultPermissionsIntegration(TestDefaultPermissionsIntegration):
    new_user_dataset_access_role_default_private = True
    expected_access_status_code = 403
    framework_tool_and_types = True

    def setUp(self) -> None:
        super().setUp()
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_fetched_list_elements_get_default_permissions(self, history_id: str) -> None:
        self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["a\n", "b\n"], direct_upload=True, wait=True
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        self._assert_history_datasets_private(history_id, expected_count=2)

    def test_dynamic_collection_elements_get_default_permissions(self, history_id: str) -> None:
        response = self.dataset_populator.run_tool(
            "collection_creates_dynamic_list_of_pairs", {"foo": "bar"}, history_id
        )
        self.dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
        self._assert_history_datasets_private(history_id, expected_count=6)

    def _assert_history_datasets_private(self, history_id: str, expected_count: int) -> None:
        role_id = self.dataset_populator.user_private_role_id()
        datasets = self.dataset_populator.get_history_contents_of_type(history_id, "datasets")
        assert len(datasets) == expected_count, [d["name"] for d in datasets]
        permissions = {d["name"]: self._get(f"datasets/{d['id']}").json().get("permissions") for d in datasets}
        assert permissions == {name: {"manage": [role_id], "access": [role_id]} for name in permissions}


class TestPublicDefaultPermissionsIntegration(TestDefaultPermissionsIntegration):
    new_user_dataset_access_role_default_private = False
    expected_access_status_code = 200
