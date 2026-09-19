"""Tests for adapting test output properties onto dataset API response keys."""

import http.server
import socket
import struct
import threading
import time
from typing import (
    Any,
    Literal,
)

import pytest
import requests
import responses
from requests.exceptions import (
    ConnectionError,
    HTTPError,
)

from galaxy.tool_util.verify.interactor import (
    compare_expected_metadata_to_api_response,
    GalaxyInteractorApi,
    get_metadata_to_test,
    PathOrLocation,
    POLLING_BACKOFF,
    POLLING_DELTA,
)
from galaxy.tool_util.verify.wait import DEFAULT_POLLING_DELTA


def test_ftype_maps_onto_file_ext():
    assert get_metadata_to_test({"ftype": "bed"}) == {"file_ext": "bed"}


def test_datatype_specific_metadata_is_prefixed():
    assert get_metadata_to_test({"metadata": {"columns": 3}}) == {"metadata_columns": 3}


@pytest.mark.parametrize("value", [True, False])
def test_visible_passes_through_unprefixed(value):
    """visible is a top level key on the dataset API response, not datatype metadata."""
    assert get_metadata_to_test({"visible": value}) == {"visible": value}


def test_visible_false_still_produces_work():
    """The callers skip the API request on an empty dict, so `visible: false` must not read as unset."""
    assert get_metadata_to_test({"visible": False})


def test_visible_unset_is_omitted():
    assert get_metadata_to_test({"ftype": "bed"}) == {"file_ext": "bed"}
    assert get_metadata_to_test({}) == {}


def test_visible_compares_against_api_response():
    compare_expected_metadata_to_api_response({"visible": False}, {"visible": False})


def test_visible_mismatch_raises():
    with pytest.raises(Exception) as exc:
        compare_expected_metadata_to_api_response({"visible": False}, {"visible": True})
    assert "visible" in str(exc.value)


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _ResponseInteractor(GalaxyInteractorApi):
    """Interactor whose HTTP layer always yields one canned response."""

    def __init__(self, response):
        self._response = response

    def _get(self, *args, **kwds):
        return self._response


def test_test_data_path_returns_path_on_200():
    interactor = _ResponseInteractor(_FakeResponse(200, "/srv/test-data/1.bed"))
    assert interactor.test_data_path("some_tool", "1.bed") == "/srv/test-data/1.bed"


def test_test_data_path_returns_none_on_404():
    """A 404 means the server has no path for this file, not that it errored.

    It used to return the error body, so callers got a dict where a path was
    expected and os.path.exists() raised TypeError.
    """
    interactor = _ResponseInteractor(_FakeResponse(404, {"err_msg": "not found", "err_code": 0}))
    assert interactor.test_data_path("some_tool", "1.bed") is None


def test_test_data_path_raises_on_other_errors():
    interactor = _ResponseInteractor(_FakeResponse(500, {"err_msg": "boom"}))
    with pytest.raises(Exception) as exc:
        interactor.test_data_path("some_tool", "1.bed")
    assert "boom" in str(exc.value)


class _PathLookupInteractor(GalaxyInteractorApi):
    """Interactor with a stubbed server-side path lookup, recording its calls."""

    def __init__(self, server_path, downloaded="/tmp/downloaded/1.bed"):
        self._server_path = server_path
        self._downloaded = downloaded
        self.calls: list[str] = []

    def test_data_path(self, tool_id, filename, tool_version=None):
        self.calls.append(filename)
        return self._server_path

    def test_data_download(self, *args, **kwds):
        return self._downloaded


def test_get_path_or_location_falls_back_when_server_has_no_path():
    """force_path_paste plus a 404 must download, not build a file://None URI."""
    interactor = _PathLookupInteractor(server_path=None)
    result = interactor._get_path_or_location("1.bed", {}, "some_tool", force_path_paste=True)
    assert result.path == "/tmp/downloaded/1.bed"
    assert result.location is None


def test_get_path_or_location_asks_the_server_once():
    """The path lookup used to be repeated for the same input."""
    interactor = _PathLookupInteractor(server_path=None)
    interactor._get_path_or_location("1.bed", {}, "some_tool", force_path_paste=True)
    assert interactor.calls == ["1.bed"]


def test_get_path_or_location_uses_server_path_when_available():
    interactor = _PathLookupInteractor(server_path="/srv/test-data/1.bed")
    result = interactor._get_path_or_location("1.bed", {}, "some_tool", force_path_paste=True)
    assert result.location == "file:///srv/test-data/1.bed"
    assert result.path is None
    assert interactor.calls == ["1.bed"]


