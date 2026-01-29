from urllib.parse import parse_qsl

from galaxy.tool_util.verify.wait import wait_on
from galaxy_test.base.populators import DatasetPopulator
from .test_containerized_jobs import ContainerizedIntegrationTestCase


class TestDisplayApplicationTestCase(ContainerizedIntegrationTestCase):
    dataset_populator: DatasetPopulator
    container_type = "docker"

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_get_display_application_links(self, history_id):
        # a controller route, but used in external apps. IMO qualifies (and can be used) as API
        instance_url = self.galaxy_interactor.api_url.split("/api")[0]
        for display_app_url in self._setup_igv_datasets(history_id=history_id, instance_url=instance_url):
            # wait for eventual conversion to finish
            wait_on(
                lambda display_app_url=display_app_url: (
                    True if self._get(display_app_url, allow_redirects=False).status_code == 302 else None
                ),
                "display application to become ready",
                timeout=60,
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
