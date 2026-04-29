"""Unit tests for VisualizationPackageManager."""

import json
import os
import shutil
import subprocess
import tempfile
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from galaxy import exceptions
from galaxy.managers.visualization_admin import VisualizationPackageManager


@pytest.fixture()
def manager():
    """Create a VisualizationPackageManager with a temp directory as root."""
    tmpdir = tempfile.mkdtemp()
    app = MagicMock()
    app.config.root = tmpdir

    mgr = VisualizationPackageManager(app)
    yield mgr

    shutil.rmtree(tmpdir, ignore_errors=True)


def _create_installed_package(manager, viz_id, package_name="@galaxyproject/test", version="1.0.0"):
    """Helper to simulate an installed runtime package in the managed package store."""
    pkg_dir = manager.get_package_path(viz_id)
    os.makedirs(pkg_dir, exist_ok=True)
    with open(os.path.join(pkg_dir, "package.json"), "w") as f:
        json.dump({"name": package_name, "version": version}, f)
    manager.add_package_to_config(viz_id, package_name, version, enabled=True)
    return pkg_dir


def _create_runtime_viz_package(manager, viz_id, package_name="@galaxyproject/test", version="1.0.0", content="test"):
    """Helper to create a managed runtime package with static assets."""
    pkg_dir = _create_installed_package(manager, viz_id, package_name, version)
    static_dir = os.path.join(pkg_dir, "static")
    os.makedirs(static_dir, exist_ok=True)
    plugin_name = viz_id.split("/")[-1]
    with open(os.path.join(static_dir, f"{plugin_name}.xml"), "w") as f:
        f.write(f"<visualization name='{plugin_name}' />")
    with open(os.path.join(static_dir, "index.html"), "w") as f:
        f.write(content)
    return pkg_dir


def _create_viz_static(manager, viz_name, content="test"):
    """Helper to create config/plugins visualization static assets."""
    plugins_dir = os.path.join(
        manager.app.config.root,
        "config",
        "plugins",
        "visualizations",
        viz_name,
        "static",
    )
    os.makedirs(plugins_dir, exist_ok=True)
    with open(os.path.join(plugins_dir, "index.html"), "w") as f:
        f.write(content)
    plugin_name = viz_name.split("/")[-1]
    with open(os.path.join(plugins_dir, f"{plugin_name}.xml"), "w") as f:
        f.write(f"<visualization name='{plugin_name}' />")
    return plugins_dir


# --- Input validation ---


class TestVizIdValidation:
    def test_valid_simple_id(self, manager):
        manager.validate_viz_id("circster")

    def test_valid_id_with_hyphens(self, manager):
        manager.validate_viz_id("my-viz-plugin")

    def test_valid_nested_id(self, manager):
        manager.validate_viz_id("jqplot/jqplot_bar")

    def test_rejects_path_traversal(self, manager):
        with pytest.raises(exceptions.RequestParameterInvalidException):
            manager.validate_viz_id("../../etc/passwd")

    def test_rejects_empty(self, manager):
        with pytest.raises(exceptions.RequestParameterInvalidException):
            manager.validate_viz_id("")

    def test_rejects_spaces(self, manager):
        with pytest.raises(exceptions.RequestParameterInvalidException):
            manager.validate_viz_id("my viz")

    def test_rejects_semicolons(self, manager):
        with pytest.raises(exceptions.RequestParameterInvalidException):
            manager.validate_viz_id("viz; rm -rf /")


