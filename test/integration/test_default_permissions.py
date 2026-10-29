from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from galaxy_test.driver import integration_util


class TestDefaultPermissionsIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    new_user_dataset_access_role_default_private: bool | None = None
    expected_access_status_code = 403

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
        self.dataset_populator.assert_history_datasets_permissions(history_id, expected_count=2, access_private=True)

    def test_dynamic_collection_elements_get_default_permissions(self, history_id: str) -> None:
        response = self.dataset_populator.run_tool(
            "collection_creates_dynamic_list_of_pairs", {"foo": "bar"}, history_id
        )
        self.dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
        self.dataset_populator.assert_history_datasets_permissions(history_id, expected_count=6, access_private=True)


class TestPublicDefaultPermissionsIntegration(TestDefaultPermissionsIntegration):
    new_user_dataset_access_role_default_private = False
    expected_access_status_code = 200
    framework_tool_and_types = True

    def setUp(self) -> None:
        super().setUp()
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_guess_derived_permissions_collections(self, history_id: str) -> None:
        # Tool outputs also get the history's default access restriction (#21802),
        # so outputs derived from public inputs are only public with public defaults.
        def first_element_dataset_id(hdca):
            full_hdca = self.dataset_populator.get_history_collection_details(history_id, hid=hdca["hid"])
            return full_hdca["elements"][0]["object"]["id"]

        response = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["a\nb\nc\nd", "e\nf\ng\nh"], direct_upload=True, wait=True
        )
        hdca = response.json()["output_collections"][0]
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        inputs = {
            "input1": {"src": "hdca", "id": hdca["id"]},
        }
        public_output = self.dataset_populator.run_tool("collection_creates_list", inputs, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)

        self.dataset_populator.make_private(history_id, first_element_dataset_id(hdca))

        private_output = self.dataset_populator.run_tool("collection_creates_list", inputs, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)

        public_element_id = first_element_dataset_id(public_output["output_collections"][0])
        private_element_id = first_element_dataset_id(private_output["output_collections"][0])

        def _dataset_accessible(dataset_id):
            contents_response = self._get(f"histories/{history_id}/contents/{dataset_id}").json()
            return "name" in contents_response

        with self._different_user():
            assert _dataset_accessible(public_element_id)
            assert not _dataset_accessible(private_element_id)
