"""Unit tests for the DB-connection release in :mod:`galaxy.webapps.base.api`.

``GalaxyStreamingResponse`` / ``GalaxyFileResponse`` must return the
request-scoped pooled DB connection(s) the moment streaming begins, so a
long-lived stream (SSE, a slow/large download) does not pin a connection for
its whole lifetime. These tests drive the responses with fake ASGI ``send``
callables and a fake Galaxy app whose scoped registries hold ``FakeSession``
objects, and assert the sessions are closed *before* the first body byte.
"""

from types import SimpleNamespace

from galaxy.webapps.base.api import (
    GalaxyFileResponse,
    GalaxyStreamingResponse,
)

KEY = "test-request-id"


class FakeSession:
    """Request-scoped Session stand-in. ``close`` records the release and
    treats a second close as a contract violation (double-release is a bug)."""

    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        if self.closed:
            raise AssertionError("session closed more than once")
        self.closed = True


def _mapping(registry: dict):
    """A model-mapping stand-in exposing the registry access the helper uses."""
    return SimpleNamespace(
        scoped_registry=SimpleNamespace(registry=registry),
        request_scopefunc=lambda: KEY,
    )


def _install_fake_app(monkeypatch, *, model_registry=None, install_registry=None, app_present=True):
    if not app_present:
        monkeypatch.setattr("galaxy.app.app", None)
        return None
    app = SimpleNamespace(
        model=_mapping(model_registry if model_registry is not None else {}),
        install_model=_mapping(install_registry if install_registry is not None else {}),
    )
    monkeypatch.setattr("galaxy.app.app", app)
    return app


async def _collect(send_messages):
    async def send(message):
        send_messages.append(message)

    return send


async def test_streaming_releases_session_before_first_chunk(monkeypatch):
    session = FakeSession()
    _install_fake_app(monkeypatch, model_registry={KEY: session})
    observed = []

    async def body():
        observed.append(session.closed)  # state captured when the first chunk is produced
        yield b"data"

    response = GalaxyStreamingResponse(body())
    messages: list = []
    await response.stream_response(await _collect(messages))

    assert observed == [True]
    assert session.closed is True


async def test_streaming_releases_both_model_and_install_sessions(monkeypatch):
    model_session = FakeSession()
    install_session = FakeSession()
    _install_fake_app(monkeypatch, model_registry={KEY: model_session}, install_registry={KEY: install_session})

    async def body():
        yield b"x"

    response = GalaxyStreamingResponse(body())
    await response.stream_response(await _collect([]))

    assert model_session.closed is True
    assert install_session.closed is True


async def test_streaming_no_session_does_not_lazy_create(monkeypatch):
    model_registry: dict = {}
    _install_fake_app(monkeypatch, model_registry=model_registry)

    async def body():
        yield b"x"

    response = GalaxyStreamingResponse(body())
    assert response._sessions_to_release == []

    await response.stream_response(await _collect([]))

    # We must never have touched the scoped proxy, which would have created one.
    assert model_registry == {}


async def test_streaming_no_app_bound_is_noop(monkeypatch):
    _install_fake_app(monkeypatch, app_present=False)

    async def body():
        yield b"x"

    response = GalaxyStreamingResponse(body())
    assert response._sessions_to_release == []

    messages: list = []
    await response.stream_response(await _collect(messages))
    assert any(m["type"] == "http.response.body" for m in messages)


async def test_file_response_releases_before_response_start(monkeypatch, tmp_path):
    f = tmp_path / "download.txt"
    f.write_bytes(b"hello")
    session = FakeSession()
    _install_fake_app(monkeypatch, model_registry={KEY: session})

    response = GalaxyFileResponse(str(f))
    closed_at_start = []

    async def send(message):
        if message["type"] == "http.response.start":
            closed_at_start.append(session.closed)

    async def receive():
        return {"type": "http.request"}

    await response({"type": "http", "method": "GET", "headers": []}, receive, send)

    assert closed_at_start == [True]
    assert session.closed is True


async def test_file_response_releases_on_xaccel_header_only_path(monkeypatch, tmp_path):
    f = tmp_path / "download.txt"
    f.write_bytes(b"hello")
    session = FakeSession()
    _install_fake_app(monkeypatch, model_registry={KEY: session})

    class XAccelFileResponse(GalaxyFileResponse):
        nginx_x_accel_redirect_base = "/internal"

    response = XAccelFileResponse(str(f))
    closed_at_start = []

    async def send(message):
        if message["type"] == "http.response.start":
            closed_at_start.append(session.closed)

    async def receive():
        return {"type": "http.request"}

    await response({"type": "http", "method": "GET", "headers": []}, receive, send)

    assert closed_at_start == [True]
    assert session.closed is True
