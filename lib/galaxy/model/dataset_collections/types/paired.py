from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model import (
    DatasetCollectionElement,
    HistoryDatasetAssociation,
)
from . import BaseDatasetCollectionType

FORWARD_IDENTIFIER = "forward"
REVERSE_IDENTIFIER = "reverse"


class PairedDatasetCollectionType(BaseDatasetCollectionType):
    """
    Paired (left/right) datasets.
    """

    collection_type = "paired"

    def generate_elements(self, dataset_instances, **kwds):
        num_datasets = len(dataset_instances)
        if num_datasets != 2:
            raise RequestParameterInvalidException(
                "Incorrect number of datasets - 2 datasets exactly are required to create a paired collection"
            )

        if forward_dataset := self._ensure_dataset_with_identifier(dataset_instances, FORWARD_IDENTIFIER):
            left_association = DatasetCollectionElement(
                element=forward_dataset,
                element_identifier=FORWARD_IDENTIFIER,
            )
            yield left_association
        if reverse_dataset := self._ensure_dataset_with_identifier(dataset_instances, REVERSE_IDENTIFIER):
            right_association = DatasetCollectionElement(
                element=reverse_dataset,
                element_identifier=REVERSE_IDENTIFIER,
            )
            yield right_association

    def prototype_elements(self, **kwds):
        left_association = DatasetCollectionElement(
            element=HistoryDatasetAssociation(),
            element_identifier=FORWARD_IDENTIFIER,
        )
        right_association = DatasetCollectionElement(
            element=HistoryDatasetAssociation(),
            element_identifier=REVERSE_IDENTIFIER,
        )
        yield left_association
        yield right_association
