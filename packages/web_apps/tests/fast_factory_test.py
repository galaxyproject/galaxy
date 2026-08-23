from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from galaxy.util import in_packages
from galaxy.webapps.galaxy import fast_factory


@pytest.mark.skipif(not in_packages(), reason="requires package-installed Galaxy")
def test_build_galaxy_web_app_starts_without_a_checkout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    paths = {name: tmp_path / name for name in ("config", "data", "files", "jobs", "new")}
    for path in paths.values():
        path.mkdir()

    web_app = fast_factory.build_galaxy_web_app(
        {
            "config_dir": str(paths["config"]),
            "managed_config_dir": str(paths["config"]),
            "data_dir": str(paths["data"]),
            "database_connection": f"sqlite:///{paths['data'] / 'galaxy.sqlite'}?isolation_level=IMMEDIATE",
            "database_auto_migrate": True,
            "file_path": str(paths["files"]),
            "job_working_directory": str(paths["jobs"]),
            "new_file_path": str(paths["new"]),
            "bootstrap_admin_api_key": "package-test-key",
            "id_secret": "package-test-secret",
            "use_heartbeat": False,
        },
        register_shutdown_at_exit=False,
    )

    try:
        tool_path = Path(web_app.galaxy_app.config.tool_path)
        assert tool_path.name == "bundled"
        assert "site-packages" in tool_path.parts
        with TestClient(web_app.asgi_app) as client:
            response = client.get("/api/version")
        assert response.status_code == 200
        assert response.json()["version_major"]
    finally:
        web_app.galaxy_app.shutdown()
