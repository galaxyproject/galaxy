"""Unit tests for VisualizationPackageManager."""

import json
import os
import shutil
import tempfile
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest


@pytest.fixture()
def manager():
    """Create a VisualizationPackageManager with a temp directory as root."""
    from galaxy.managers.visualization_admin import VisualizationPackageManager

    tmpdir = tempfile.mkdtemp()
    app = MagicMock()
    app.config.root = tmpdir

    mgr = VisualizationPackageManager(app)
    yield mgr

    shutil.rmtree(tmpdir, ignore_errors=True)


class TestConfigManagement:
    def test_load_config_empty(self, manager):
        config = manager.load_config()
        assert config == {}

    def test_save_and_load_config(self, manager):
        config = {
            "circster": {
                "package": "@galaxyproject/circster",
                "version": "1.0.0",
                "enabled": True,
            }
        }
        manager.save_config(config)
        loaded = manager.load_config()
        assert loaded == config

    def test_add_package_to_config(self, manager):
        manager.add_package_to_config("circster", "@galaxyproject/circster", "1.0.0", enabled=True)
        config = manager.load_config()
        assert "circster" in config
        assert config["circster"]["package"] == "@galaxyproject/circster"
        assert config["circster"]["version"] == "1.0.0"
        assert config["circster"]["enabled"] is True

    def test_remove_package_from_config(self, manager):
        manager.add_package_to_config("circster", "@galaxyproject/circster", "1.0.0")
        manager.remove_package_from_config("circster")
        config = manager.load_config()
        assert "circster" not in config

    def test_remove_nonexistent_package_is_noop(self, manager):
        manager.remove_package_from_config("nonexistent")
        config = manager.load_config()
        assert config == {}

    def test_toggle_package_enabled(self, manager):
        manager.add_package_to_config("circster", "@galaxyproject/circster", "1.0.0", enabled=True)
        manager.toggle_package_enabled("circster", False)
        config = manager.load_config()
        assert config["circster"]["enabled"] is False

    def test_toggle_nonexistent_raises(self, manager):
        from galaxy import exceptions

        with pytest.raises(exceptions.ObjectNotFound):
            manager.toggle_package_enabled("nonexistent", True)


class TestPackageInfo:
    def test_get_package_info_missing(self, manager):
        assert manager.get_package_info("nonexistent") is None

    def test_get_package_info_present(self, manager):
        manager.add_package_to_config("circster", "@galaxyproject/circster", "2.0.0")
        info = manager.get_package_info("circster")
        assert info["package"] == "@galaxyproject/circster"
        assert info["version"] == "2.0.0"

    def test_is_package_installed_false(self, manager):
        assert manager.is_package_installed("circster") is False

    def test_is_package_installed_true(self, manager):
        pkg_dir = manager.get_package_path("circster")
        os.makedirs(pkg_dir)
        assert manager.is_package_installed("circster") is True

    def test_get_package_metadata_no_package_json(self, manager):
        pkg_dir = manager.get_package_path("circster")
        os.makedirs(pkg_dir)
        assert manager.get_package_metadata("circster") == {}

    def test_get_package_metadata_with_package_json(self, manager):
        pkg_dir = manager.get_package_path("circster")
        os.makedirs(pkg_dir)
        metadata = {
            "name": "@galaxyproject/circster",
            "version": "1.0.0",
            "description": "A viz",
        }
        with open(os.path.join(pkg_dir, "package.json"), "w") as f:
            json.dump(metadata, f)
        result = manager.get_package_metadata("circster")
        assert result["name"] == "@galaxyproject/circster"
        assert result["description"] == "A viz"


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
        size = manager.get_directory_size(pkg_dir)
        assert size > 0


