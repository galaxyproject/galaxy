from galaxy.exceptions import RequestParameterMissingException
from galaxy.model import (
    DatasetCollectionElement,
    HistoryDatasetAssociation,
)
from ..types import BaseDatasetCollectionType


class RecordDatasetCollectionType(BaseDatasetCollectionType):
    """Arbitrary CWL-style record type."""

    collection_type = "record"

    def generate_elements(self, dataset_instances, **kwds):
        fields = kwds.get("fields", None)
        if fields is None:
            raise RequestParameterMissingException("Missing or null parameter 'fields' required for record types.")
        if len(dataset_instances) != len(fields):
            self._validation_failed("Supplied element do not match fields.")
        index = 0
        for identifier, element in dataset_instances.items():
            field = fields[index]
            if field["name"] != identifier:
                self._validation_failed("Supplied element do not match fields.")

            # TODO: validate type and such.
            association = DatasetCollectionElement(
                element=element,
                element_identifier=identifier,
            )
            yield association
            index += 1

    def prototype_elements(self, fields=None, **kwds):
        if fields is None:
            raise RequestParameterMissingException("Missing or null parameter 'fields' required for record types.")
        for field in fields:
            name = field.get("name", None)
            assert name
            assert field.get("type", "File")  # NS: this assert doesn't make sense as it is
            field_dataset = DatasetCollectionElement(
                element=HistoryDatasetAssociation(),
                element_identifier=name,
            )
            yield field_dataset
