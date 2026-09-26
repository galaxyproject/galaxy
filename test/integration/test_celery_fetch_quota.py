"""Integration test for quota enforcement during Celery-based data fetch.

Verifies that when a user is over their disk quota, data fetch jobs
submitted via the Celery task chain are correctly paused rather than
being allowed to proceed with the download.
"""

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class TestCeleryFetchQuotaEnforcement(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_quotas"] = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_fetch_paused_when_over_quota(self):
        with self.dataset_populator.test_history() as history_id:
            # Upload an initial dataset so the user has some disk usage
            self.dataset_populator.new_dataset(history_id, content="initial content", wait=True)

            # Set a very low quota (1 byte) so the user is over quota
            payload = {
                "name": "default-celery-fetch-quota",
                "description": "very low default quota for testing",
                "amount": "1 bytes",
                "operation": "=",
                "default": "registered",
            }
            self.dataset_populator.create_quota(payload)

            # Now try to upload another dataset - should be paused due to quota
            hda = self.dataset_populator.new_dataset(history_id, content="more data", wait=False)
            self.dataset_populator.wait_for_history(history_id, assert_ok=False)

            details = self.dataset_populator.get_history_dataset_details(
                history_id, dataset=hda, wait=False, assert_ok=False
            )
            assert details["state"] == "paused", f"Expected dataset state 'paused', got '{details['state']}'"
