import json
import os
import shutil
from unittest.mock import MagicMock, patch

import pytest

from galaxy.webapps.galaxy.services.admin_visualizations import AdminVisualizationsService
from galaxy.managers.visualization_admin import VisualizationPackageManager


def _write_package(package_dir: str, package_name: str, version: str) -> None:
    shutil.rmtree(package_dir, ignore_errors=True)
    static_dir = os.path.join(package_dir, "static")
    os.makedirs(static_dir, exist_ok=True)
    with open(os.path.join(package_dir, "package.json"), "w") as f:
        json.dump({"name": package_name, "version": version}, f)
    plugin_name = os.path.basename(package_dir)
    with open(os.path.join(static_dir, f"{plugin_name}.xml"), "w") as f:
        f.write(f"<visualization name='{plugin_name}' />")
    with open(os.path.join(static_dir, "index.html"), "w") as f:
        f.write(version)


@pytest.fixture()
def service(tmp_path):
    app = MagicMock()
    app.config.root = str(tmp_path)
    manager = VisualizationPackageManager(app)
    service = AdminVisualizationsService(security=MagicMock(), app=app, package_manager=manager)
    return service, manager


def test_update_package_restores_previous_version_on_swap_failure(service):
    service, manager = service
    viz_id = "circster"
    package_name = "@galaxyproject/circster"
    target_dir = manager.get_package_path(viz_id)
    _write_package(target_dir, package_name, "1.0.0")
    manager.add_package_to_config(viz_id, package_name, "1.0.0", enabled=True)

    def fake_install(package: str, version: str, destination: str):
        _write_package(destination, package, version)
        return {"package": package, "version": version, "size": 1}

    real_move = shutil.move

    def flaky_move(src: str, dst: str, *args, **kwargs):
        if src != target_dir and dst == target_dir:
            raise OSError("swap failed")
        return real_move(src, dst, *args, **kwargs)

    with patch.object(manager, "install_npm_package", side_effect=fake_install):
        with patch("galaxy.webapps.galaxy.services.admin_visualizations.shutil.move", side_effect=flaky_move):
            with pytest.raises(OSError, match="swap failed"):
                service.update_package(MagicMock(), viz_id, "2.0.0")

    with open(os.path.join(target_dir, "package.json")) as f:
        metadata = json.load(f)

    assert metadata["version"] == "1.0.0"
    assert manager.load_config()[viz_id]["version"] == "1.0.0"
