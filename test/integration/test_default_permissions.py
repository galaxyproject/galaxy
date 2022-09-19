from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class DefaultPermissionsIntegrationTestCase(integration_util.IntegrationTestCase):
    expected_access_status_code = 200

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.history_id = self.dataset_populator.new_history()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        if hasattr(cls, "new_user_dataset_access_role_default_private"):
            config["new_user_dataset_access_role_default_private"] = cls.new_user_dataset_access_role_default_private

    def test_setting(self):
        hda = self.dataset_populator.new_dataset(self.history_id, wait=True)
        with self._different_user():
            details_response = self.dataset_populator.get_history_dataset_details_raw(
                history_id=self.history_id, dataset_id=hda["id"]
            )
            assert details_response.status_code == self.expected_access_status_code, details_response.content


class PrivateDefaultPermissionsIntegrationTestCase(DefaultPermissionsIntegrationTestCase):
    new_user_dataset_access_role_default_private = True
    expected_access_status_code = 403


class PublicDefaultPermissionsIntegrationTestCase(DefaultPermissionsIntegrationTestCase):
    new_user_dataset_access_role_default_private = False
    expected_access_status_code = 200
