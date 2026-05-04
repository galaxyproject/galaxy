"""Integration tests for tool source storage backends.

These tests configure Galaxy to use different tool source storage backends
and verify that the toolbox boots and serves tools through the API.
Dataset uploads / job execution are exercised by Galaxy's general
integration suite — these tests focus only on the tool source storage
plumbing.
"""

import os
import tempfile

from galaxy_test.driver import integration_util


class BaseToolSourceStorageIntegrationTestCase(integration_util.IntegrationTestCase):
    """Base class for tool source storage integration tests."""

    framework_tool_and_types = True

    def _test_api_tools_list(self):
        response = self._get("tools")
        self._assert_status_code_is(response, 200)
        tools = response.json()
        assert len(tools) > 0, "Expected at least one tool to be loaded"

    def _test_api_tools_show(self, tool_id: str = "cat1"):
        response = self._get(f"tools/{tool_id}")
        self._assert_status_code_is(response, 200)
        tool_info = response.json()
        assert tool_info["id"] == tool_id


class TestDatabaseToolSourceStorage(BaseToolSourceStorageIntegrationTestCase):
    """Integration tests with database tool source storage backend."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["tool_source_store"] = "database"

    def test_api_tools_list(self):
        self._test_api_tools_list()

    def test_api_tools_show(self):
        self._test_api_tools_show()

    def test_default_store_is_database_backend(self):
        from galaxy.tool_source_store.database import DatabaseToolSourceStore

        assert isinstance(self._app.tool_source_store, DatabaseToolSourceStore)


class TestCompositeToolSourceStorage(BaseToolSourceStorageIntegrationTestCase):
    """Galaxy boots with a default DB store + a per-conf read-only sqlite store.

    Verifies the composite wiring: a tool_conf carrying ``store="cvmfs_main"``
    plus ``use_lazy_toolbox: true`` causes ``build_tool_source_store`` to wrap
    the default backend in a composite store.
    """

    _sqlite_path: str
    _conf_path: str
    _tmpdir: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._tmpdir = tempfile.mkdtemp(prefix="composite_tss_")
        cls._sqlite_path = os.path.join(cls._tmpdir, "sources.sqlite")

        from galaxy.tool_source_store.sqlalchemy import SqlAlchemyToolSourceStore

        SqlAlchemyToolSourceStore(path=cls._sqlite_path).count()

        cls._conf_path = os.path.join(cls._tmpdir, "extra_tool_conf.xml")
        with open(cls._conf_path, "w") as f:
            f.write('<?xml version="1.0"?>\n<toolbox store="cvmfs_main"/>\n')

        config["tool_source_store"] = "database"
        config["use_lazy_toolbox"] = True
        existing_confs = config.get("tool_config_file") or "config/tool_conf.xml.sample"
        if isinstance(existing_confs, str):
            config["tool_config_file"] = f"{existing_confs},{cls._conf_path}"
        else:
            config["tool_config_file"] = list(existing_confs) + [cls._conf_path]
        config["tool_source_stores"] = {
            "cvmfs_main": {
                "backend": "sqlalchemy",
                "path": cls._sqlite_path,
                "read_only": True,
            }
        }

    def test_composite_store_is_wired(self):
        # The boot path must produce a CompositeToolSourceStore when a
        # tool_conf opts into a named per-conf store and use_lazy_toolbox
        # is enabled. Verifying the live app's store directly is more
        # robust than relying on /api/tools, which depends on whether the
        # store was populated in advance.
        from galaxy.tool_source_store.composite import CompositeToolSourceStore

        assert isinstance(self._app.tool_source_store, CompositeToolSourceStore)

    def test_api_tools_list_populated_via_bootstrap(self):
        # With use_lazy_toolbox=true and an empty store, LazyToolBox
        # auto-bootstraps from the configured tool confs on first boot;
        # /api/tools must therefore return a non-empty tool list.
        response = self._get("tools")
        self._assert_status_code_is(response, 200)
        tools = response.json()
        assert isinstance(tools, list)
        assert len(tools) > 0, "Bootstrap should have populated the store with framework tools"
