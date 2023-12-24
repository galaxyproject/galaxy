import random
from typing import List
from urllib.parse import parse_qsl

from galaxy.util import UNKNOWN
from galaxy_test.base.decorators import requires_admin
from galaxy_test.base.populators import (
    DatasetPopulator,
    wait_on,
)
from ._framework import ApiTestCase


class TestDisplayApplicationsApi(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_index(self):
        response = self._get("display_applications")
        self._assert_status_code_is(response, 200)
        as_list = response.json()
        assert isinstance(as_list, list)
        assert len(as_list) > 0
        for display_app in as_list:
            self._assert_has_keys(display_app, "id", "name", "version", "filename_", "links")

    @requires_admin
    def test_reload_as_admin(self):
        response = self._post("display_applications/reload", admin=True)
        self._assert_status_code_is(response, 200)

    @requires_admin
    def test_reload_with_some_ids(self):
        response = self._get("display_applications")
        self._assert_status_code_is(response, 200)
        display_apps = response.json()
        all_ids = [display_app["id"] for display_app in display_apps]
        input_ids = self._get_half_random_items(all_ids)
        payload = {"ids": input_ids}
        response = self._post("display_applications/reload", payload, admin=True, json=True)
        self._assert_status_code_is(response, 200)
        reloaded = response.json()["reloaded"]
        assert len(reloaded) == len(input_ids)
        assert all(elem in reloaded for elem in input_ids)

    @requires_admin
    def test_reload_unknown_returns_as_failed(self):
        unknown_id = UNKNOWN
        payload = {"ids": [unknown_id]}
        response = self._post("display_applications/reload", payload, admin=True, json=True)
        self._assert_status_code_is(response, 200)
        reloaded = response.json()["reloaded"]
        failed = response.json()["failed"]
        assert len(reloaded) == 0
        assert len(failed) == 1
        assert unknown_id in failed

    def test_reload_as_non_admin_returns_403(self):
        response = self._post("display_applications/reload")
        self._assert_status_code_is(response, 403)

    def test_get_display_application_link_bam(self, history_id):
        # a controller route, but used in external apps. IMO qualifies (and can be used) as API
        instance_url = self.galaxy_interactor.api_url.split("/api")[0]
        for display_app_url in self._setup_igv_datasets(history_id=history_id, instance_url=instance_url):
            # wait for eventual conversion to finish
            wait_on(
                lambda display_app_url=display_app_url: True
                if self._get(display_app_url, allow_redirects=False).status_code == 302
                else None,
                "display application to become ready",
            )
            response = self._get(display_app_url, allow_redirects=False)
            components = parse_qsl(response.next.url)
            params = dict(components[1:])
            redirect_url = components[0][1]
            assert redirect_url.startswith(instance_url)
            data_response = self._get(redirect_url, data=params)
            data_response.raise_for_status()
            assert data_response.content

    def _setup_igv_datasets(self, history_id, instance_url: str):
        dataset_app_combinations = {
            "1.bam": "igv_bam/local_default",
            "test.vcf": "igv_vcf/local_default",
            "test.vcf.gz": "igv_vcf/local_default",
            "5.gff": "igv_gff/local_default",
            "1.bigwig": "igv_bigwig/local_default",
            "1.fasta": "igv_fasta/local_default",
        }
        display_urls = []
        for file_name, display_app_link in dataset_app_combinations.items():
            test_file = self.test_data_resolver.get_filename(file_name)
            test_dataset = self.dataset_populator.new_dataset(
                history_id, content=open(test_file, "rb"), file_type="auto", wait=True
            )
            display_app_url = f"{instance_url}/display_application/{test_dataset['dataset_id']}/{display_app_link}"
            display_urls.append(display_app_url)
        return display_urls

    def _get_half_random_items(self, collection: List[str]) -> List[str]:
        half_num_items = int(len(collection) / 2)
        rval = random.sample(collection, half_num_items)
        return rval
