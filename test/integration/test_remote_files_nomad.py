import pytest

from galaxy.util.unittest_utils import skip_if_site_down
from galaxy_test.base import api_asserts
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

pytest.importorskip("nomad_fsspec")

# "demo example data" on nomad-lab.eu
DEMO_UPLOAD = "gxfiles://nomad/wWgAnNZNQxOHLf97H62dgw/Xa2LB__ESiKu-odRBPJhjA"
DEMO_DIRECTORY = f"{DEMO_UPLOAD}/nomad-demo-data/BrK_svSe/TBCC006.ABC"

skip_if_nomad_down = skip_if_site_down(
    "https://nomad-lab.eu/prod/v1/api/v1/info",
    unavailable_pattern=r"NOMAD at nomad-lab\.eu answered HTTP (429|5\d\d)|Request to NOMAD at nomad-lab\.eu failed",
)


class TestNomadFileSourceIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["file_sources"] = [
            {"type": "nomad", "id": "nomad"},
            {"type": "nomad", "id": "nomad-internal", "base_url": "http://169.254.169.254"},
        ]

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @skip_if_nomad_down
    def test_find_and_import_a_public_file(self):
        response = self.galaxy_interactor.get("remote_files", {"target": "gxfiles://nomad", "query": " demo example "})
        api_asserts.assert_status_code_is_ok(response)
        assert "gxfiles://nomad/wWgAnNZNQxOHLf97H62dgw" in [entry["uri"] for entry in response.json()]

        response = self.galaxy_interactor.get("remote_files", {"target": DEMO_DIRECTORY})
        api_asserts.assert_status_code_is_ok(response)
        sizes = {entry["name"]: entry["size"] for entry in response.json()}
        assert sizes == {"vasprun.xml.relax1": 648412, "vasprun.xml.relax2": 424235}

        with self.dataset_populator.test_history() as history_id:
            self.dataset_populator.fetch(
                {
                    "history_id": history_id,
                    "targets": [
                        {
                            "destination": {"type": "hdas"},
                            "elements": [{"src": "url", "url": f"{DEMO_DIRECTORY}/vasprun.xml.relax2"}],
                        }
                    ],
                }
            )
            dataset = self.dataset_populator.get_history_dataset_details(history_id)
            assert dataset["name"] == "vasprun.xml.relax2"
            assert dataset["file_size"] == 424235

    def test_refuses_a_local_address_and_a_recursive_listing_of_all_datasets(self):
        response = self.galaxy_interactor.get("remote_files", {"target": "gxfiles://nomad-internal"})
        assert response.status_code in (400, 403), response.text
        assert "not permitted" in response.text

        response = self.galaxy_interactor.get("remote_files", {"target": "gxfiles://nomad", "recursive": "true"})
        api_asserts.assert_status_code_is(response, 400)