class _RecordingInteractor(GalaxyInteractorApi):
    """Interactor recording how each _get_path_or_location call was made."""

    def __init__(self):
        self.calls: list[dict] = []

    def _get_path_or_location(
        self,
        fname: str,
        test_data: dict[str, Any],
        tool_id: str,
        tool_version: str | None = None,
        force_path_paste: bool = False,
        mode: Literal["file", "directory"] = "file",
    ) -> PathOrLocation:
        self.calls.append({"force_path_paste": force_path_paste, "mode": mode})
        return PathOrLocation(name=fname, location=None, path=f"/tmp/{fname}")


def _test_data(fname, **kwds):
    data = {
        "fname": fname,
        "ftype": "bed",
        "dbkey": "?",
        "composite_data": None,
    }
    data.update(kwds)
    return data


@pytest.mark.parametrize("force_path_paste", [True, False])
def test_remote_to_input_forwards_force_path_paste(force_path_paste):
    """--force_path_paste must reach _get_path_or_location for ordinary inputs.

    It was only forwarded on the composite_data branch, so the flag was
    silently ignored for the far commoner single-file input.
    """
    interactor = _RecordingInteractor()
    interactor.remote_to_input(_test_data("1.bed"), "some_tool", force_path_paste=force_path_paste)
    assert len(interactor.calls) == 1
    assert interactor.calls[0]["force_path_paste"] is force_path_paste


@pytest.mark.parametrize("force_path_paste", [True, False])
def test_remote_to_input_forwards_force_path_paste_for_composite_data(force_path_paste):
    interactor = _RecordingInteractor()
    interactor.remote_to_input(
        _test_data("1.bed", composite_data=["a.txt", "b.txt"]), "some_tool", force_path_paste=force_path_paste
    )
    assert len(interactor.calls) == 2
    assert all(call["force_path_paste"] is force_path_paste for call in interactor.calls)


GALAXY_URL = "http://galaxy.example"
API = f"{GALAXY_URL}/api"


@pytest.fixture
def interactor():
    return GalaxyInteractorApi(
        galaxy_url=GALAXY_URL, master_api_key="admin", api_key="key", download_attempts=3, download_sleep=0
    )


@pytest.fixture
def mocked():
    with responses.RequestsMock() as rsps:
        yield rsps


def test_session_is_available_while_resolving_user_key(mocked):
    mocked.get(f"{API}/users", json=[{"email": "user@example.org", "id": "user1"}])
    mocked.post(f"{API}/users/user1/api_key", json="resolved-key")

    interactor = GalaxyInteractorApi(
        galaxy_url=GALAXY_URL,
        master_api_key="admin",
        test_user="user@example.org",
    )

    assert interactor.api_key == "resolved-key"


def test_verify_output_dataset_retries_while_dataset_is_not_ready(interactor, mocked):
    display = f"{API}/histories/hist1/contents/hda1/display"
    mocked.get(display, status=409)
    mocked.get(display, body=b"payload")
    interactor.verify_output_dataset("hist1", "hda1", None, {"assert_list": []}, "some_tool")
    assert len(mocked.calls) == 2


def test_verify_output_dataset_gives_up_after_download_attempts(interactor, mocked):
    display = f"{API}/histories/hist1/contents/hda1/display"
    for _ in range(3):
        mocked.get(display, status=409)
    with pytest.raises(HTTPError, match="409"):
        interactor.verify_output_dataset("hist1", "hda1", None, {"assert_list": []}, "some_tool")
    assert len(mocked.calls) == 3


def test_wait_for_job_surfaces_http_status(interactor, mocked):
    mocked.get(f"{API}/jobs/job1", status=502)
    with pytest.raises(HTTPError, match="502"):
        interactor.wait_for_job("job1")


def test_wait_for_job_returns_when_job_is_ok(interactor, mocked):
    mocked.get(f"{API}/jobs/job1", json={"state": "ok"})
    interactor.wait_for_job("job1")


