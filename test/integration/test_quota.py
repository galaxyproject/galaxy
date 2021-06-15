from galaxy_test.base.populators import (
    DatasetPopulator,
)
from galaxy_test.driver import integration_util


class QuotaIntegrationTestCase(integration_util.IntegrationTestCase):
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["enable_quotas"] = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_quota_crud(self):
        quotas = self.dataset_populator.get_quotas()
        assert len(quotas) == 0

        payload = {
            'name': 'defaultquota1',
            'description': 'first default quota',
            'amount': '100MB',
            'operation': '=',
            'default': 'registered',
        }
        self.dataset_populator.create_quota(payload)

        quotas = self.dataset_populator.get_quotas()
        assert len(quotas) == 1
