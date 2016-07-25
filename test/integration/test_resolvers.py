"""Integration tests for the conda dependency resolution."""

import os
import shutil
from base import integration_util
import svgwrite  # svgwrite import after twill, otherwise twill's pyparsing breaks svgwrite import.
from base.api import ApiTestCase
from tempfile import mkdtemp

GNUPLOT = {u'version': u'4.6', u'type': u'package', u'name': u'gnuplot'}

class CondaResolutionIntegrationTestCase(integration_util.IntegrationTestCase, ApiTestCase):
    """Test conda dependency resolution through API."""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls.conda_tmp_prefix = mkdtemp()
        config["conda_auto_init"] = True
        config["conda_prefix"] = os.path.join(cls.conda_tmp_prefix, 'conda')

    @classmethod
    def tearDownClass(cls):
        """Shutdown Galaxy server and cleanup temp directory."""
        shutil.rmtree(cls.conda_tmp_prefix)
        cls._test_driver.tear_down()
        cls._app_available = False

    def test_dependency_before_install( self ):
        """
        GET request to dependency_resolvers/dependency with dependency.
        Should not be installed (response['dependency_type'] == 'null').
        """
        data = GNUPLOT
        create_response = self._get( "dependency_resolvers/dependency", data=data, admin=True )
        self._assert_status_code_is( create_response, 200 )
        response = create_response.json()
        assert response['dependency_type'] == 'null' and response['exact'] == True

    def test_dependency_install( self ):
        """
        POST request to dependency_resolvers/dependency with GNUPLOT dependency.
        Should install via conda (response[dependency_type] == 'conda').
        """
        data = GNUPLOT
        create_response = self._post( "dependency_resolvers/dependency", data=data, admin=True )
        self._assert_status_code_is( create_response, 200 )
        response = create_response.json()
        assert response['dependency_type'] == 'conda' and response['exact'] == True

    def test_dependency_install_not_exact(self):
        """
        POST request to dependency_resolvers/dependency with GNUPLOT dependency.
        Should install through conda (response['dependency_type'] == 'conda'),
        but version 4.9999 does not exist, so response['exact'] == False.
        """
        data = GNUPLOT.copy()
        data['version'] = '4.9999'
        create_response = self._post("dependency_resolvers/dependency", data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        assert response['dependency_type'] == 'conda' and response['exact'] == False

    def test_dependency_status_installed_exact( self ):
        """
        GET request to dependency_resolvers/dependency with GNUPLOT dependency.
        Should be installed through conda (response['dependency_type'] == 'conda').
        """
        data = GNUPLOT
        create_response = self._get( "dependency_resolvers/dependency", data=data, admin=True )
        self._assert_status_code_is( create_response, 200 )
        response = create_response.json()
        assert response['dependency_type'] == 'conda' and response['exact'] == True

    def test_dependency_status_installed_not_exact( self ):
        """
        GET request to dependency_resolvers/dependency with GNUPLOT dependency.
        Should be installed through conda (response['dependency_type'] == 'conda'),
        but version 4.9999 does not exist.
        """
        data = GNUPLOT.copy()
        data['version'] = '4.9999'
        create_response = self._get( "dependency_resolvers/dependency", data=data, admin=True )
        self._assert_status_code_is( create_response, 200 )
        response = create_response.json()
        assert response['dependency_type'] == 'conda' and response['exact'] == False