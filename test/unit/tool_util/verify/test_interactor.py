"""Tests for adapting test output properties onto dataset API response keys."""

import pytest

from galaxy.tool_util.verify.interactor import (
    compare_expected_metadata_to_api_response,
    GalaxyInteractorApi,
    get_metadata_to_test,
)


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


def _interactor_with_response(response):
    interactor = GalaxyInteractorApi.__new__(GalaxyInteractorApi)
    interactor._get = lambda *args, **kwds: response  # type: ignore[method-assign]
    return interactor


def test_test_data_path_returns_path_on_200():
    interactor = _interactor_with_response(_FakeResponse(200, "/srv/test-data/1.bed"))
    assert interactor.test_data_path("some_tool", "1.bed") == "/srv/test-data/1.bed"


def test_test_data_path_returns_none_on_404():
    """A 404 means the server has no path for this file, not that it errored.

    It used to return the error body, so callers got a dict where a path was
    expected and os.path.exists() raised TypeError.
    """
    interactor = _interactor_with_response(_FakeResponse(404, {"err_msg": "not found", "err_code": 0}))
    assert interactor.test_data_path("some_tool", "1.bed") is None


def test_test_data_path_raises_on_other_errors():
    interactor = _interactor_with_response(_FakeResponse(500, {"err_msg": "boom"}))
    with pytest.raises(Exception) as exc:
        interactor.test_data_path("some_tool", "1.bed")
    assert "boom" in str(exc.value)


def _interactor_for_path_lookup(server_path, downloaded="/tmp/downloaded/1.bed"):
    """Interactor whose server-side lookup yields server_path, counting calls."""
    interactor = GalaxyInteractorApi.__new__(GalaxyInteractorApi)
    calls: list[str] = []

    def _test_data_path(tool_id, filename, tool_version=None):
        calls.append(filename)
        return server_path

    interactor.test_data_path = _test_data_path  # type: ignore[method-assign]
    interactor.test_data_download = lambda *args, **kwds: downloaded  # type: ignore[method-assign]
    return interactor, calls


def test_get_path_or_location_falls_back_when_server_has_no_path():
    """force_path_paste plus a 404 must download, not build a file://None URI."""
    interactor, _ = _interactor_for_path_lookup(server_path=None)
    result = interactor._get_path_or_location("1.bed", {}, "some_tool", force_path_paste=True)
    assert result.path == "/tmp/downloaded/1.bed"
    assert result.location is None


def test_get_path_or_location_asks_the_server_once():
    """The path lookup used to be repeated for the same input."""
    interactor, calls = _interactor_for_path_lookup(server_path=None)
    interactor._get_path_or_location("1.bed", {}, "some_tool", force_path_paste=True)
    assert calls == ["1.bed"]


def test_get_path_or_location_uses_server_path_when_available():
    interactor, calls = _interactor_for_path_lookup(server_path="/srv/test-data/1.bed")
    result = interactor._get_path_or_location("1.bed", {}, "some_tool", force_path_paste=True)
    assert result.location == "file:///srv/test-data/1.bed"
    assert result.path is None
    assert calls == ["1.bed"]
