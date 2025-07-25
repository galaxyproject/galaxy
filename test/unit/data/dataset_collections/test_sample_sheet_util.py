from typing import Any

import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model.dataset_collections.types.sample_sheet_util import (
    validate_column_definitions as real_validate_column_definitions,
    validate_row as real_validate_row,
)

ALL_ELEMENT_IDENTIFIERS = ["sample1", "sample2", "sample3", "sample4", "sample5"]


def validate_row(row: Any, column_definitions: Any):
    # for testing allow various incompatible data structures to be sent in to assure
    # they fail properly.
    real_validate_row(row, column_definitions, ALL_ELEMENT_IDENTIFIERS)


def validate_column_definitions(column_definitions: Any):
    # for testing allow various incompatible data structures to be sent in to assure
    # they fail properly.
    real_validate_column_definitions(column_definitions)


def test_sample_sheet_validation_skipped_on_empty_definitions():
    validate_row([0, 1], None)  # just ensure no exception is thrown


def test_sample_sheet_validation_number_columns():
    with pytest.raises(RequestParameterInvalidException):
        validate_row([0, 1], [{"type": "int", "name": "replicate number", "default_value": 0, "optional": False}])


def test_sample_sheet_validation_int_type():
    validate_row([1], [{"type": "int", "name": "replicate number", "default_value": 0, "optional": False}])

    with pytest.raises(RequestParameterInvalidException):
        validate_row(["sample1"], [{"type": "int", "name": "replicate number", "default_value": 0, "optional": False}])


def test_sample_sheet_validation_float_type():
    validate_row([1.0], [{"type": "float", "name": "seconds", "optional": False}])

    with pytest.raises(RequestParameterInvalidException):
        validate_row(["sample1"], [{"type": "float", "name": "seconds", "default_value": 0.0, "optional": False}])


def test_sample_sheet_validation_string_type():
    validate_row(["sample1"], [{"type": "string", "name": "condition", "default_value": "none", "optional": False}])

    with pytest.raises(RequestParameterInvalidException):
        validate_row([1], [{"type": "string", "name": "condition", "default_value": "none", "optional": False}])

    # restrict characters that might interfere with CSV/TSV serialization
    with pytest.raises(RequestParameterInvalidException):
        validate_row(
            ["sample1\t"], [{"type": "string", "name": "condition", "default_value": "none", "optional": False}]
        )

    with pytest.raises(RequestParameterInvalidException):
        validate_row(
            ['sample1"'], [{"type": "string", "name": "condition", "default_value": "none", "optional": False}]
        )

    with pytest.raises(RequestParameterInvalidException):
        validate_row(
            ["sample1'"], [{"type": "string", "name": "condition", "default_value": "none", "optional": False}]
        )

    # but allow simple spaces even though we don't allow tabs/newlines in the sheet.
    validate_row(
        ["sample1 is cool"], [{"type": "string", "name": "condition", "default_value": "none", "optional": False}]
    )


def test_sample_sheet_validation_boolean_type():
    validate_row([True], [{"type": "boolean", "name": "control?", "optional": False}])

    with pytest.raises(RequestParameterInvalidException):
        validate_row([1], [{"type": "boolean", "name": "control?", "optional": False}])


def test_sample_sheet_element_identifiers_type():
    validate_row(["sample1"], [{"type": "element_identifier", "name": "control_element", "optional": False}])

    with pytest.raises(RequestParameterInvalidException):
        # not an actual element identifier from the rest of the collection
        validate_row(["sample6"], [{"type": "element_identifier", "name": "control_element", "optional": False}])

    with pytest.raises(RequestParameterInvalidException):
        # invalid type
        validate_row([3], [{"type": "element_identifier", "name": "control_element", "optional": False}])


def test_sample_sheet_validation_restrictions():
    validate_row(
        ["control"],
        [
            {
                "type": "string",
                "restrictions": ["treatment", "control"],
                "name": "condition",
                "default_value": "treatment",
                "optional": False,
            }
        ],
    )

    with pytest.raises(RequestParameterInvalidException):
        validate_row(
            ["controlx"],
            [
                {
                    "type": "string",
                    "restrictions": ["treatment", "control"],
                    "name": "condition",
                    "default_value": "treatment",
                    "optional": False,
                }
            ],
        )


def test_sample_sheet_validation_length():
    column_definitions = [
        {
            "type": "string",
            "validators": [{"type": "length", "min": 6}],
            "name": "condition",
            "default_value": "default",
            "optional": False,
        }
    ]
    validate_row(["treatment"], column_definitions)

    with pytest.raises(RequestParameterInvalidException):
        validate_row(["treat"], column_definitions)


def test_sample_sheet_validation_min_max():
    column_definitions = [
        {"type": "int", "validators": [{"type": "in_range", "min": 6}], "name": "replicate number", "optional": False}
    ]
    validate_row([7], column_definitions)

    with pytest.raises(RequestParameterInvalidException):
        validate_row([5], column_definitions)


def test_column_definitions_validators_on_valid_defs():
    column_definitions = [
        {
            "type": "string",
            "restrictions": ["treatment", "control"],
            "name": "condition",
            "default_value": "treatment",
            "optional": False,
        }
    ]
    validate_column_definitions(column_definitions)


def test_column_definitions_validators_invalid_length():
    column_definitions = [
        {
            "type": "string",
            "validators": [{"type": "length", "min": 6}],
            "name": "condition",
            "default_value": "default",
            "optional": False,
        }
    ]
    validate_column_definitions(column_definitions)


def test_column_definitions_do_not_allow_unsafe_validators():
    column_definitions = [
        {
            "type": "string",
            "name": "condition",
            "validators": [
                {"type": "expression", "expression": "False"},
            ],
            "default_value": "default",
            "optional": False,
        }
    ]

    with pytest.raises(RequestParameterInvalidException):
        validate_column_definitions(column_definitions)


def test_column_definitions_do_not_allow_special_characters_in_column_name():
    column_definitions = [
        {
            "type": "string",
            "name": "condition\t",
            "default_value": "default",
            "optional": False,
        }
    ]

    with pytest.raises(RequestParameterInvalidException):
        validate_column_definitions(column_definitions)