class TestNpmInputValidation:
    def test_valid_scoped_package(self, manager):
        manager.validate_npm_inputs("@galaxyproject/circster", "1.0.0")

    def test_valid_unscoped_package(self, manager):
        manager.validate_npm_inputs("some-package", "2.3.4")

    def test_valid_semver_with_prerelease(self, manager):
        manager.validate_npm_inputs("pkg", "1.0.0-beta.1")

    def test_rejects_path_traversal_in_package(self, manager):
        with pytest.raises(exceptions.RequestParameterInvalidException):
            manager.validate_npm_inputs("../../etc/passwd", "1.0.0")

    def test_rejects_shell_injection_in_package(self, manager):
        with pytest.raises(exceptions.RequestParameterInvalidException):
            manager.validate_npm_inputs("foo; rm -rf /", "1.0.0")

    def test_rejects_git_url_version(self, manager):
        with pytest.raises(exceptions.RequestParameterInvalidException):
            manager.validate_npm_inputs("pkg", "git+https://evil.com/repo")

    def test_rejects_file_url_version(self, manager):
        with pytest.raises(exceptions.RequestParameterInvalidException):
            manager.validate_npm_inputs("pkg", "file:../local-pkg")

    def test_rejects_range_version(self, manager):
        with pytest.raises(exceptions.RequestParameterInvalidException):
            manager.validate_npm_inputs("pkg", "^1.0.0")

    def test_rejects_latest_tag(self, manager):
        with pytest.raises(exceptions.RequestParameterInvalidException):
            manager.validate_npm_inputs("pkg", "latest")

    def test_rejects_incomplete_semver(self, manager):
        with pytest.raises(exceptions.RequestParameterInvalidException):
            manager.validate_npm_inputs("pkg", "1.2")


# --- Config management ---


class TestConfigManagement:
    def test_load_config_empty(self, manager):
        assert manager.load_config() == {}

    def test_save_and_load_config(self, manager):
        config = {
            "circster": {
                "package": "@galaxyproject/circster",
                "version": "1.0.0",
                "enabled": True,
            }
        }
        manager.save_config(config)
        assert manager.load_config() == config

    def test_add_package_to_config(self, manager):
        manager.add_package_to_config("circster", "@galaxyproject/circster", "1.0.0", enabled=True)
        config = manager.load_config()
        assert config["circster"]["package"] == "@galaxyproject/circster"
        assert config["circster"]["version"] == "1.0.0"
        assert config["circster"]["enabled"] is True

    def test_remove_package_from_config(self, manager):
        manager.add_package_to_config("circster", "@galaxyproject/circster", "1.0.0")
        manager.remove_package_from_config("circster")
        assert "circster" not in manager.load_config()

    def test_remove_nonexistent_is_noop(self, manager):
        manager.remove_package_from_config("nonexistent")
        assert manager.load_config() == {}

    def test_toggle_enabled(self, manager):
        manager.add_package_to_config("circster", "@galaxyproject/circster", "1.0.0", enabled=True)
        manager.toggle_package_enabled("circster", False)
        assert manager.load_config()["circster"]["enabled"] is False

    def test_toggle_nonexistent_raises(self, manager):
        with pytest.raises(exceptions.ObjectNotFound):
            manager.toggle_package_enabled("nonexistent", True)


# --- Package info ---


class TestPackageInfo:
    def test_get_package_info_missing(self, manager):
        assert manager.get_package_info("nonexistent") is None

    def test_get_package_info_present(self, manager):
        manager.add_package_to_config("circster", "@galaxyproject/circster", "2.0.0")
        info = manager.get_package_info("circster")
        assert info["version"] == "2.0.0"

    def test_is_package_installed_false(self, manager):
        assert manager.is_package_installed("circster") is False

    def test_is_package_installed_true(self, manager):
        os.makedirs(manager.get_package_path("circster"))
        assert manager.is_package_installed("circster") is True

    def test_get_package_metadata_with_package_json(self, manager):
        pkg_dir = manager.get_package_path("circster")
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, "package.json"), "w") as f:
            json.dump({"name": "@galaxyproject/circster", "description": "A viz"}, f)
        result = manager.get_package_metadata("circster")
        assert result["description"] == "A viz"

    def test_get_package_metadata_no_package_json(self, manager):
        os.makedirs(manager.get_package_path("circster"))
        assert manager.get_package_metadata("circster") == {}


