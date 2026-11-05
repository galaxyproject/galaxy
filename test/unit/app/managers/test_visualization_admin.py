"""Unit tests for VisualizationPackageManager."""

import json
import os
import shutil
import subprocess
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from galaxy import exceptions
from galaxy.managers.visualization_admin import VisualizationPackageManager


@pytest.fixture()
def manager(tmp_path):
    """Create a VisualizationPackageManager whose managed store lives outside the Galaxy root."""
    config = MagicMock()
    config.root = str(tmp_path / "galaxy")
    config.visualization_packages_config_file = str(tmp_path / "managed" / "visualization_packages.yml")
    config.visualization_packages_dir = str(tmp_path / "managed" / "visualization_packages")
    return VisualizationPackageManager(config)


# --- Input validation ---


class TestVizIdValidation:
    def test_valid_simple_id(self, manager):
        manager.validate_viz_id("circster")

    def test_valid_id_with_hyphens(self, manager):
        manager.validate_viz_id("my-viz-plugin")

    def test_rejects_nested_id(self, manager):
        # runtime packages are flat npm packages; nested ids collide on their last segment in the
        # registry and can't be addressed by the {viz_id} admin routes
        with pytest.raises(exceptions.RequestParameterInvalidException):
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

    def test_failed_save_keeps_the_previous_config(self, manager):
        manager.add_package_to_config("circster", "@galaxyproject/circster", "1.0.0")

        def dump_then_die(data, stream, **kwargs):
            stream.write("circster:\n  pack")
            raise OSError("No space left on device")

        with patch("galaxy.managers.visualization_admin.yaml.safe_dump", side_effect=dump_then_die):
            with pytest.raises(exceptions.InternalServerError):
                manager.add_package_to_config("other", "@galaxyproject/other", "1.0.0")

        # every process re-reads this file on reload and at boot, so it must never be half written
        assert manager.load_config() == {
            "circster": {"package": "@galaxyproject/circster", "version": "1.0.0", "enabled": True}
        }
        assert os.listdir(os.path.dirname(manager.config_path)) == ["visualization_packages.yml"]


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
        with pytest.raises(exceptions.RequestParameterInvalidException, match="package.json"):
            manager.validate_package_structure(pkg_dir)

    def test_missing_required_field(self, manager):
        pkg_dir = manager.get_package_path("test_pkg")
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, "package.json"), "w") as f:
            json.dump({"name": "test"}, f)
        with pytest.raises(exceptions.RequestParameterInvalidException, match="version"):
            manager.validate_package_structure(pkg_dir)


# --- npm install (mocked subprocess) ---


def _fake_npm_install(package_spec, prefix, with_static_config=True):
    """Stand-in for ``npm install`` that lays the package out the way npm does."""
    package, version = package_spec.rsplit("@", 1)
    pkg_path = os.path.join(prefix, "node_modules", *package.split("/"))
    os.makedirs(os.path.join(pkg_path, "static"), exist_ok=True)
    with open(os.path.join(pkg_path, "package.json"), "w") as f:
        json.dump({"name": package, "version": version}, f)
    with open(os.path.join(pkg_path, "static", "index.html"), "w") as f:
        f.write(version)
    if with_static_config:
        plugin_name = package.split("/")[-1]
        with open(os.path.join(pkg_path, "static", f"{plugin_name}.xml"), "w") as f:
            f.write(f"<visualization name='{plugin_name}' />")


def _fake_npm_install_without_static_config(package_spec, prefix):
    _fake_npm_install(package_spec, prefix, with_static_config=False)


@pytest.fixture()
def fake_npm(manager, monkeypatch):
    monkeypatch.setattr(manager, "_run_npm_install", _fake_npm_install)
    return manager


