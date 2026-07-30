"""Verify the TUS routers stay reachable when galaxy_url_prefix is set.

initialize_fast_app mounts the Galaxy app underneath galaxy_url_prefix, so the TUS
routers must be registered without it. Registering them with the prefix made the
creation POST miss the router entirely and fall through to the legacy WSGI upload
hooks endpoint, which answers 200 without a Location header, leaving TUS clients
with no upload URL to PATCH to.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from galaxy.util.bunch import Bunch
from galaxy.webapps.galaxy.fast_app import include_tus

UPLOAD_PATH = "api/upload/resumable_upload"
JOB_FILES_PATH = "api/job_files/resumable_upload"


def _build_app(tmp_path, url_prefix):
    """Mirror how initialize_fast_app wires the app for a given url prefix."""
    config = Bunch(
        galaxy_url_prefix=url_prefix,
        tus_upload_store=str(tmp_path),
        tus_upload_store_job_files=None,
        new_file_path=str(tmp_path),
        maximum_upload_file_size=1024,
    )
    root_path = "" if url_prefix == "/" else url_prefix
    app = FastAPI(root_path=root_path)
    include_tus(app, Bunch(config=config))
    if not root_path:
        return app
    parent_app = FastAPI()
    parent_app.mount(root_path, app=app)
    return parent_app


@pytest.mark.parametrize("url_prefix", ["/", "/galaxypf", "/proxy/google/v1/apps/ns/app/galaxy"])
@pytest.mark.parametrize("tus_path", [UPLOAD_PATH, JOB_FILES_PATH])
def test_tus_creation_returns_prefixed_location(tmp_path, url_prefix, tus_path):
    client = TestClient(_build_app(tmp_path, url_prefix))
    base = "" if url_prefix == "/" else url_prefix

    response = client.post(
        f"{base}/{tus_path}/",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": "11",
            "Host": "galaxy.example.org",
            "X-Forwarded-Proto": "https",
        },
    )

    assert response.status_code == 201
    location = response.headers["location"]
    assert location.startswith(f"https://galaxy.example.org{base}/{tus_path}/")