# --- Package validation ---


class TestPackageValidation:
    def test_valid_package(self, manager):
        pkg_dir = manager.get_package_path("test_pkg")
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, "package.json"), "w") as f:
            json.dump({"name": "test", "version": "1.0.0"}, f)
        assert manager.validate_package_structure(pkg_dir) is True

    def test_missing_package_json(self, manager):
        pkg_dir = manager.get_package_path("test_pkg")
        os.makedirs(pkg_dir)
        with pytest.raises(exceptions.ConfigurationError, match="package.json"):
            manager.validate_package_structure(pkg_dir)

    def test_missing_required_field(self, manager):
        pkg_dir = manager.get_package_path("test_pkg")
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, "package.json"), "w") as f:
            json.dump({"name": "test"}, f)
        with pytest.raises(exceptions.ConfigurationError, match="version"):
            manager.validate_package_structure(pkg_dir)


# --- npm install (mocked subprocess) ---


class TestNpmInstall:
    @patch("galaxy.managers.visualization_admin.subprocess.run")
    def test_install_scoped_package(self, mock_run, manager):
        """Scoped packages resolve to node_modules/@scope/name."""
        target_dir = manager.get_package_path("circster")

        def side_effect(cmd, **kwargs):
            # Simulate npm creating the scoped package directory
            pkg_path = os.path.join(kwargs["cwd"], "node_modules", "@galaxyproject", "circster")
            os.makedirs(pkg_path, exist_ok=True)
            with open(os.path.join(pkg_path, "package.json"), "w") as f:
                json.dump({"name": "@galaxyproject/circster", "version": "1.0.0"}, f)
            result = MagicMock()
            result.returncode = 0
            return result

        mock_run.side_effect = side_effect

        result = manager.install_npm_package("@galaxyproject/circster", "1.0.0", target_dir)
        assert result["package"] == "@galaxyproject/circster"
        assert os.path.exists(os.path.join(target_dir, "package.json"))

    @patch("galaxy.managers.visualization_admin.subprocess.run")
    def test_install_unscoped_package(self, mock_run, manager):
        target_dir = manager.get_package_path("some_viz")

        def side_effect(cmd, **kwargs):
            pkg_path = os.path.join(kwargs["cwd"], "node_modules", "some-viz-package")
            os.makedirs(pkg_path, exist_ok=True)
            with open(os.path.join(pkg_path, "package.json"), "w") as f:
                json.dump({"name": "some-viz-package", "version": "2.0.0"}, f)
            result = MagicMock()
            result.returncode = 0
            return result

        mock_run.side_effect = side_effect

        result = manager.install_npm_package("some-viz-package", "2.0.0", target_dir)
        assert result["version"] == "2.0.0"

    @patch("galaxy.managers.visualization_admin.subprocess.run")
    def test_install_npm_failure(self, mock_run, manager):
        mock_run.return_value = MagicMock(returncode=1, stderr="npm ERR! 404 Not Found")
        target_dir = manager.get_package_path("bad_pkg")
        with pytest.raises(exceptions.InternalServerError, match="installation failed"):
            manager.install_npm_package("@galaxyproject/bad-pkg", "9.9.9", target_dir)

    @patch("galaxy.managers.visualization_admin.subprocess.run")
    def test_install_timeout(self, mock_run, manager):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="npm", timeout=300)
        target_dir = manager.get_package_path("slow_pkg")
        with pytest.raises(exceptions.InternalServerError, match="timed out"):
            manager.install_npm_package("@galaxyproject/slow", "1.0.0", target_dir)


# --- Install/uninstall/reinstall lifecycle ---


