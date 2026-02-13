import pytest
from pydantic import ValidationError

from galaxy.tool_util_models.parameters import (
    build_collection_model_for_type,
    collection_runtime_discriminator,
    DataCollectionListRuntime,
    DataCollectionPairedRuntime,
    DataCollectionRecordRuntime,
)

_FILE_ELEMENT = {
    "class": "File",
    "element_identifier": "f1",
    "basename": "f1.txt",
    "location": "step_input://0",
    "path": "/tmp/f1.txt",
    "nameroot": "f1",
    "nameext": ".txt",
    "format": "txt",
    "size": 100,
}


def test_build_collection_model_returns_static_for_leaf():
    assert build_collection_model_for_type("list") is DataCollectionListRuntime
    assert build_collection_model_for_type("paired") is DataCollectionPairedRuntime
    assert build_collection_model_for_type("record") is DataCollectionRecordRuntime


def test_build_collection_model_returns_none_for_unknown():
    assert build_collection_model_for_type("unknown_type") is None


def test_dynamic_model_accepts_correct_inner_type():
    model = build_collection_model_for_type("list:paired")
    assert model is not None
    result = model.model_validate(
        {
            "class": "Collection",
            "name": "good",
            "collection_type": "list:paired",
            "tags": [],
            "elements": [
                {
                    "class": "Collection",
                    "name": "p1",
                    "collection_type": "paired",
                    "tags": [],
                    "elements": {
                        "forward": {**_FILE_ELEMENT, "element_identifier": "forward"},
                        "reverse": {
                            **_FILE_ELEMENT,
                            "element_identifier": "reverse",
                            "basename": "r.txt",
                            "location": "step_input://1",
                            "path": "/tmp/r.txt",
                            "nameroot": "r",
                        },
                    },
                }
            ],
        }
    )
    assert result.collection_type == "list:paired"
    assert isinstance(result.elements[0], DataCollectionPairedRuntime)


def test_dynamic_model_rejects_wrong_inner_type():
    model = build_collection_model_for_type("list:paired")
    assert model is not None
    with pytest.raises(ValidationError):
        model.model_validate(
            {
                "class": "Collection",
                "name": "bad",
                "collection_type": "list:paired",
                "tags": [],
                "elements": [
                    {
                        "class": "Collection",
                        "name": "l1",
                        "collection_type": "list",
                        "tags": [],
                        "elements": [_FILE_ELEMENT],
                    }
                ],
            }
        )


def test_dynamic_model_rejects_wrong_collection_type_literal():
    model = build_collection_model_for_type("list:paired")
    assert model is not None
    with pytest.raises(ValidationError):
        model.model_validate(
            {
                "class": "Collection",
                "name": "bad",
                "collection_type": "list:list",
                "tags": [],
                "elements": [],
            }
        )


def test_dynamic_model_rejects_depth_mismatch():
    model = build_collection_model_for_type("list:list:paired")
    assert model is not None
    # Inner is "paired" (depth 1) but should be "list:paired" (depth 2)
    with pytest.raises(ValidationError):
        model.model_validate(
            {
                "class": "Collection",
                "name": "bad",
                "collection_type": "list:list:paired",
                "tags": [],
                "elements": [
                    {
                        "class": "Collection",
                        "name": "p1",
                        "collection_type": "paired",
                        "tags": [],
                        "elements": {
                            "forward": {**_FILE_ELEMENT, "element_identifier": "forward"},
                            "reverse": {
                                **_FILE_ELEMENT,
                                "element_identifier": "reverse",
                                "basename": "r.txt",
                                "location": "step_input://1",
                                "path": "/tmp/r.txt",
                                "nameroot": "r",
                            },
                        },
                    }
                ],
            }
        )


def test_dynamic_model_json_schema_precise():
    """JSON Schema for list:paired shows elements as array of paired, not Union."""
    model = build_collection_model_for_type("list:paired")
    assert model is not None
    schema = model.model_json_schema()
    # elements should reference paired model, NOT anyOf with all types
    elements_schema = schema["properties"]["elements"]
    schema_str = str(elements_schema)
    assert "anyOf" not in schema_str


def test_dynamic_model_caching():
    m1 = build_collection_model_for_type("list:paired")
    m2 = build_collection_model_for_type("list:paired")
    assert m1 is m2


