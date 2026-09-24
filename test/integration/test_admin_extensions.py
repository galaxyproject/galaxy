"""Integration tests for the Admin panel extensions API."""

import os

from galaxy_test.driver import integration_util

EXTENSION_CONFIG = """
id: example
section: Example Section
items:
  - id: framed
    type: link
    title: Framed Page
    url: /welcome
  - id: external
    type: link
    title: External Page
    url: https://galaxyproject.org
    target: new_tab
"""


class TestAdminExtensionsIntegration(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        extensions_dir = cls._test_driver.mkdtemp()
        extension_dir = os.path.join(extensions_dir, "example")
        os.makedirs(extension_dir)
        with open(os.path.join(extension_dir, "config.yml"), "w") as fh:
            fh.write(EXTENSION_CONFIG)
        config["admin_extensions_dir"] = extensions_dir

    def test_admin_lists_extensions(self):
        response = self._get("admin/extensions", admin=True)
        self._assert_status_code_is_ok(response)
        extensions = response.json()
        assert len(extensions) == 1
        extension = extensions[0]
        assert extension["id"] == "example"
        assert extension["section"] == "Example Section"
        items = {item["id"]: item for item in extension["items"]}
        assert items["framed"]["target"] == "iframe"
        assert items["framed"]["url"] == "/welcome"
        assert items["external"]["target"] == "new_tab"

    def test_non_admin_is_forbidden(self):
        response = self._get("admin/extensions")
        self._assert_status_code_is(response, 403)


class TestAdminExtensionsUnconfiguredIntegration(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["admin_extensions_dir"] = cls._test_driver.mkdtemp()

    def test_empty_when_no_extensions(self):
        response = self._get("admin/extensions", admin=True)
        self._assert_status_code_is_ok(response)
        assert response.json() == []