class TestInstallLifecycle:
    @patch("galaxy.managers.visualization_admin.subprocess.run")
    def _mock_install(self, manager, viz_id, package, version, mock_run):
        """Helper that mocks npm and performs an install."""

        def side_effect(cmd, **kwargs):
            parts = package.split("/") if package.startswith("@") else [package]
            pkg_path = os.path.join(kwargs["cwd"], "node_modules", *parts)
            os.makedirs(pkg_path, exist_ok=True)
            with open(os.path.join(pkg_path, "package.json"), "w") as f:
                json.dump({"name": package, "version": version}, f)
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect
        return manager.install_npm_package(package, version, manager.get_package_path(viz_id))

    def test_install_then_uninstall(self, manager):
        self._mock_install(manager, "my_viz", "@galaxyproject/my-viz", "1.0.0")
        manager.add_package_to_config("my_viz", "@galaxyproject/my-viz", "1.0.0")

        assert manager.is_package_installed("my_viz")
        assert manager.get_package_info("my_viz") is not None

        manager.remove_package_from_config("my_viz")
        manager.cleanup_package_files("my_viz")

        assert not manager.is_package_installed("my_viz")
        assert manager.get_package_info("my_viz") is None

    def test_install_then_uninstall_then_reinstall(self, manager):
        self._mock_install(manager, "my_viz", "@galaxyproject/my-viz", "1.0.0")
        manager.add_package_to_config("my_viz", "@galaxyproject/my-viz", "1.0.0")

        manager.remove_package_from_config("my_viz")
        manager.cleanup_package_files("my_viz")
        assert not manager.is_package_installed("my_viz")

        # Reinstall
        self._mock_install(manager, "my_viz", "@galaxyproject/my-viz", "1.0.0")
        manager.add_package_to_config("my_viz", "@galaxyproject/my-viz", "1.0.0")
        assert manager.is_package_installed("my_viz")

    def test_install_then_upgrade(self, manager):
        self._mock_install(manager, "my_viz", "@galaxyproject/my-viz", "1.0.0")
        manager.add_package_to_config("my_viz", "@galaxyproject/my-viz", "1.0.0")

        assert manager.load_config()["my_viz"]["version"] == "1.0.0"

        # Upgrade by installing new version over old
        manager.cleanup_package_files("my_viz")
        self._mock_install(manager, "my_viz", "@galaxyproject/my-viz", "2.0.0")
        manager.add_package_to_config("my_viz", "@galaxyproject/my-viz", "2.0.0")

        assert manager.load_config()["my_viz"]["version"] == "2.0.0"
        metadata = manager.get_package_metadata("my_viz")
        assert metadata["version"] == "2.0.0"

    def test_install_then_stage_then_verify(self, manager):
        """Full flow: install from npm, then stage so Galaxy can serve it."""
        self._mock_install(manager, "my_viz", "@galaxyproject/my-viz", "1.0.0")
        manager.add_package_to_config("my_viz", "@galaxyproject/my-viz", "1.0.0")
        static_dir = os.path.join(manager.get_package_path("my_viz"), "static")
        os.makedirs(static_dir, exist_ok=True)
        with open(os.path.join(static_dir, "my_viz.xml"), "w") as f:
            f.write("<visualization name='my_viz' />")
        with open(os.path.join(static_dir, "index.html"), "w") as f:
            f.write("<html>viz content</html>")

        result = manager.stage_visualization("my_viz")
        assert result["visualization_id"] == "my_viz"

        # Verify the static content is now in the serving directory
        staged_dir = os.path.join(manager.app.config.root, "static", "plugins", "visualizations")
        staged_file = os.path.join(staged_dir, "my_viz", "static", "index.html")
        assert os.path.exists(staged_file)
        with open(staged_file) as f:
            assert "viz content" in f.read()


# --- Staging (migration from old install mechanisms) ---