class TestNpmInstall:
    def test_install_scoped_package(self, fake_npm):
        """Scoped packages resolve to node_modules/@scope/name."""
        target_dir = fake_npm.get_package_path("circster")
        result = fake_npm.install_npm_package("@galaxyproject/circster", "1.0.0", target_dir)
        assert result["package"] == "@galaxyproject/circster"
        with open(os.path.join(target_dir, "package.json")) as f:
            assert json.load(f)["name"] == "@galaxyproject/circster"

    def test_install_unscoped_package(self, fake_npm):
        target_dir = fake_npm.get_package_path("some_viz")
        result = fake_npm.install_npm_package("some-viz-package", "2.0.0", target_dir)
        assert result["version"] == "2.0.0"
        assert os.path.exists(os.path.join(target_dir, "package.json"))

    def test_install_rejects_package_without_package_json(self, manager, monkeypatch):
        def npm_without_package_json(package_spec, prefix):
            os.makedirs(os.path.join(prefix, "node_modules", "@galaxyproject", "broken"))

        monkeypatch.setattr(manager, "_run_npm_install", npm_without_package_json)
        with pytest.raises(exceptions.RequestParameterInvalidException, match="package.json"):
            manager.install_npm_package("@galaxyproject/broken", "1.0.0", manager.get_package_path("broken"))

    @patch("galaxy.managers.visualization_admin.subprocess.run")
    def test_npm_cache_stays_inside_the_install_prefix(self, mock_run, manager):
        # the Galaxy user's home may not be writable on a locked-down web host
        mock_run.return_value = MagicMock(returncode=0)
        manager._run_npm_install("@galaxyproject/circster@1.0.0", "/tmp/prefix")
        cmd = mock_run.call_args[0][0]
        assert cmd[cmd.index("--cache") + 1].startswith("/tmp/prefix")

    @patch("galaxy.managers.visualization_admin.subprocess.run")
    def test_npm_never_runs_package_scripts(self, mock_run, manager):
        # visualization packages ship prebuilt assets; lifecycle scripts would run as the Galaxy user
        mock_run.return_value = MagicMock(returncode=0)
        manager._run_npm_install("@galaxyproject/circster@1.0.0", "/tmp/prefix")
        assert "--ignore-scripts" in mock_run.call_args[0][0]

    @patch("galaxy.managers.visualization_admin.subprocess.run")
    def test_install_npm_failure(self, mock_run, manager):
        mock_run.return_value = MagicMock(returncode=1, stderr="npm ERR! 404 Not Found")
        target_dir = manager.get_package_path("bad_pkg")
        with pytest.raises(exceptions.InternalServerError, match="installation failed"):
            manager.install_npm_package("@galaxyproject/bad-pkg", "9.9.9", target_dir)

    @patch("galaxy.managers.visualization_admin.subprocess.run")
    def test_missing_npm_says_so(self, mock_run, manager):
        mock_run.side_effect = FileNotFoundError(2, "No such file or directory", "npm")
        with pytest.raises(exceptions.InternalServerError, match="npm executable"):
            manager._run_npm_install("@galaxyproject/circster@1.0.0", "/tmp/prefix")

    @patch("galaxy.managers.visualization_admin.subprocess.run")
    def test_install_timeout(self, mock_run, manager):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="npm", timeout=300)
        target_dir = manager.get_package_path("slow_pkg")
        with pytest.raises(exceptions.InternalServerError, match="timed out"):
            manager.install_npm_package("@galaxyproject/slow", "1.0.0", target_dir)


# --- Install/update/uninstall lifecycle ---


def _installed_version(manager, viz_id):
    with open(os.path.join(manager.get_package_path(viz_id), "package.json")) as f:
        return json.load(f)["version"]


