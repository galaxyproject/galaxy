from galaxy.exceptions import RequestParameterMissingException
from galaxy.model import DatasetCollectionElement
from . import BaseDatasetCollectionType
from .sample_sheet_util import validate_row


class SampleSheetDatasetCollectionType(BaseDatasetCollectionType):
    """A flat list of named elements starting rows with column metadata."""

    collection_type = "sample_sheet"

    def generate_elements(self, dataset_instances, **kwds):
        rows = kwds.get("rows", None)
        column_definitions = kwds.get("column_definitions", None)
        if rows is None:
            raise RequestParameterMissingException(
                "Missing or null parameter 'rows' required for 'sample_sheet' collection types."
            )
        if len(dataset_instances) != len(rows):
            self._validation_failed("Supplied element do not match 'rows'.")

        for identifier, element in dataset_instances.items():
            columns = rows[identifier]
            validate_row(columns, column_definitions)
            association = DatasetCollectionElement(
                element=element,
                element_identifier=identifier,
                columns=columns,
            )
            yield association
