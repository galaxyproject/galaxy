from base import integration_util


class ConfigDefaultsTestCase(integration_util.IntegrationTestCase):
    """
    Test automatic creation of configuration properties and assignment of
    default values specified in the schema.
    """
    def get_default(self, key):
        return self._app.config.appschema[key]['default']

    def test_default_database_engine_option_pool_recycle(self):
        expect = self.get_default('database_engine_option_pool_recycle')
        assert expect == self._app.config.database_engine_option_pool_recycle

    def test_default_database_engine_option_server_side_cursors(self):
        expect = self.get_default('database_engine_option_server_side_cursors')
        assert expect == self._app.config.database_engine_option_server_side_cursors

    def test_default_database_query_profiling_proxy(self):
        expect = self.get_default('database_query_profiling_proxy')
        assert expect == self._app.config.database_query_profiling_proxy