class TestInstallLifecycle:
    def test_install_then_uninstall(self, fake_npm):
        fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")
        assert fake_npm.is_package_installed("my_viz")
        assert fake_npm.get_package_info("my_viz") == {
            "package": "@galaxyproject/my_viz",
            "version": "1.0.0",
            "enabled": True,
        }

        fake_npm.uninstall_package("my_viz")
        assert not fake_npm.is_package_installed("my_viz")
        assert fake_npm.get_package_info("my_viz") is None

    def test_install_twice_conflicts(self, fake_npm):
        fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")
        with pytest.raises(exceptions.Conflict):
            fake_npm.install_package("@galaxyproject/my_viz", "2.0.0")
        assert _installed_version(fake_npm, "my_viz") == "1.0.0"

    def test_install_then_uninstall_then_reinstall(self, fake_npm):
        fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")
        fake_npm.uninstall_package("my_viz")
        fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")
        assert fake_npm.is_package_installed("my_viz")

    def test_uninstall_unknown_raises(self, manager):
        with pytest.raises(exceptions.ObjectNotFound):
            manager.uninstall_package("never_installed")

    def test_uninstall_removes_a_store_directory_with_no_config_entry(self, fake_npm):
        fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")
        fake_npm.remove_package_from_config("my_viz")
        fake_npm.uninstall_package("my_viz")
        assert not fake_npm.is_package_installed("my_viz")

    def test_uninstall_keeps_config_entry_when_file_removal_fails(self, fake_npm):
        fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")
        with patch("galaxy.managers.visualization_admin.shutil.rmtree", side_effect=OSError("busy")):
            with pytest.raises(exceptions.InternalServerError):
                fake_npm.uninstall_package("my_viz")
        # still listed, so the admin can retry the uninstall
        assert fake_npm.get_package_info("my_viz") is not None

    def test_update_swaps_version_and_keeps_enabled_flag(self, fake_npm):
        fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")
        fake_npm.toggle_package_enabled("my_viz", False)

        result = fake_npm.update_package("my_viz", "2.0.0")

        assert result["enabled"] is False
        assert _installed_version(fake_npm, "my_viz") == "2.0.0"
        assert fake_npm.get_package_info("my_viz") == {
            "package": "@galaxyproject/my_viz",
            "version": "2.0.0",
            "enabled": False,
        }

    def test_update_keeps_old_version_when_install_fails(self, fake_npm, monkeypatch):
        fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")

        def failing_npm(package_spec, prefix):
            raise exceptions.InternalServerError("Package installation failed: boom")

        monkeypatch.setattr(fake_npm, "_run_npm_install", failing_npm)
        with pytest.raises(exceptions.InternalServerError):
            fake_npm.update_package("my_viz", "2.0.0")

        assert _installed_version(fake_npm, "my_viz") == "1.0.0"
        assert fake_npm.get_package_info("my_viz")["version"] == "1.0.0"

    def test_update_keeps_old_version_when_swap_fails(self, fake_npm):
        fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")
        target_dir = fake_npm.get_package_path("my_viz")
        real_move = shutil.move

        def flaky_move(src, dst, *args, **kwargs):
            if src != target_dir and dst == target_dir and not os.path.exists(target_dir):
                if "_backup" not in src:
                    raise OSError("swap failed")
            return real_move(src, dst, *args, **kwargs)

        with patch("galaxy.managers.visualization_admin.shutil.move", side_effect=flaky_move):
            with pytest.raises(OSError, match="swap failed"):
                fake_npm.update_package("my_viz", "2.0.0")

        assert _installed_version(fake_npm, "my_viz") == "1.0.0"
        assert fake_npm.get_package_info("my_viz")["version"] == "1.0.0"

    def test_update_restores_old_version_when_swap_fails_partway(self, fake_npm):
        # a cross-filesystem move is copy-then-delete, so a failure can leave a partial target behind
        fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")
        target_dir = fake_npm.get_package_path("my_viz")
        real_move = shutil.move

        def partial_move(src, dst, *args, **kwargs):
            if dst == target_dir and "_backup" not in src:
                os.makedirs(os.path.join(target_dir, "static"))
                raise OSError("No space left on device")
            return real_move(src, dst, *args, **kwargs)

        with patch("galaxy.managers.visualization_admin.shutil.move", side_effect=partial_move):
            with pytest.raises(OSError):
                fake_npm.update_package("my_viz", "2.0.0")

        assert _installed_version(fake_npm, "my_viz") == "1.0.0"
        assert sorted(os.listdir(target_dir)) == ["package.json", "static"]

    def test_update_unknown_raises(self, manager):
        with pytest.raises(exceptions.ObjectNotFound):
            manager.update_package("never_installed", "1.0.0")

    def test_install_rejects_package_without_static_config(self, manager, monkeypatch):
        monkeypatch.setattr(manager, "_run_npm_install", _fake_npm_install_without_static_config)
        with pytest.raises(exceptions.RequestParameterInvalidException, match="my_viz.xml"):
            manager.install_package("@galaxyproject/my_viz", "1.0.0")
        assert not manager.is_package_installed("my_viz")
        assert manager.get_package_info("my_viz") is None

    def test_failed_validation_leaves_nothing_behind(self, manager, monkeypatch):
        def npm_with_bad_package_json(package_spec, prefix):
            _fake_npm_install(package_spec, prefix)
            pkg_json = os.path.join(prefix, "node_modules", "@galaxyproject", "my_viz", "package.json")
            with open(pkg_json, "w") as f:
                f.write("{not json")

        monkeypatch.setattr(manager, "_run_npm_install", npm_with_bad_package_json)
        with pytest.raises(exceptions.RequestParameterInvalidException):
            manager.install_package("@galaxyproject/my_viz", "1.0.0")
        assert not manager.is_package_installed("my_viz")

        # and the admin can simply try again
        monkeypatch.setattr(manager, "_run_npm_install", _fake_npm_install)
        manager.install_package("@galaxyproject/my_viz", "1.0.0")
        assert manager.is_package_installed("my_viz")

    def test_failed_config_write_leaves_nothing_behind(self, fake_npm, monkeypatch):
        def failing_save(config):
            raise exceptions.InternalServerError("Failed to save configuration: disk full")

        monkeypatch.setattr(fake_npm, "save_config", failing_save)
        with pytest.raises(exceptions.InternalServerError):
            fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")
        assert not fake_npm.is_package_installed("my_viz")

    def test_install_copies_symlinks_as_links_not_their_targets(self, manager, monkeypatch, tmp_path):
        secret = tmp_path / "secret.txt"
        secret.write_text("galaxy.yml contents")

        def npm_with_symlink(package_spec, prefix):
            _fake_npm_install(package_spec, prefix)
            static = os.path.join(prefix, "node_modules", "@galaxyproject", "my_viz", "static")
            os.symlink(secret, os.path.join(static, "leak.txt"))

        monkeypatch.setattr(manager, "_run_npm_install", npm_with_symlink)
        manager.install_package("@galaxyproject/my_viz", "1.0.0")
        # a dereferenced copy would be a regular file inside static/ that the public route happily serves
        assert os.path.islink(os.path.join(manager.get_package_path("my_viz"), "static", "leak.txt"))

    def test_update_rejects_version_without_static_config(self, fake_npm, monkeypatch):
        fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")
        monkeypatch.setattr(fake_npm, "_run_npm_install", _fake_npm_install_without_static_config)
        with pytest.raises(exceptions.RequestParameterInvalidException, match="my_viz.xml"):
            fake_npm.update_package("my_viz", "2.0.0")
        assert _installed_version(fake_npm, "my_viz") == "1.0.0"
        assert fake_npm.get_package_info("my_viz")["version"] == "1.0.0"


