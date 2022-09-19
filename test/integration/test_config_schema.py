from galaxy_test.driver import integration_util


class ConfigSchemaTestCase(integration_util.IntegrationTestCase):
    def test_schema_path_resolution_graph(self):
        # Run schema's validation method; throws error if schema invalid
        schema = self._app.config.schema
        schema.validate_path_resolution_graph()
