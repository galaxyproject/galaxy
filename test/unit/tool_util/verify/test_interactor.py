"""Tests for adapting test output properties onto dataset API response keys."""

import pytest

from galaxy.tool_util.verify.interactor import (
    compare_expected_metadata_to_api_response,
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
