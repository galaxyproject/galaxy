"""Unit tests for XFrameOptionsMiddleware embed framing headers (Phase 1.1)."""

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from galaxy.webapps.galaxy.fast_app import XFrameOptionsMiddleware

EMBED_ORIGINS = "https://orbit.example https://loom.example"


def _client(embed_allowed_origins=None, x_frame_options="SAMEORIGIN"):
    async def endpoint(request):
        return PlainTextResponse("ok")

    app = Starlette(
        routes=[
            Route("/published/page", endpoint),
            Route("/api/whatever", endpoint),
        ]
    )
    app.add_middleware(
        XFrameOptionsMiddleware,
        x_frame_options=x_frame_options,
        embed_allowed_origins=embed_allowed_origins,
    )
    return TestClient(app)


def test_non_embed_request_sets_xframe_no_csp():
    resp = _client(embed_allowed_origins=EMBED_ORIGINS).get("/api/whatever")
    assert resp.headers.get("x-frame-options") == "SAMEORIGIN"
    assert "content-security-policy" not in resp.headers


def test_embed_request_emits_frame_ancestors_csp_no_xframe():
    resp = _client(embed_allowed_origins=EMBED_ORIGINS).get("/published/page?id=abc&embed=true")
    assert "x-frame-options" not in resp.headers
    assert resp.headers.get("content-security-policy") == f"frame-ancestors {EMBED_ORIGINS}"


def test_embed_request_without_configured_origins_omits_csp_and_xframe():
    resp = _client(embed_allowed_origins=None).get("/published/page?id=abc&embed=true")
    assert "x-frame-options" not in resp.headers
    assert "content-security-policy" not in resp.headers