# --- Store creation and enabled packages ---


class TestVisualizationIdFromPackage:
    def test_scoped_package_installs_under_its_unscoped_name(self, fake_npm):
        result = fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")
        assert result["id"] == "my_viz"
        assert fake_npm.get_package_info("my_viz")["package"] == "@galaxyproject/my_viz"
        assert fake_npm.is_package_installed("my_viz")

    def test_unscoped_package_installs_under_its_name(self, fake_npm):
        assert fake_npm.install_package("my-viz", "1.0.0")["id"] == "my-viz"

    def test_name_that_cant_be_an_id_is_rejected_before_npm(self, manager):
        with patch.object(manager, "_run_npm_install") as npm:
            with pytest.raises(exceptions.RequestParameterInvalidException):
                manager.install_package("@galaxyproject/my.viz", "1.0.0")
        npm.assert_not_called()
        assert manager.load_config() == {}


class TestStoreCreation:
    """Startup can't depend on managed_config_dir being writable; only installing a package can."""

    def _fresh_manager(self, tmp_path):
        config = MagicMock()
        config.root = str(tmp_path / "galaxy")
        config.visualization_packages_config_file = str(tmp_path / "fresh" / "visualization_packages.yml")
        config.visualization_packages_dir = str(tmp_path / "fresh" / "visualization_packages")
        return VisualizationPackageManager(config)

    def test_constructing_the_manager_writes_nothing(self, tmp_path):
        manager = self._fresh_manager(tmp_path)
        assert manager.get_enabled_packages() == {}
        assert manager.load_config() == {}
        assert not os.path.exists(tmp_path / "fresh")

    def test_first_install_creates_the_store(self, tmp_path, monkeypatch):
        manager = self._fresh_manager(tmp_path)
        monkeypatch.setattr(manager, "_run_npm_install", _fake_npm_install)
        manager.install_package("@galaxyproject/my_viz", "1.0.0")
        assert manager.get_enabled_packages() == {"my_viz": manager.get_package_path("my_viz")}


