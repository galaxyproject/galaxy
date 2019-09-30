import os

from base import integration_util


class ConfigResolvePathsTestCase(integration_util.IntegrationTestCase):

    def test_resolve_openid_consumer_cache_path(self):
        data_dir = self._app.config.data_dir
        schema_default = self._app.config.appschema['openid_consumer_cache_path']['default']
        expected = os.path.join(data_dir, schema_default)
        assert expected == self._app.config.openid_consumer_cache_path

    def test_resolve_citation_cache_data_dir(self):
        data_dir = self._app.config.data_dir
        schema_default = self._app.config.appschema['citation_cache_data_dir']['default']
        expected = os.path.join(data_dir, schema_default)
        assert expected == self._app.config.citation_cache_data_dir

    def test_resolve_citation_cache_lock_dir(self):
        data_dir = self._app.config.data_dir
        schema_default = self._app.config.appschema['citation_cache_lock_dir']['default']
        expected = os.path.join(data_dir, schema_default)
        assert expected == self._app.config.citation_cache_lock_dir