def test_dynamic_model_record_paired_accepts_correct():
    """record:paired dynamic model: dict of paired collections."""
    model = build_collection_model_for_type("record:paired")
    assert model is not None
    result = model.model_validate(
        {
            "class": "Collection",
            "name": "rec",
            "collection_type": "record:paired",
            "tags": [],
            "elements": {
                "sample_a": {
                    "class": "Collection",
                    "name": "sample_a",
                    "collection_type": "paired",
                    "tags": [],
                    "elements": {
                        "forward": {**_FILE_ELEMENT, "element_identifier": "forward"},
                        "reverse": {
                            **_FILE_ELEMENT,
                            "element_identifier": "reverse",
                            "basename": "r.txt",
                            "location": "step_input://1",
                            "path": "/tmp/r.txt",
                            "nameroot": "r",
                        },
                    },
                },
            },
        }
    )
    assert result.collection_type == "record:paired"
    assert isinstance(result.elements["sample_a"], DataCollectionPairedRuntime)


def test_dynamic_model_record_paired_rejects_wrong_inner():
    """record:paired rejects inner collection with wrong type (list instead of paired)."""
    model = build_collection_model_for_type("record:paired")
    assert model is not None
    with pytest.raises(ValidationError):
        model.model_validate(
            {
                "class": "Collection",
                "name": "bad_rec",
                "collection_type": "record:paired",
                "tags": [],
                "elements": {
                    "sample_a": {
                        "class": "Collection",
                        "name": "sample_a",
                        "collection_type": "list",
                        "tags": [],
                        "elements": [_FILE_ELEMENT],
                    },
                },
            }
        )


def test_build_collection_model_returns_none_for_unknown_nested():
    assert build_collection_model_for_type("list:unknown_type") is None
    assert build_collection_model_for_type("record:unknown") is None
    assert build_collection_model_for_type("list:list:unknown") is None


def test_dynamic_model_record_paired_empty_elements():
    """Empty dict elements on a record-like dynamic model should validate."""
    model = build_collection_model_for_type("record:paired")
    assert model is not None
    result = model.model_validate(
        {
            "class": "Collection",
            "name": "empty_rec",
            "collection_type": "record:paired",
            "tags": [],
            "elements": {},
        }
    )
    assert result.elements == {}


def test_dynamic_model_json_schema_deeply_nested():
    """JSON Schema for list:list:paired has 3 levels, no anyOf at any level."""
    model = build_collection_model_for_type("list:list:paired")
    assert model is not None
    schema = model.model_json_schema()
    # Outer elements: array of list:paired models
    elements_schema = schema["properties"]["elements"]
    schema_str = str(elements_schema)
    assert "anyOf" not in schema_str

    # Should have definitions for multiple distinct models (at least the inner dynamic + leaf)
    defs = schema.get("$defs", {})
    assert len(defs) >= 2
    assert any("list_paired" in k for k in defs.keys())


def test_collection_runtime_discriminator_known_types():
    """Known leaf and nested types route correctly."""
    assert collection_runtime_discriminator({"collection_type": "list"}) == "list"
    assert collection_runtime_discriminator({"collection_type": "paired"}) == "paired"
    assert collection_runtime_discriminator({"collection_type": "record"}) == "record"
    assert collection_runtime_discriminator({"collection_type": "paired_or_unpaired"}) == "paired_or_unpaired"
    assert collection_runtime_discriminator({"collection_type": "sample_sheet"}) == "sample_sheet"
    assert collection_runtime_discriminator({"collection_type": "list:paired"}) == "nested_list"
    assert collection_runtime_discriminator({"collection_type": "record:paired"}) == "nested_record"


def test_collection_runtime_discriminator_rejects_unknown():
    """Unknown collection_type raises ValueError instead of silently defaulting."""
    with pytest.raises(ValueError, match="Unknown collection_type"):
        collection_runtime_discriminator({"collection_type": "banana"})


def test_collection_runtime_discriminator_missing_routes_to_list():
    """Missing/empty collection_type routes to list for Pydantic schema rejection."""
    assert collection_runtime_discriminator({"collection_type": ""}) == "list"
    assert collection_runtime_discriminator({}) == "list"
