from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class TestPrefixUrlSerializationIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    url_prefix = "/galaxypf"

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["galaxy_url_prefix"] = "/galaxypf"

    def test_display_application_prefix_handling(self, history_id: str) -> None:
        hda = self.dataset_populator.new_dataset(
            history_id, content="chr1\t1\t2", file_type="interval", dbkey="hg18", wait=True
        )
        details_response = self.dataset_populator.get_history_dataset_details(
            history_id=history_id, dataset_id=hda["id"]
        )
        # verify old style display app contains correct link back to galaxy
        ucsc = details_response["display_types"][0]
        assert ucsc["label"] == "display at UCSC"
        assert "galaxypf" in ucsc["links"][0]["href"].split("redirect_url=")[-1]
        # verify new style display app links contain prefix
        display_apps = details_response["display_apps"]
        for display_app in display_apps:
            href = display_app["links"][0]["href"]
            # This is a little inconsistent since most other references are generated without prefix
            # but it's a real pain to work with the reverse lookup in routes and the callback URLs
            # do need to include the prefix.
            assert href.startswith(f"{self.url_prefix}/display_application")
            response = self._get(f"{self.url[:-(len(self.url_prefix) + 1)]}{href}")
            response.raise_for_status()