class TestPackageValidation:
    def test_valid_package(self, manager):
        pkg_dir = manager.get_package_path("test_pkg")
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, "package.json"), "w") as f:
            json.dump({"name": "test", "version": "1.0.0"}, f)
        assert manager.validate_package_structure(pkg_dir) is True

    def test_missing_package_json(self, manager):
        from galaxy import exceptions

        pkg_dir = manager.get_package_path("test_pkg")
        os.makedirs(pkg_dir)
        with pytest.raises(exceptions.ConfigurationError, match="package.json"):
            manager.validate_package_structure(pkg_dir)

    def test_missing_required_field(self, manager):
        from galaxy import exceptions

        pkg_dir = manager.get_package_path("test_pkg")
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, "package.json"), "w") as f:
            json.dump({"name": "test"}, f)
        with pytest.raises(exceptions.ConfigurationError, match="version"):
            manager.validate_package_structure(pkg_dir)


class TestCleanupPackageFiles:
    def test_cleanup_existing(self, manager):
        pkg_dir = manager.get_package_path("circster")
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, "file.txt"), "w") as f:
            f.write("data")
        manager.cleanup_package_files("circster")
        assert not os.path.exists(pkg_dir)

    def test_cleanup_nonexistent_is_noop(self, manager):
        manager.cleanup_package_files("nonexistent")


class TestNpmRegistryQuery:
    @patch("galaxy.managers.visualization_admin.requests.get")
    def test_query_npm_registry(self, mock_get, manager):
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
                        "author": {},
                        "maintainers": [],
                        "links": {},
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
    def test_query_npm_registry_with_search(self, mock_get, manager):
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
        assert "1.0.0" in versions
        assert "2.0.0" in versions
        assert len(versions) == 3


class TestStaging:
    def _create_viz_static(self, manager, viz_name, content="test"):
        """Helper to create a visualization with static assets in config/plugins."""
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
        return plugins_dir

    def test_stage_all_visualizations(self, manager):
        self._create_viz_static(manager, "circster")
        self._create_viz_static(manager, "trackster")

        result = manager.stage_all_visualizations()
        assert result["staged_count"] == 2
        assert len(result["staged_visualizations"]) == 2

        static_dir = os.path.join(manager.app.config.root, "static", "plugins", "visualizations")
        assert os.path.exists(os.path.join(static_dir, "circster", "static", "index.html"))
        assert os.path.exists(os.path.join(static_dir, "trackster", "static", "index.html"))

    def test_stage_single_visualization(self, manager):
        self._create_viz_static(manager, "circster", content="<html>circster</html>")

        result = manager.stage_visualization("circster")
        assert result["visualization_id"] == "circster"
        assert result["size"] > 0

    def test_stage_nonexistent_raises(self, manager):
        from galaxy import exceptions

        with pytest.raises(exceptions.ObjectNotFound):
            manager.stage_visualization("nonexistent")

    def test_clean_staged_assets(self, manager):
        self._create_viz_static(manager, "circster")
        manager.stage_all_visualizations()

        result = manager.clean_staged_assets()
        assert result["cleaned_count"] > 0

        static_dir = os.path.join(manager.app.config.root, "static", "plugins", "visualizations")
        assert os.path.exists(static_dir)
        assert len(os.listdir(static_dir)) == 0

    def test_get_staging_status(self, manager):
        self._create_viz_static(manager, "circster")
        manager.stage_all_visualizations()

        status = manager.get_staging_status()
        assert status["staged_count"] >= 1
        assert status["total_size"] > 0
        names = [v["name"] for v in status["staged_visualizations"]]
        assert "circster" in names

    def test_get_staging_status_empty(self, manager):
        status = manager.get_staging_status()
        assert status["staged_count"] == 0
        assert status["total_size"] == 0


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
        assert os.path.exists(backup_path)

        manager.save_config({"different": {"package": "other", "version": "2.0.0", "enabled": False}})
        assert manager.load_config() != original

        manager.restore_config(backup_path)
        assert manager.load_config() == original

    def test_backup_no_config(self, manager):
        os.remove(manager.config_path) if os.path.exists(manager.config_path) else None
        result = manager.backup_config()
        assert result is None
