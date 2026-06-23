from collections.abc import Iterable
from typing import (
    TYPE_CHECKING,
)

from galaxy.model import DatasetCollectionElement
from . import BaseDatasetCollectionType

if TYPE_CHECKING:
    from . import DatasetInstanceMapping


class ListDatasetCollectionType(BaseDatasetCollectionType):
    """A flat list of named elements."""

    collection_type = "list"

    def generate_elements(
        self, dataset_instances: "DatasetInstanceMapping", **kwds
    ) -> Iterable[DatasetCollectionElement]:
        for identifier, element in dataset_instances.items():
            association = DatasetCollectionElement(
                element=element,
                element_identifier=identifier,
            )
            yield association