class TestStaging:
    def test_stage_all_visualizations(self, manager):
        _create_viz_static(manager, "circster")
        _create_viz_static(manager, "trackster")

        result = manager.stage_all_visualizations()
        assert result["staged_count"] == 2
        assert len(result["staged_visualizations"]) == 2

        static_dir = os.path.join(manager.app.config.root, "static", "plugins", "visualizations")
        assert os.path.exists(os.path.join(static_dir, "circster", "static", "index.html"))
        assert os.path.exists(os.path.join(static_dir, "trackster", "static", "index.html"))

    def test_stage_runtime_visualization(self, manager):
        _create_runtime_viz_package(manager, "runtime_viz", content="<html>runtime</html>")

        result = manager.stage_visualization("runtime_viz")
        assert result["visualization_id"] == "runtime_viz"
        assert result["source_path"] == manager.get_package_path("runtime_viz")
        assert result["target_path"] == manager.get_staged_path("runtime_viz")
        assert os.path.exists(os.path.join(manager.get_staged_path("runtime_viz"), "static", "runtime_viz.xml"))

    def test_stage_single_visualization(self, manager):
        _create_viz_static(manager, "circster", content="<html>circster</html>")

        result = manager.stage_visualization("circster")
        assert result["visualization_id"] == "circster"
        assert result["size"] > 0

    def test_stage_nested_visualization(self, manager):
        """Nested visualizations like jqplot/jqplot_bar have a two-level directory structure."""
        nested_dir = os.path.join(
            manager.app.config.root,
            "config",
            "plugins",
            "visualizations",
            "jqplot",
            "jqplot_bar",
            "static",
        )
        os.makedirs(nested_dir, exist_ok=True)
        with open(os.path.join(nested_dir, "index.html"), "w") as f:
            f.write("<html>jqplot bar</html>")

        result = manager.stage_visualization("jqplot/jqplot_bar")
        assert result["visualization_id"] == "jqplot/jqplot_bar"

        static_dir = os.path.join(manager.app.config.root, "static", "plugins", "visualizations")
        assert os.path.exists(os.path.join(static_dir, "jqplot", "jqplot_bar", "static", "index.html"))

    def test_stage_nonexistent_raises(self, manager):
        with pytest.raises(exceptions.ObjectNotFound):
            manager.stage_visualization("nonexistent")

    def test_clean_staged_assets(self, manager):
        _create_viz_static(manager, "circster")
        manager.stage_all_visualizations()

        result = manager.clean_staged_assets()
        assert result["cleaned_count"] > 0

        static_dir = os.path.join(manager.app.config.root, "static", "plugins", "visualizations")
        assert os.path.exists(static_dir)
        assert len(os.listdir(static_dir)) == 0

    def test_staging_status(self, manager):
        _create_viz_static(manager, "circster")
        manager.stage_all_visualizations()

        status = manager.get_staging_status()
        assert status["staged_count"] >= 1
        assert status["total_size"] > 0
        names = [v["name"] for v in status["staged_visualizations"]]
        assert "circster" in names

    def test_staging_status_empty(self, manager):
        status = manager.get_staging_status()
        assert status["staged_count"] == 0
        assert status["total_size"] == 0

    def test_stage_all_discovers_existing_viz_plugins(self, manager):
        """Simulates the migration scenario: existing visualizations in config/plugins
        are discovered and staged to static/plugins on startup."""
        # These represent pre-existing visualizations from the old build system
        for viz_name in ["circster", "trackster", "sweepster", "phyloviz"]:
            _create_viz_static(manager, viz_name, f"<html>{viz_name}</html>")

        result = manager.stage_all_visualizations()
        assert result["staged_count"] == 4
        assert result["errors"] == []

        # All should be servable now
        static_dir = os.path.join(manager.app.config.root, "static", "plugins", "visualizations")
        for viz_name in ["circster", "trackster", "sweepster", "phyloviz"]:
            assert os.path.exists(os.path.join(static_dir, viz_name, "static", "index.html"))

    def test_stage_all_includes_runtime_and_legacy_visualizations(self, manager):
        _create_runtime_viz_package(manager, "runtime_viz", content="<html>runtime</html>")
        _create_viz_static(manager, "legacy_viz", "<html>legacy</html>")

        result = manager.stage_all_visualizations()

        assert result["staged_count"] == 2
        assert set(result["staged_visualizations"]) == {"runtime_viz", "legacy_viz"}
        assert os.path.exists(os.path.join(manager.get_staged_path("runtime_viz"), "static", "index.html"))
        assert os.path.exists(os.path.join(manager.get_staged_path("legacy_viz"), "static", "index.html"))


