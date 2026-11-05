"""Runtime-installed visualization packages, served from the managed package store through the API."""

import os

import yaml

from galaxy_test.driver.integration_util import IntegrationTestCase

TEST_VISUALIZATION_PLUGINS_DIR = os.path.join(os.path.dirname(__file__), "test_visualization_plugins")

SEEDED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<visualization name="Seeded Package">
    <description>A runtime package laid down in the store the way an npm install would</description>
    <data_sources>
        <data_source>
            <model_class>HistoryDatasetAssociation</model_class>
        </data_source>
    </data_sources>
    <params>
        <param required="true">dataset_id</param>
    </params>
    <entry_point entry_point_type="script" src="index.js" />
</visualization>
"""
SEEDED_JS = "console.log('seeded');\n"


class TestVisualizationPackagesStaticRoute(IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        managed = cls._test_driver.mkdtemp()
        store = os.path.join(managed, "visualization_packages")
        static = os.path.join(store, "seeded", "static")
        os.makedirs(static)
        with open(os.path.join(static, "seeded.xml"), "w") as f:
            f.write(SEEDED_XML)
        with open(os.path.join(static, "index.js"), "w") as f:
            f.write(SEEDED_JS)
        with open(os.path.join(store, "seeded", "package.json"), "w") as f:
            f.write('{"name": "@galaxyproject/seeded", "version": "1.0.0"}')
        config_file = os.path.join(managed, "visualization_packages.yml")
        with open(config_file, "w") as f:
            yaml.safe_dump({"seeded": {"package": "@galaxyproject/seeded", "version": "1.0.0", "enabled": True}}, f)
        config["visualization_packages_dir"] = store
        config["visualization_packages_config_file"] = config_file
        # gives the registry a built-in plugin to check the route refuses
        config["visualization_plugins_directory"] = TEST_VISUALIZATION_PLUGINS_DIR

    def _static(self, file_path, headers=None):
        return self._get(f"plugins/seeded/static/{file_path}", headers=headers)

    def test_serves_runtime_package_files(self):
        plugin = self._get("plugins/seeded").json()
        assert plugin["href"].endswith("/api/plugins/seeded/static")

        response = self._static("index.js")
        self._assert_status_code_is(response, 200)
        assert response.text == SEEDED_JS
        assert response.headers["cache-control"] == "no-cache"

    def test_refuses_paths_outside_static_and_builtin_plugins(self):
        self._assert_status_code_is(self._static("..%2Fpackage.json"), 404)
        self._assert_status_code_is(self._static("%2Fetc%2Fpasswd"), 404)
        self._assert_status_code_is(self._get("plugins/jupyterlite/static/jupyterlite.xml"), 404)

    def test_matching_etag_is_not_modified(self):
        # no-cache makes every load revalidate, so revalidating has to be cheap
        etag = self._static("index.js").headers["etag"]
        response = self._static("index.js", headers={"If-None-Match": etag})
        self._assert_status_code_is(response, 304)
        assert response.content == b""
        assert response.headers["etag"] == etag

        response = self._static("index.js", headers={"If-None-Match": '"some-other-version"'})
        self._assert_status_code_is(response, 200)

    def test_head_on_runtime_file(self):
        response = self._head("plugins/seeded/static/index.js")
        self._assert_status_code_is(response, 200)
        assert int(response.headers["content-length"]) == len(SEEDED_JS)

    def test_disabled_package_is_not_served(self):
        toggle = "admin/visualizations/seeded/toggle"
        self._assert_status_code_is(self._put(toggle, {"enabled": False}, admin=True, json=True), 200)
        try:
            self._assert_status_code_is(self._static("index.js"), 404)
        finally:
            self._assert_status_code_is(self._put(toggle, {"enabled": True}, admin=True, json=True), 200)
        self._assert_status_code_is(self._static("index.js"), 200)
