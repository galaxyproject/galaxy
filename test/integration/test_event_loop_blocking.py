"""Integration tests for aiocop blocking-I/O detection.

Spins up a Galaxy server with aiocop enabled and registers test-only debug
endpoints that intentionally perform high-severity blocking I/O from inside
an async handler.  The aiocop audit hook must catch the call and the test
interactor must fail the request via the ``X-Aiocop-Violations`` header.

The debug endpoints are **only** added to the test server — they never
exist in a production Galaxy instance.
"""

import socket

import pytest

from galaxy.webapps.galaxy.fast_app import initialize_fast_app
from galaxy_test.base.api import AIOCOP_ENABLED
from galaxy_test.driver import integration_util


def _init_fast_app_with_debug_routes(wsgi_webapp, gx_app):
    """Wrap the standard FastAPI initializer to add debug blocking routes.

    Routes must be injected before the WSGI catch-all mount (``app.mount("/", ...)``)
    that ``initialize_fast_app`` adds, otherwise Starlette never reaches them.
    We pop the catch-all, register our routes, then re-append it.
    """
    app = initialize_fast_app(wsgi_webapp, gx_app)

    wsgi_catch_all = app.routes.pop()

    @app.get("/api/debug/block")
    async def block_event_loop() -> dict:
        # socket.getaddrinfo is a high-severity blocking call in aiocop's
        # severity table and will trigger the audit hook.
        try:
            socket.getaddrinfo("invalid.local.test.galaxy.example", 80)
        except socket.gaierror:
            pass
        return {"status": "blocked"}

    @app.get("/api/debug/ok")
    async def ok() -> dict:
        return {"status": "ok"}

    app.routes.append(wsgi_catch_all)
    return app


@pytest.mark.skipif(
    not AIOCOP_ENABLED,
    reason="GALAXY_TEST_AIOCOP not set",
)
class TestAiocopBlockingDetection(integration_util.IntegrationTestCase):
    init_fast_app = staticmethod(_init_fast_app_with_debug_routes)

    def test_ok_endpoint_does_not_block(self):
        """A trivial async endpoint must not trigger a high-severity aiocop violation.

        Low-severity events (e.g. ``os.stat`` from Galaxy middleware) may
        still appear in the ``X-Aiocop-Violations`` header; only events at
        ``AIOCOP_FAIL_SEVERITY`` or above fail the request.
        """
        response = self._get("debug/ok")
        self._assert_status_code_is(response, 200)
        assert response.json()["status"] == "ok"
        header = response.headers.get("x-aiocop-violations", "")
        if header:
            fields = dict(p.split("=", 1) for p in header.split(";") if "=" in p)
            assert (
                int(fields.get("severity", "0")) < 50
            ), f"OK endpoint triggered high-severity aiocop violation: {header!r}"

    def test_blocking_endpoint_detected(self):
        """An endpoint that makes a blocking syscall must be caught by aiocop."""
        with pytest.raises(AssertionError, match="aiocop detected high-severity blocking I/O"):
            self._get("debug/block")

    def test_violations_header_present_on_block(self):
        """The X-Aiocop-Violations header must be set when blocking I/O occurs."""
        response = self.galaxy_interactor._get("debug/block")
        header = response.headers.get("x-aiocop-violations", "")
        assert "count=" in header and "severity=" in header, f"Missing aiocop violation summary: {header!r}"
