"""A collection exported as a link and imported from it, as between two Galaxy servers."""

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


def _element(name: str, content: str) -> dict:
    return {
        "src": "pasted",
        "paste_content": content,
        "name": name,
        "ext": "bed",
        "dbkey": "hg38",
        "tags": ["group:demo"],
    }


class TestGalaxyLinkImportIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        # The "other" Galaxy is this one, on a loopback address that link imports otherwise refuse.
        config["fetch_url_allowlist"] = ["127.0.0.0/8", "::1"]

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_a_collection_keeps_its_structure_types_and_tags(self):
        source_id = self.dataset_populator.new_history()
        target = {
            "destination": {"type": "hdca"},
            "collection_type": "paired",
            "name": "sample1",
            "elements": [_element("forward", "chr1\t1\t10\n"), _element("reverse", "chr1\t5\t20\n")],
        }
        self.dataset_populator.fetch({"history_id": source_id, "targets": [target]}, wait=True)
        hdca = self.dataset_populator.get_history_collection_details(source_id)

        prepared = self._post(
            f"histories/{source_id}/contents/dataset_collections/{hdca['id']}/prepare_store_download",
            {"model_store_format": "tar.gz", "include_files": True},
            json=True,
        ).json()
        self.dataset_populator.wait_for_download_ready(prepared["storage_request_id"])
        link = f"{self.url.rstrip('/')}/api/short_term_storage/{prepared['storage_request_id']}"

        target_id = self.dataset_populator.new_history()
        response = self.dataset_populator.create_contents_from_store_raw(
            target_id, {"store_content_uri": link, "model_store_format": "tar.gz", "discarded_data": "forbid"}
        )
        response.raise_for_status()

        imported = self.dataset_populator.get_history_collection_details(target_id)
        assert imported["collection_type"] == "paired"
        elements = {e["element_identifier"]: e["object"] for e in imported["elements"]}
        assert sorted(elements) == ["forward", "reverse"]
        for identifier, content in (("forward", "chr1\t1\t10\n"), ("reverse", "chr1\t5\t20\n")):
            dataset = elements[identifier]
            assert dataset["file_ext"] == "bed"
            assert dataset["genome_build"] == "hg38"
            assert dataset["tags"] == ["group:demo"]
            assert self.dataset_populator.get_history_dataset_content(target_id, dataset_id=dataset["id"]) == content
