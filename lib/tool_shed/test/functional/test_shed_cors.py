import requests

from ..base.api import ShedApiTestCase

ORIGIN = "https://vscode.dev"


class TestShedCorsApi(ShedApiTestCase):
    def test_preflight_allows_cross_origin_get(self):
        response = requests.options(
            f"{self.url}/api/repositories",
            headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == ORIGIN

    def test_get_response_reflects_origin(self):
        response = requests.get(f"{self.url}/api/repositories", headers={"Origin": ORIGIN})
        response.raise_for_status()
        assert response.headers.get("access-control-allow-origin") == ORIGIN

    def test_credentials_not_exposed_cross_origin(self):
        # No Access-Control-Allow-Credentials keeps the cookie-authenticated surface
        # unreadable cross-origin: a browser will not expose a credentialed response
        # without that header.
        response = requests.get(f"{self.url}/api/repositories", headers={"Origin": ORIGIN})
        response.raise_for_status()
        assert "access-control-allow-credentials" not in response.headers

    def test_repository_files_allow_cross_origin_reads(self):
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker", end=1)
        metadata = populator.get_metadata(repository, downloadable_only=True)
        revision = next(iter(metadata.root.values())).changeset_revision
        origin = {"Origin": ORIGIN}
        for path in (None, "column_maker/column_maker.xml"):
            response = populator.get_repository_files_raw(
                repository, revision, path=path, headers=origin, anonymous=True
            )
            response.raise_for_status()
            assert response.headers.get("access-control-allow-origin") == ORIGIN
            not_modified = populator.get_repository_files_raw(
                repository,
                revision,
                path=path,
                headers={**origin, "If-None-Match": response.headers["ETag"]},
                anonymous=True,
            )
            assert not_modified.status_code == 304
            assert not_modified.headers.get("access-control-allow-origin") == ORIGIN

        preflight = requests.options(
            f"{self.url}/api/repositories/{repository.id}/revisions/{revision}/files/column_maker/column_maker.xml",
            headers={**origin, "Access-Control-Request-Method": "GET"},
        )
        assert preflight.status_code == 200
        assert preflight.headers.get("access-control-allow-origin") == ORIGIN

    def test_uncovered_endpoint_has_no_cors(self):
        # CORS is opt-in per route; an endpoint not marked allow_cors emits no header.
        response = requests.get(f"{self.url}/api/ga4gh/trs/v2/service-info", headers={"Origin": ORIGIN})
        response.raise_for_status()
        assert "access-control-allow-origin" not in response.headers
