"""Tests for the discriminated `TestOutputAssertions` Union."""

import json

import pytest
from pydantic import ValidationError

from galaxy.tool_util_models import (
    Tests,
    TestCollectionCollectionElementAssertions,
    TestCollectionOutputAssertions,
    TestDataOutputAssertions,
)


def _one_test(outputs):
    return [{"doc": "t", "job": {}, "outputs": outputs}]


def test_implicit_file_output_validates_as_data():
    tests = Tests.model_validate(_one_test({"out": {"asserts": [{"that": "has_text", "text": "x"}]}}))
    out = tests.root[0].outputs["out"]
    assert isinstance(out, TestDataOutputAssertions)


def test_explicit_collection_output_validates_as_collection():
    tests = Tests.model_validate(_one_test({"out": {"class": "Collection", "elements": {"a": {"asserts": []}}}}))
    out = tests.root[0].outputs["out"]
    assert isinstance(out, TestCollectionOutputAssertions)


@pytest.mark.parametrize("value", [True, 42, 3.14, "hello"])
def test_scalar_literal_output_validates(value):
    tests = Tests.model_validate(_one_test({"out": value}))
    assert tests.root[0].outputs["out"] == value


def test_nested_collection_element_with_class_collection_validates():
    tests = Tests.model_validate(
        _one_test(
            {
                "out": {
                    "class": "Collection",
                    "elements": {
                        "inner": {
                            "class": "Collection",
                            "elements": {"leaf": {"asserts": []}},
                        }
                    },
                }
            }
        )
    )
    out = tests.root[0].outputs["out"]
    assert isinstance(out, TestCollectionOutputAssertions)
    assert out.elements is not None
    inner = out.elements["inner"]
    assert isinstance(inner, TestCollectionCollectionElementAssertions)


def test_unknown_field_on_file_output_yields_single_error():
    with pytest.raises(ValidationError) as exc:
        Tests.model_validate(_one_test({"out": {"asserts": [], "garbage_key": 1}}))
    errs = exc.value.errors()
    assert len(errs) == 1
    err = errs[0]
    assert err["loc"][:4] == (0, "outputs", "out", "File")
    assert err["loc"][-1] == "garbage_key"
    assert err["type"] == "extra_forbidden"


def test_unknown_class_value_yields_single_class_literal_error():
    with pytest.raises(ValidationError) as exc:
        Tests.model_validate(_one_test({"out": {"class": "Banana"}}))
    errs = exc.value.errors()
    assert len(errs) == 1
    err = errs[0]
    assert err["loc"][:4] == (0, "outputs", "out", "File")
    assert err["type"] == "literal_error"


def test_bad_asserts_error_scoped_to_file_branch():
    with pytest.raises(ValidationError) as exc:
        Tests.model_validate(_one_test({"out": {"asserts": [{"that": "not_a_real_assert"}]}}))
    errs = exc.value.errors()
    for err in errs:
        assert "Collection" not in err["loc"]
        assert "scalar" not in err["loc"]
        assert err["loc"][:4] == (0, "outputs", "out", "File")


def test_json_schema_emits_discriminator_for_outputs():
    schema = Tests.model_json_schema()
    dumped = json.dumps(schema)
    assert "discriminator" in dumped or '"oneOf"' in dumped
