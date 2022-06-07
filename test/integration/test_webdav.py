# Before running this test, start nginx+webdav in Docker using following command:
# docker run -v `pwd`/test/integration/webdav/data:/media  -e WEBDAV_USERNAME=alice -e WEBDAV_PASSWORD=secret1234 -p 7083:7083 jmchilton/webdavdev
# Apache Docker host (shown next) doesn't work because displayname not set in response.
# docker run -v `pwd`/test/integration/webdav:/var/lib/dav  -e AUTH_TYPE=Basic -e USERNAME=alice -e PASSWORD=secret1234  -e LOCATION=/ -p 7083:80 bytemark/webdav

import os

import pytest

from galaxy_test.base import api_asserts
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_JOB_CONF = os.path.join(SCRIPT_DIRECTORY, "file_sources_conf.yml")

skip_if_no_webdav = pytest.mark.skipif(not os.environ.get("GALAXY_TEST_WEBDAV"), reason="GALAXY_TEST_WEBDAV not set")


@skip_if_no_webdav
class WebDavIntegrationTestCase(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["file_sources_config_file"] = FILE_SOURCES_JOB_CONF

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_simple_usage(self):
        plugin_config_response = self.galaxy_interactor.get("remote_files/plugins")
        api_asserts.assert_status_code_is_ok(plugin_config_response)
        plugins = plugin_config_response.json()
        assert len(plugins) == 1
        assert plugins[0]["type"] == "webdav"
        assert plugins[0]["uri_prefix"] == "gxfiles://test1"

        data = {"target": "gxfiles://test1"}
        list_response = self.galaxy_interactor.get("remote_files", data)
        api_asserts.assert_status_code_is_ok(list_response)
        remote_files = list_response.json()
        print(remote_files)

        with self.dataset_populator.test_history() as history_id:
            new_dataset = self.dataset_populator.new_dataset(history_id, content="gxfiles://test1/a", assert_ok=True)
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=new_dataset)
            assert content == "a\n", content
