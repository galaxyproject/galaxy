from galaxy.model import DatasetCollectionElement, HistoryDatasetAssociation
from ..types import BaseDatasetCollectionType

FORWARD_IDENTIFIER = "forward"
REVERSE_IDENTIFIER = "reverse"

INVALID_IDENTIFIERS_MESSAGE = "Paired instance must define '%s' and '%s' datasets ." % (FORWARD_IDENTIFIER, REVERSE_IDENTIFIER)


class PairedDatasetCollectionType(BaseDatasetCollectionType):
    """
    Paired (left/right) datasets.
    """
    collection_type = "paired"

    def __init__(self):
        pass

    def generate_elements(self, elements):
        forward_dataset = elements.get(FORWARD_IDENTIFIER, None)
        reverse_dataset = elements.get(REVERSE_IDENTIFIER, None)
        if not forward_dataset or not reverse_dataset:
            self._validation_failed(INVALID_IDENTIFIERS_MESSAGE)
        left_association = DatasetCollectionElement(
            element=forward_dataset,
            element_identifier=FORWARD_IDENTIFIER,
        )
        right_association = DatasetCollectionElement(
            element=reverse_dataset,
            element_identifier=REVERSE_IDENTIFIER,
        )
        yield left_association
        yield right_association

    def prototype_elements(self):
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
