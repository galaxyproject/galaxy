import json
import os
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from galaxy.jobs import MinimalJobWrapper
from galaxy.model import Job
from galaxy.util import in_packages
from galaxy.webapps.galaxy import fast_factory


def wait_for_job(client, job_id, headers):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        response = client.get(f"/api/jobs/{job_id}", headers=headers)
        assert response.status_code == 200
        state = response.json()["state"]
        if state in {"ok", "error", "deleted"}:
            return state
        time.sleep(0.5)
    pytest.fail(f"job {job_id} did not finish within 90 seconds")


@pytest.mark.skipif(not in_packages(), reason="requires package-installed Galaxy")
def test_build_galaxy_web_app_starts_without_a_checkout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    galaxy_bin = str(Path(sys.executable).parent)
    monkeypatch.setenv(
        "PATH", os.pathsep.join(path for path in os.environ["PATH"].split(os.pathsep) if path != galaxy_bin)
    )
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
        job_wrapper = MinimalJobWrapper(Job(), web_app.galaxy_app)
        assert job_wrapper.galaxy_lib_dir is None
        assert job_wrapper.galaxy_virtual_env == sys.prefix

        tool_path = Path(web_app.galaxy_app.config.tool_path)
        assert tool_path.name == "bundled"
        assert "site-packages" in tool_path.parts
        with TestClient(web_app.asgi_app) as client:
            response = client.get("/api/version")
            assert response.status_code == 200
            assert response.json()["version_major"]

            admin_headers = {"x-api-key": "package-test-key"}
            user_response = client.post(
                "/api/users",
                json={
                    "email": "package-test@example.org",
                    "password": "package-test-password",
                    "username": "package-test",
                },
                headers=admin_headers,
            )
            assert user_response.status_code == 200, user_response.text
            user_id = user_response.json()["id"]
            api_key_response = client.post(f"/api/users/{user_id}/api_key", headers=admin_headers)
            assert api_key_response.status_code == 200, api_key_response.text
            headers = {"x-api-key": api_key_response.json()}
            history_response = client.post("/api/histories", json={"name": "package smoke test"}, headers=headers)
            assert history_response.status_code == 200, history_response.text
            history_id = history_response.json()["id"]
            upload_response = client.post(
                "/api/tools",
                data={
                    "history_id": history_id,
                    "tool_id": "upload1",
                    "upload_type": "upload_dataset",
                    "inputs": json.dumps(
                        {
                            "dbkey": "?",
                            "file_type": "txt",
                            "files_0|NAME": "hello.txt",
                            "files_0|url_paste": "hello, wheel-installed Galaxy!\n",
                        }
                    ),
                },
                headers=headers,
            )
            assert upload_response.status_code == 200, upload_response.text
            job_id = upload_response.json()["jobs"][0]["id"]
            assert wait_for_job(client, job_id, headers) == "ok"
    finally:
        web_app.galaxy_app.shutdown()
