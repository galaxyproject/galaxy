from galaxy_test.driver import integration_util

SITES = [
    {"label": "Base site", "url": "https://usegalaxy.example.org"},
    {"label": "Single Cell Omics", "url": "https://singlecell.usegalaxy.example.org/"},
]


class TestSubdomainSwitcherConfiguration(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["subdomain_switcher"] = SITES

    def test_configuration_is_exposed_to_registered_and_anonymous_users(self):
        response = self.galaxy_interactor.get("configuration")
        response.raise_for_status()
        assert response.json()["subdomain_switcher"] == SITES

        with self._different_user(anon=True):
            response = self.galaxy_interactor.get("configuration")
        response.raise_for_status()
        assert response.json()["subdomain_switcher"] == SITES