def test_requests_reuse_one_connection_per_thread():
    """Polling should not open a fresh TCP connection every time."""
    connects = []

    class CountingServer(http.server.ThreadingHTTPServer):
        def get_request(self):
            conn, addr = super().get_request()
            connects.append(addr)
            return conn, addr

    class Handler(http.server.BaseHTTPRequestHandler):
        # HTTP/1.0 closes after every response, which would hide reuse.
        protocol_version = "HTTP/1.1"

        def do_GET(self):
            body = b'{"state": "running"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = CountingServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True).start()
    try:
        interactor = GalaxyInteractorApi(
            galaxy_url=f"http://127.0.0.1:{server.server_address[1]}",
            master_api_key="key",
            api_key="key",
        )
        for _ in range(25):
            interactor._get("jobs/abc")
    finally:
        server.shutdown()
        server.server_close()

    assert len(connects) == 1, f"expected one reused connection, got {len(connects)}"


def _dropping_server(drop_first: bool = True):
    """A listener that resets the first connection, then serves normally.

    SO_LINGER 0 forces an RST rather than a clean FIN, which is what a
    pooled connection looks like when the server has closed it and urllib3
    has not noticed yet.
    """
    accepts = []
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(8)

    def serve():
        dropped = not drop_first
        while True:
            try:
                conn, _ = listener.accept()
            except OSError:
                return
            accepts.append(1)
            if not dropped:
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
                conn.close()
                dropped = True
                continue
            try:
                conn.recv(65536)
                body = b'{"state": "running"}'
                conn.sendall(
                    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
                    + str(len(body)).encode()
                    + b"\r\n\r\n"
                    + body
                )
            finally:
                conn.close()

    threading.Thread(target=serve, daemon=True).start()
    return listener, listener.getsockname()[1], accepts


def test_dead_pooled_connection_is_retried():
    """A GET surviving a connection the server has already closed.

    requests mounts its adapters with max_retries=0, so without the session's
    retry configuration this surfaces the reset to the caller instead.
    """
    listener, port, accepts = _dropping_server()
    try:
        interactor = GalaxyInteractorApi(galaxy_url=f"http://127.0.0.1:{port}", master_api_key="key", api_key="key")
        response = interactor._get("jobs/abc")
    finally:
        listener.close()

    assert response.status_code == 200
    assert len(accepts) == 2, f"expected a retry on a second connection, got {len(accepts)}"


def test_post_is_not_resubmitted_when_the_connection_drops():
    """A retry must never resend a POST - that would submit the job twice."""
    listener, port, accepts = _dropping_server()
    try:
        interactor = GalaxyInteractorApi(galaxy_url=f"http://127.0.0.1:{port}", master_api_key="key", api_key="key")
        with pytest.raises(ConnectionError):
            interactor._post("jobs", data={"a": 1})
    finally:
        listener.close()

    assert len(accepts) == 1, f"POST was resent on a new connection ({len(accepts)} accepts)"


def test_each_thread_gets_its_own_session():
    """One interactor is shared across script.py's worker pool.

    requests.Session is not thread-safe, so sharing one across those
    workers is the hazard this avoids.
    """
    interactor = GalaxyInteractorApi(galaxy_url=GALAXY_URL, master_api_key="key", api_key="key")
    seen = []
    threads = [threading.Thread(target=lambda: seen.append(interactor._session())) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(seen) == 4
    assert len({id(session) for session in seen}) == 4
    # ... and reused within a thread.
    assert interactor._session() is interactor._session()


def test_session_factory_is_injectable():
    sentinel = requests.Session()
    interactor = GalaxyInteractorApi(
        galaxy_url=GALAXY_URL, master_api_key="key", api_key="key", session_factory=lambda: sentinel
    )
    assert interactor._session() is sentinel


def test_polling_cadence_defaults_to_the_module_settings():
    interactor = GalaxyInteractorApi(galaxy_url=GALAXY_URL, master_api_key="admin", api_key="key")
    assert interactor.polling_delta == POLLING_DELTA
    assert interactor.polling_backoff == POLLING_BACKOFF


def test_configured_polling_delta_paces_job_status_checks(mocked):
    # Deliberately slower than the default cadence, so a delta that never
    # reaches wait_on fails this rather than passing on the default sleep.
    delta = DEFAULT_POLLING_DELTA * 2
    interactor = GalaxyInteractorApi(
        galaxy_url=GALAXY_URL, master_api_key="admin", api_key="key", polling_delta=delta, polling_backoff=0
    )
    mocked.get(f"{API}/jobs/job1", json={"state": "running"})
    mocked.get(f"{API}/jobs/job1", json={"state": "ok"})
    started = time.monotonic()
    interactor.wait_for_job("job1")
    assert time.monotonic() - started >= delta
