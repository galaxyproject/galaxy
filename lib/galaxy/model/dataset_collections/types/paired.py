from typing import (
    Iterable,
    TYPE_CHECKING,
)

from galaxy.model import (
    DatasetCollectionElement,
    HistoryDatasetAssociation,
)
from . import BaseDatasetCollectionType

if TYPE_CHECKING:
    from . import DatasetInstanceMapping

FORWARD_IDENTIFIER = "forward"
REVERSE_IDENTIFIER = "reverse"


class PairedDatasetCollectionType(BaseDatasetCollectionType):
    """
    Paired (left/right) datasets.
    """

    collection_type = "paired"

    def generate_elements(
        self, dataset_instances: "DatasetInstanceMapping", **kwds
    ) -> Iterable[DatasetCollectionElement]:
        if forward_dataset := dataset_instances.get(FORWARD_IDENTIFIER):
            left_association = DatasetCollectionElement(
                element=forward_dataset,
                element_identifier=FORWARD_IDENTIFIER,
            )
            yield left_association
        if reverse_dataset := dataset_instances.get(REVERSE_IDENTIFIER):
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
