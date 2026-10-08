import json
import os
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from galaxy import exceptions
from galaxy.managers.visualization_admin import VisualizationPackageManager
from galaxy.webapps.galaxy.services.admin_visualizations import AdminVisualizationsService


def _fake_npm_install(package_spec: str, prefix: str) -> None:
    package, version = package_spec.rsplit("@", 1)
    pkg_path = os.path.join(prefix, "node_modules", *package.split("/"))
    os.makedirs(os.path.join(pkg_path, "static"), exist_ok=True)
    with open(os.path.join(pkg_path, "package.json"), "w") as f:
        json.dump({"name": package, "version": version}, f)
    plugin_name = package.split("/")[-1]
    with open(os.path.join(pkg_path, "static", f"{plugin_name}.xml"), "w") as f:
        f.write(f"<visualization name='{plugin_name}' />")


@pytest.fixture()
def manager(tmp_path, monkeypatch):
    config = MagicMock()
    config.root = str(tmp_path / "galaxy")
    config.visualization_packages_config_file = str(tmp_path / "managed" / "visualization_packages.yml")
    config.visualization_packages_dir = str(tmp_path / "managed" / "visualization_packages")
    manager = VisualizationPackageManager(config)
    monkeypatch.setattr(manager, "_run_npm_install", _fake_npm_install)
    return manager


@pytest.fixture()
def app():
    return MagicMock()


@pytest.fixture()
def service(manager, app):
    return AdminVisualizationsService(security=MagicMock(), app=app, package_manager=manager)


def test_install_then_show(service):
    installed = service.install_package(MagicMock(), "circster", "@galaxyproject/circster", "1.0.0")
    assert installed.installed is True
    assert installed.size > 0

    shown = service.show(MagicMock(), "circster")
    assert shown.package == "@galaxyproject/circster"
    assert shown.version == "1.0.0"
    assert shown.metadata == {"name": "@galaxyproject/circster", "version": "1.0.0"}


def test_install_invalid_package_is_rejected_before_npm(service, manager):
    with patch.object(manager, "_run_npm_install") as npm:
        with pytest.raises(exceptions.RequestParameterInvalidException):
            service.install_package(MagicMock(), "circster", "../escape", "1.0.0")
    npm.assert_not_called()
    assert manager.get_package_info("circster") is None


def test_update_reports_new_version_and_existing_enabled_flag(service, manager):
    service.install_package(MagicMock(), "circster", "@galaxyproject/circster", "1.0.0")
    service.toggle_package(MagicMock(), "circster", False)

    updated = service.update_package(MagicMock(), "circster", "2.0.0")

    assert updated.package == "@galaxyproject/circster"
    assert updated.version == "2.0.0"
    assert updated.enabled is False
    assert manager.get_package_info("circster")["version"] == "2.0.0"


def test_manager_errors_keep_their_type(service):
    # These used to be rewrapped as InternalServerError by the service
    with pytest.raises(exceptions.ObjectNotFound):
        service.update_package(MagicMock(), "missing", "1.0.0")
    with pytest.raises(exceptions.ObjectNotFound):
        service.stage_visualization(MagicMock(), "missing")


def test_reload_registry_reloads_locally_and_broadcasts(service, app):
    service.reload_registry(MagicMock())
    app.visualizations_registry.reload.assert_called_once_with()
    app.queue_worker.send_control_task.assert_called_once_with("reload_visualizations", noop_self=True)


def _assert_registry_reloaded(app):
    app.visualizations_registry.reload.assert_called_once_with()
    app.queue_worker.send_control_task.assert_called_once_with("reload_visualizations", noop_self=True)


def test_install_reloads_registry(service, app):
    service.install_package(MagicMock(), "circster", "@galaxyproject/circster", "1.0.0")
    _assert_registry_reloaded(app)


def test_update_reloads_registry(service, app):
    service.install_package(MagicMock(), "circster", "@galaxyproject/circster", "1.0.0")
    app.reset_mock()
    service.update_package(MagicMock(), "circster", "2.0.0")
    _assert_registry_reloaded(app)


def test_stage_reloads_registry(service, app):
    service.install_package(MagicMock(), "circster", "@galaxyproject/circster", "1.0.0")
    app.reset_mock()
    service.stage_visualization(MagicMock(), "circster")
    _assert_registry_reloaded(app)


def test_stage_all_reloads_registry(service, app):
    service.stage_all_visualizations(MagicMock())
    _assert_registry_reloaded(app)


def test_uninstall_reloads_registry(service, app):
    service.install_package(MagicMock(), "circster", "@galaxyproject/circster", "1.0.0")
    app.reset_mock()
    service.uninstall_package(MagicMock(), "circster")
    _assert_registry_reloaded(app)


def test_toggle_reloads_registry(service, app):
    service.install_package(MagicMock(), "circster", "@galaxyproject/circster", "1.0.0")
    app.reset_mock()
    service.toggle_package(MagicMock(), "circster", False)
    _assert_registry_reloaded(app)


def test_available_packages_maps_registry_results(service, manager):
    registry_result = [
        {
            "name": "@galaxyproject/circster",
            "description": "Circster",
            "version": "1.2.3",
            "keywords": ["visualization"],
            "author": {},
            "maintainers": [],
            "links": {},
            "date": "2026-01-01",
            "score": {},
        }
    ]
    with patch.object(manager, "query_npm_registry", return_value=registry_result):
        available = service.get_available_packages(MagicMock())
    assert [(pkg.name, pkg.version) for pkg in available.root] == [("@galaxyproject/circster", "1.2.3")]


def test_package_versions_passthrough(service, manager):
    with patch.object(manager, "get_package_versions", return_value=["2.0.0", "1.0.0"]):
        versions = service.get_package_versions(MagicMock(), "@galaxyproject/circster")
    assert versions.package == "@galaxyproject/circster"
    assert versions.versions == ["2.0.0", "1.0.0"]
