"""Integration tests for framework configuration code."""

from requests import options

from galaxy_test.driver import integration_util

ENDPOINT_WITH_CORS = "workflow_landings"
ENDPOINT_WITHOUT_EXPLICIT_CORS = "licenses"
WSGI_ENDPOINT = "tools"


class BaseWebFrameworkTestCase(integration_util.IntegrationTestCase):
    def _options(self, headers=None, endpoint=ENDPOINT_WITH_CORS):
        url = self._api_url(endpoint)
        options_response = options(url, headers=headers or {})
        return options_response


class TestCorsDefaultIntegration(BaseWebFrameworkTestCase):
    def test_options(self):
        headers = {
            "Access-Control-Request-Method": "GET",
            "origin": "http://192.168.0.101:8083",
        }
        options_response = self._options(headers, ENDPOINT_WITHOUT_EXPLICIT_CORS)
        options_response.raise_for_status()
        assert "access-control-allow-origin" not in options_response.headers

    def test_options_wsgi(self):
        # Tests legacy handling
        headers = {
            "Access-Control-Request-Method": "GET",
            "origin": "http://192.168.0.101:8083",
        }
        options_response = self._options(headers, WSGI_ENDPOINT)
        options_response.raise_for_status()
        assert "access-control-allow-origin" not in options_response.headers

    def test_origin_not_allowed_default(self):
        headers = {
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
            "origin": "http://192.168.0.101:8083",
        }
        options_response = self._options(headers, ENDPOINT_WITHOUT_EXPLICIT_CORS)
        options_response.raise_for_status()
        assert "access-control-allow-origin" not in options_response.headers

    def test_origin_explicitly_allowed(self):
        headers = {
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
            "Origin": "http://192.168.0.101:8083",
        }
        options_response = self._options(headers, ENDPOINT_WITH_CORS)
        options_response.raise_for_status()
        assert options_response.headers["access-control-allow-origin"] == "http://192.168.0.101:8083"


class TestAllowOriginIntegration(BaseWebFrameworkTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["allowed_origin_hostnames"] = "192.168.0.101,/.*.galaxyproject.org/"

    def test_origin_allowed_if_configured(self):
        headers = {
            "Access-Control-Request-Method": "GET",
            "origin": "http://192.168.0.101:8083",
            "Access-Control-Request-Headers": "Authorization",
        }
        options_response = self._options(headers, ENDPOINT_WITHOUT_EXPLICIT_CORS)
        options_response.raise_for_status()
        assert "access-control-allow-origin" in options_response.headers
        assert options_response.headers["access-control-allow-origin"] == "http://192.168.0.101:8083"
        assert options_response.headers["access-control-max-age"] == "600"

    def test_origin_allowed_if_configured_via_regex(self):
        headers = {
            "Access-Control-Request-Method": "GET",
            "origin": "http://rna.galaxyproject.org",
            "Access-Control-Request-Headers": "Authorization",
        }
        options_response = self._options(headers, ENDPOINT_WITHOUT_EXPLICIT_CORS)
        options_response.raise_for_status()
        assert "access-control-allow-origin" in options_response.headers
        assert options_response.headers["access-control-allow-origin"] == "http://rna.galaxyproject.org"
        assert options_response.headers["access-control-max-age"] == "600"

    def test_origin_not_allowed_if_not_in_configured_list(self):
        headers = {
            "Access-Control-Request-Method": "GET",
            "origin": "http://192.168.0.102:8083",  # swapped ip by one
            "Access-Control-Request-Headers": "Authorization",
        }
        options_response = self._options(headers, ENDPOINT_WITHOUT_EXPLICIT_CORS)
        assert options_response.status_code == 400
