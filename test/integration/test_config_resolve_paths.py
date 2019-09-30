import os

from base import integration_util


class ConfigResolvePathsTestCase(integration_util.IntegrationTestCase):
    """
    Test automatic path resolution of configuration properties that use the
    'path_resolves_to' attribute.
    """
    def setUp(self):
        super(ConfigResolvePathsTestCase, self).setUp()
        self.data_dir = self._app.config.data_dir

    def get_default(self, key):
        return self._app.config.appschema[key]['default']

    def test_resolve_openid_consumer_cache_path(self):
        schema_default = self.get_default('openid_consumer_cache_path')
        expect = os.path.join(self.data_dir, schema_default)
        assert expect == self._app.config.openid_consumer_cache_path

    def test_resolve_citation_cache_data_dir(self):
        schema_default = self.get_default('citation_cache_data_dir')
        expect = os.path.join(self.data_dir, schema_default)
        assert expect == self._app.config.citation_cache_data_dir

    def test_resolve_citation_cache_lock_dir(self):
        schema_default = self.get_default('citation_cache_lock_dir')
        expect = os.path.join(self.data_dir, schema_default)
        assert expect == self._app.config.citation_cache_lock_dir

    def test_resolve_file_path(self):
        schema_default = self.get_default('file_path')
        expect = os.path.join(self.data_dir, schema_default)
        assert expect == self._app.config.file_path
