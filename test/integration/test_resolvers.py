"""Integration tests for the conda dependency resolution."""

import os
from base import integration_util
from base.api import ApiTestCase

GNUPLOT = {u'version': u'4.6', u'type': u'package', u'name': u'gnuplot'}

class CondaResolutionIntegrationTestCase(integration_util.IntegrationTestCase, ApiTestCase):
    """Test conda dependency resolution through API."""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["conda_auto_init"] = True
        config["conda_prefix"] = '/tmp/conda'

    def test_dependency_install( self ):
        data = GNUPLOT
        create_response = self._post( "dependency_resolvers/dependency", data=data, admin=True )
        self._assert_status_code_is( create_response, 200 )
        response = create_response.json()
        assert response['dependency_type'] == 'conda' and response['exact'] == True
