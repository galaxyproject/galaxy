"""Tests for the discriminated `TestOutputAssertions` Union."""

import json

import pytest
from pydantic import ValidationError

from galaxy.tool_util_models import (
    TestCollectionCollectionElementAssertions,
    TestCollectionOutputAssertions,
    TestDataOutputAssertions,
    Tests,
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


def test_doc_is_optional_on_test_job():
    tests = Tests.model_validate([{"job": {}, "outputs": {}}])
    assert tests.root[0].doc is None
    schema = Tests.model_json_schema()
    test_job = schema["$defs"]["TestJob"]
    assert "doc" not in test_job.get("required", [])


def test_test_job_top_level_properties_have_descriptions():
    schema = Tests.model_json_schema()
    props = schema["$defs"]["TestJob"]["properties"]
    for name in ("doc", "job", "outputs", "expect_failure"):
        assert props[name].get("description"), f"missing description on TestJob.{name}"


def test_test_job_titles_are_human_readable_not_lowercase():
    schema = Tests.model_json_schema()
    props = schema["$defs"]["TestJob"]["properties"]
    assert props["doc"]["title"] == "Doc"
    assert props["outputs"]["title"] == "Outputs"
    assert props["expect_failure"]["title"] == "Expect Failure"


def test_assertion_model_titles_are_human_readable():
    schema = Tests.model_json_schema()
    defs = schema["$defs"]
    assert defs["has_text_model"]["title"] == "Assert Has Text"
    assert defs["has_text_model_nested"]["title"] == "Assert Has Text (Nested)"
    # Every field in has_text_model has an explicit title.
    for name, prop in defs["has_text_model"]["properties"].items():
        assert prop.get("title"), f"has_text_model.{name} missing title"


def test_test_data_output_assertions_field_titles():
    schema = Tests.model_json_schema()
    props = schema["$defs"]["TestDataOutputAssertions"]["properties"]
    assert props["lines_diff"]["title"] == "Lines Diff"
    assert props["class"]["title"] == "Class"
    assert props["ftype"]["title"] == "File Type"


def test_top_level_schema_has_title_description_and_schema():
    schema = Tests.model_json_schema()
    assert schema.get("title") == "GalaxyWorkflowTests"
    assert schema.get("description")
    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"


def test_root_model_wrappers_have_clean_defs_keys():
    schema = Tests.model_json_schema()
    defs = schema["$defs"]
    assert "Job" in defs
    assert "assertion_list" in defs
    # None of the RootModel-auto-generated mangled names should appear.
    mangled = [k for k in defs if k.startswith("RootModel_")]
    assert not mangled, f"unexpected mangled RootModel defs: {mangled}"


def test_test_data_output_assertions_properties_have_descriptions():
    schema = Tests.model_json_schema()
    props = schema["$defs"]["TestDataOutputAssertions"]["properties"]
    for name in (
        "asserts",
        "metadata",
        "file",
        "ftype",
        "sort",
        "checksum",
        "compare",
        "lines_diff",
        "decompress",
        "delta",
        "delta_frac",
        "location",
    ):
        assert props[name].get("description"), f"missing description on TestDataOutputAssertions.{name}"