class TestEnabledPackages:
    def test_reads_the_config_once(self, fake_npm, monkeypatch):
        fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")
        fake_npm.install_package("@galaxyproject/other_viz", "1.0.0")
        load_config = MagicMock(wraps=fake_npm.load_config)
        monkeypatch.setattr(fake_npm, "load_config", load_config)
        fake_npm.get_enabled_packages()
        assert load_config.call_count == 1

    def test_lists_enabled_installed_packages(self, fake_npm):
        fake_npm.install_package("@galaxyproject/my_viz", "1.0.0")
        fake_npm.install_package("@galaxyproject/other_viz", "1.0.0")
        fake_npm.toggle_package_enabled("other_viz", False)
        fake_npm.add_package_to_config("ghost_viz", "@galaxyproject/ghost_viz", "1.0.0")

        assert fake_npm.get_enabled_packages() == {"my_viz": fake_npm.get_package_path("my_viz")}


class TestNpmRegistryQuery:
    @patch("galaxy.managers.visualization_admin.requests.get")
    def test_lists_scoped_packages_regardless_of_keywords(self, mock_get, manager):
        # most real visualization packages carry no keywords at all; the static XML check at
        # install time is what decides whether a package is actually a visualization
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
                        "name": "@galaxyproject/untagged-viz",
                        "description": "A visualization with no keywords",
                        "version": "2.0.0",
                    },
                    "score": {},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        results = manager.query_npm_registry()
        assert [result["name"] for result in results] == ["@galaxyproject/test-viz", "@galaxyproject/untagged-viz"]

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
    def test_search_uses_v1_endpoint_scoped_to_galaxyproject(self, mock_get, manager):
        # the legacy /-/search endpoint now 405s, and v1 search ignores a scope: qualifier
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "objects": [
                {"package": {"name": "@galaxyproject/test-viz", "keywords": ["visualization"]}, "score": {}},
                {"package": {"name": "someone-else-viz", "keywords": ["visualization"]}, "score": {}},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        results = manager.query_npm_registry()
        assert mock_get.call_args[0][0] == "https://registry.npmjs.org/-/v1/search"
        assert mock_get.call_args[1]["params"]["text"].startswith("@galaxyproject")
        assert [result["name"] for result in results] == ["@galaxyproject/test-viz"]

    @patch("galaxy.managers.visualization_admin.requests.get")
    def test_get_package_versions(self, mock_get, manager):
        mock_response = MagicMock()
        mock_response.json.return_value = {"versions": {"1.0.0": {}, "2.0.0": {}, "1.1.0": {}}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        versions = manager.get_package_versions("@galaxyproject/circster")
        assert len(versions) == 3
        assert "2.0.0" in versions

    @patch("galaxy.managers.visualization_admin.requests.get")
    def test_get_package_versions_newest_first_by_version_not_string(self, mock_get, manager):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "versions": {v: {} for v in ["0.0.1", "0.0.9", "0.0.10", "0.0.11", "0.1.0-beta.1", "0.1.0"]}
        }
        mock_get.return_value = mock_response

        versions = manager.get_package_versions("@galaxyproject/tabulator")
        assert versions == ["0.1.0", "0.1.0-beta.1", "0.0.11", "0.0.10", "0.0.9", "0.0.1"]

    @patch("galaxy.managers.visualization_admin.requests.get")
    def test_get_package_versions_rejects_invalid_names(self, mock_get, manager):
        with pytest.raises(exceptions.RequestParameterInvalidException):
            manager.get_package_versions("../-/whoami")
        mock_get.assert_not_called()


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
        manager.cleanup_package_files("circster")
        assert not os.path.exists(pkg_dir)

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