# --- npm registry query ---


class TestNpmRegistryQuery:
    @patch("galaxy.managers.visualization_admin.requests.get")
    def test_filters_by_visualization_keyword(self, mock_get, manager):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "objects": [
                {
                    "package": {
                        "name": "@galaxyproject/test-viz",
                        "description": "A test visualization",
                        "version": "1.0.0",
                        "keywords": ["visualization", "galaxy-visualization"],
                        "author": {},
                        "maintainers": [],
                        "links": {},
                        "date": "2025-01-01",
                    },
                    "score": {},
                },
                {
                    "package": {
                        "name": "@galaxyproject/not-a-viz",
                        "description": "Some other package",
                        "version": "2.0.0",
                        "keywords": ["tool"],
                    },
                    "score": {},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        results = manager.query_npm_registry()
        assert len(results) == 1
        assert results[0]["name"] == "@galaxyproject/test-viz"

    @patch("galaxy.managers.visualization_admin.requests.get")
    def test_search_includes_term(self, mock_get, manager):
        mock_response = MagicMock()
        mock_response.json.return_value = {"objects": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        manager.query_npm_registry("circster")
        call_args = mock_get.call_args
        assert "circster" in call_args[1]["params"]["text"]

    @patch("galaxy.managers.visualization_admin.requests.get")
    def test_get_package_versions(self, mock_get, manager):
        mock_response = MagicMock()
        mock_response.json.return_value = {"versions": {"1.0.0": {}, "2.0.0": {}, "1.1.0": {}}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        versions = manager.get_package_versions("@galaxyproject/circster")
        assert len(versions) == 3
        assert "2.0.0" in versions


# --- Misc ---


class TestDirectorySize:
    def test_empty_directory(self, manager):
        pkg_dir = manager.get_package_path("test_pkg")
        os.makedirs(pkg_dir)
        assert manager.get_directory_size(pkg_dir) == 0

    def test_directory_with_files(self, manager):
        pkg_dir = manager.get_package_path("test_pkg")
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, "file.txt"), "w") as f:
            f.write("hello world")
        assert manager.get_directory_size(pkg_dir) > 0


class TestCleanupPackageFiles:
    def test_cleanup_existing(self, manager):
        pkg_dir = manager.get_package_path("circster")
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, "file.txt"), "w") as f:
            f.write("data")
        staged_dir = manager.get_staged_path("circster")
        os.makedirs(staged_dir)
        with open(os.path.join(staged_dir, "staged.txt"), "w") as f:
            f.write("served")
        manager.cleanup_package_files("circster")
        assert not os.path.exists(pkg_dir)
        assert not os.path.exists(staged_dir)

    def test_cleanup_nonexistent_is_noop(self, manager):
        manager.cleanup_package_files("nonexistent")


class TestBackupRestore:
    def test_backup_and_restore(self, manager):
        original = {
            "circster": {
                "package": "@galaxyproject/circster",
                "version": "1.0.0",
                "enabled": True,
            }
        }
        manager.save_config(original)

        backup_path = manager.backup_config()
        assert backup_path is not None

        manager.save_config({"different": {"package": "other", "version": "2.0.0", "enabled": False}})
        assert manager.load_config() != original

        manager.restore_config(backup_path)
        assert manager.load_config() == original

    def test_backup_no_config(self, manager):
        if os.path.exists(manager.config_path):
            os.remove(manager.config_path)
        assert manager.backup_config() is None
