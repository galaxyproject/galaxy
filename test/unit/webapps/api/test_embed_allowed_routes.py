"""Snapshot of which API routes opt into page-embed-token auth.

Pins the exact (method, path) set carrying ``embed_allowed=True`` (i.e. the
``embed_token_dependency``). The embed token recovers the page owner's *full*
user, so this marked set IS the entire trust boundary -- marking a new route,
especially a listing/enumeration route, silently widens what an exfiltrated
embed token can read. This test forces any change to that set to be deliberate.
"""

from fastapi import FastAPI

from galaxy.webapps.base.api import include_all_package_routers
from galaxy.webapps.galaxy.api import embed_token_dependency

# Every entry MUST be a single-resource, read-only GET/HEAD route. Do NOT add a
# listing/enumeration route -- see embed_token_dependency's docstring.
EXPECTED_EMBED_ALLOWED_ROUTES = {
    ("GET", "/api/pages/{id}"),
    ("GET", "/api/datasets/{history_content_id}/display"),
    ("HEAD", "/api/datasets/{history_content_id}/display"),
    ("GET", "/api/datasets/{history_content_id}/metadata_file"),
    ("HEAD", "/api/datasets/{history_content_id}/metadata_file"),
    ("GET", "/api/datasets/{dataset_id}"),
    ("GET", "/api/dataset_collections/{hdca_id}"),
}


def _embed_allowed_routes():
    app = FastAPI()
    include_all_package_routers(app, "galaxy.webapps.galaxy.api")
    found = set()
    for route in app.routes:
        dependencies = getattr(route, "dependencies", None) or []
        if not any(getattr(d, "dependency", None) is embed_token_dependency for d in dependencies):
            continue
        # Galaxy registers each route with and without a trailing slash; collapse
        # the pair to the one logical route.
        path = route.path.rstrip("/") or "/"
        for method in route.methods or []:
            found.add((method, path))
    return found


def test_embed_allowed_route_allow_list_is_pinned():
    assert _embed_allowed_routes() == EXPECTED_EMBED_ALLOWED_ROUTES
