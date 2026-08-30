"""Unit tests for the tool form harness comparison of submitted state against a test case."""

import pytest

from galaxy_test.selenium.framework import RunsToolTests

declared_mismatches = RunsToolTests._declared_mismatches


def test_identical_state_matches():
    declared = {"cond": {"test_parameter": "b"}}
    submitted = {"cond": {"test_parameter": "b"}}
    assert declared_mismatches(declared, submitted) == []


def test_undeclared_parameters_are_ignored():
    """The form submits defaults the test says nothing about."""
    declared = {"cond": {"test_parameter": "b"}}
    submitted = {"cond": {"test_parameter": "b", "unused": 0}, "extra": 1}
    assert declared_mismatches(declared, submitted) == []


def test_differing_value_is_reported():
    mismatches = declared_mismatches({"cond": {"p": "b"}}, {"cond": {"p": "a"}})
    assert mismatches == ["cond|p ('a' not 'b')"]


def test_flattened_state_is_reported():
    """A form that sends nested state under a joined key rather than nesting it."""
    mismatches = declared_mismatches({"cond": {"p": "b"}}, {"cond|p": "b"})
    assert mismatches == ["cond (absent)"]


def test_dropped_parameter_is_reported():
    assert declared_mismatches({"cond": {"p": "b"}}, {"cond": {}}) == ["cond|p (absent)"]


def test_missing_nesting_level_is_reported():
    mismatches = declared_mismatches({"sec": {"inner": {"x": "1"}}}, {"sec": {"x": "1"}})
    assert mismatches == ["sec|inner (absent)"]


@pytest.mark.parametrize("submitted_value", [5, "5"])
def test_scalar_types_are_compared_by_text(submitted_value):
    """The request carries typed values; the test case declares them as text."""
    assert declared_mismatches({"n": "5"}, {"n": submitted_value}) == []


def test_declared_file_matches_a_dataset_reference():
    declared = {"i": {"class": "File", "path": "a.bed"}}
    assert declared_mismatches(declared, {"i": {"src": "hda", "id": 3}}) == []


def test_declared_file_without_a_dataset_reference_is_reported():
    declared = {"i": {"class": "File", "path": "a.bed"}}
    assert declared_mismatches(declared, {"i": "a.bed"}) == ["i (expected a dataset, got 'a.bed')"]


def test_repeat_of_datasets_matches():
    """A repeat is a list of dicts; its data parameters are staged like any other."""
    declared = {"queries": [{"input2": {"class": "File", "path": "2.bed"}}]}
    submitted = {"queries": [{"input2": {"src": "hda", "id": "529fd61ab1c6cc36"}}]}
    assert declared_mismatches(declared, submitted) == []


def test_repeat_value_mismatch_is_reported():
    declared = {"r": [{"p": "a"}, {"p": "b"}]}
    submitted = {"r": [{"p": "a"}, {"p": "z"}]}
    assert declared_mismatches(declared, submitted) == ["r|1|p ('z' not 'b')"]


def test_missing_repeat_instance_is_reported():
    declared = {"r": [{"p": "a"}, {"p": "b"}]}
    submitted = {"r": [{"p": "a"}]}
    assert declared_mismatches(declared, submitted) == ["r (1 instances, not 2)"]


def test_list_of_scalars_matches():
    assert declared_mismatches({"vals": ["1", "2"]}, {"vals": [1, 2]}) == []
