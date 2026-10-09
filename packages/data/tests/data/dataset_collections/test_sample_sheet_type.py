import pytest

from galaxy.exceptions import (
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.model import HistoryDatasetAssociation
from galaxy.model.dataset_collections.types.sample_sheet import SampleSheetDatasetCollectionType


def _make_instances(*identifiers):
    return {identifier: HistoryDatasetAssociation(extension="txt") for identifier in identifiers}


def test_generate_elements_no_column_definitions_no_rows():
    # Uploading a sample_sheet collection without any sample-sheet-specific
    # columns (no column_definitions, no rows) should succeed and produce one
    # element per identifier with empty columns.
    instances = _make_instances("a", "b")
    elements = list(SampleSheetDatasetCollectionType().generate_elements(instances))
    assert [e.element_identifier for e in elements] == ["a", "b"]
    assert all(e.columns is None for e in elements)


def test_generate_elements_empty_list_column_definitions_no_rows():
    instances = _make_instances("a", "b")
    elements = list(SampleSheetDatasetCollectionType().generate_elements(instances, column_definitions=[], rows=None))
    assert [e.element_identifier for e in elements] == ["a", "b"]
    assert all(e.columns is None for e in elements)


def test_generate_elements_rows_required_with_column_definitions():
    instances = _make_instances("a", "b")
    column_definitions = [{"type": "int", "name": "replicate", "optional": False}]
    with pytest.raises(RequestParameterMissingException):
        list(
            SampleSheetDatasetCollectionType().generate_elements(
                instances, column_definitions=column_definitions, rows=None
            )
        )


def test_generate_elements_rows_validated_with_column_definitions():
    instances = _make_instances("a", "b")
    column_definitions = [{"type": "int", "name": "replicate", "optional": False}]
    rows = {"a": [1], "b": None}
    with pytest.raises(RequestParameterInvalidException):
        list(
            SampleSheetDatasetCollectionType().generate_elements(
                instances, column_definitions=column_definitions, rows=rows
            )
        )
