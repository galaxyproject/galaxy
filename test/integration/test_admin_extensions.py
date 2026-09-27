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
  - id: settings
    type: form
    title: Example Settings
    description: Values used by the example.
    inputs:
      - name: retries
        key: example.retries
        type: integer
        label: Retries
        default: 3
        min: 0
        max: 10
      - name: enabled
        type: boolean
        label: Enabled
        default: true
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
        response = self._get("admin/extensions/example/items/settings/form")
        self._assert_status_code_is(response, 403)
        response = self._put("admin/extensions/example/items/settings/form", data={"retries": 1}, json=True)
        self._assert_status_code_is(response, 403)

    def test_form_round_trip(self):
        response = self._get("admin/extensions/example/items/settings/form", admin=True)
        self._assert_status_code_is_ok(response)
        form = response.json()
        assert form["title"] == "Example Settings"
        assert form["message"] == "Values used by the example."
        inputs = {i["name"]: i for i in form["inputs"]}
        assert inputs["retries"]["value"] == 3
        assert inputs["retries"]["type"] == "integer"
        assert inputs["enabled"]["value"] is True

        response = self._put(
            "admin/extensions/example/items/settings/form",
            data={"retries": "7", "enabled": False},
            admin=True,
            json=True,
        )
        self._assert_status_code_is_ok(response)
        saved = response.json()
        assert saved["message"] == "Settings saved."
        inputs = {i["name"]: i for i in saved["inputs"]}
        assert inputs["retries"]["value"] == 7
        assert inputs["enabled"]["value"] is False

        response = self._get("admin/extensions/example/items/settings/form", admin=True)
        inputs = {i["name"]: i for i in response.json()["inputs"]}
        assert inputs["retries"]["value"] == 7

    def test_form_rejects_invalid_values(self):
        response = self._put(
            "admin/extensions/example/items/settings/form", data={"retries": 99}, admin=True, json=True
        )
        self._assert_status_code_is(response, 400)
        response = self._put("admin/extensions/example/items/settings/form", data={"nope": 1}, admin=True, json=True)
        self._assert_status_code_is(response, 400)

    def test_form_endpoints_reject_link_items_and_unknown_items(self):
        response = self._get("admin/extensions/example/items/framed/form", admin=True)
        self._assert_status_code_is(response, 404)
        response = self._get("admin/extensions/example/items/missing/form", admin=True)
        self._assert_status_code_is(response, 404)


class TestAdminExtensionsUnconfiguredIntegration(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["admin_extensions_dir"] = cls._test_driver.mkdtemp()

    def test_empty_when_no_extensions(self):
        response = self._get("admin/extensions", admin=True)
        self._assert_status_code_is_ok(response)
        assert response.json() == []
