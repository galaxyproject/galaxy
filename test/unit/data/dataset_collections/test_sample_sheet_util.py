import pytest
from pydantic import ValidationError

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model.dataset_collections.types.sample_sheet_util import (
    validate_column_definitions,
    validate_row,
)
from galaxy.schema.schema import (
    SampleSheetColumnDefinitions,
    SampleSheetRow,
)


def test_sample_sheet_validation_skipped_on_empty_definitions():
    validate_row([0, 1], None)  # just ensure no execption is thrown


def test_sample_sheet_validation_number_columns():
    with pytest.raises(RequestParameterInvalidException):
        validate_row([0, 1], [{"type": "int"}])


def test_sample_sheet_validation_int_type():
    validate_row([1], [{"type": "int"}])

    with pytest.raises(RequestParameterInvalidException):
        validate_row(["sample1"], [{"type": "int"}])


def test_sample_sheet_validation_float_type():
    validate_row([1.0], [{"type": "float"}])

    with pytest.raises(RequestParameterInvalidException):
        validate_row(["sample1"], [{"type": "float"}])


def test_sample_sheet_validation_string_type():
    validate_row(["sample1"], [{"type": "string"}])

    with pytest.raises(RequestParameterInvalidException):
        validate_row([1], [{"type": "string"}])


def test_sample_sheet_validation_boolean_type():
    validate_row([True], [{"type": "boolean"}])

    with pytest.raises(RequestParameterInvalidException):
        validate_row([1], [{"type": "boolean"}])


def test_sample_sheet_validation_restrictions():
    validate_row(["control"], [{"type": "string", "restrictions": ["treatment", "control"]}])

    with pytest.raises(RequestParameterInvalidException):
        validate_row(["controlx"], [{"type": "string", "restrictions": ["treatment", "control"]}])


def test_sample_sheet_validation_length():
    column_definitions = [{"type": "string", "validators": [{"type": "length", "min": 6}]}]
    validate_row(["treatment"], column_definitions)

    with pytest.raises(RequestParameterInvalidException):
        validate_row(["treat"], column_definitions)


def test_sample_sheet_validation_min_max():
    column_definitions = [{"type": "int", "validators": [{"type": "in_range", "min": 6}]}]
    validate_row([7], column_definitions)

    with pytest.raises(RequestParameterInvalidException):
        validate_row([5], column_definitions)


def test_column_definitions_validators_on_valid_defs():
    column_definitions = [{"type": "string", "restrictions": ["treatment", "control"]}]
    validate_column_definitions(column_definitions)


def test_column_definitions_validators_invalid_length():
    column_definitions = [{"type": "string", "validators": [{"type": "length", "min": 6}]}]
    validate_column_definitions(column_definitions)


def test_column_definitions_do_not_allow_unsafe_validators():
    column_definitions = [
        {
            "type": "string",
            "validators": [
                {"type": "expression", "expression": "False"},
            ],
        }
    ]

    with pytest.raises(ValidationError):
        validate_column_definitions(column_definitions)
