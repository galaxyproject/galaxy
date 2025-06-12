import logging
from abc import (
    ABCMeta,
    abstractmethod,
)
from typing import (
    Iterable,
    Mapping,
    TYPE_CHECKING,
    Union,
)

from galaxy import exceptions

if TYPE_CHECKING:
    from galaxy.model import (
        DatasetCollection,
        DatasetCollectionElement,
        DatasetInstance,
    )

log = logging.getLogger(__name__)

DatasetInstanceMapping = Mapping[str, Union["DatasetCollection", "DatasetInstance"]]


class BaseDatasetCollectionType(metaclass=ABCMeta):
    collection_type: str

    @abstractmethod
    def generate_elements(
        self, dataset_instances: DatasetInstanceMapping, **kwds
    ) -> Iterable["DatasetCollectionElement"]:
        """Generate DatasetCollectionElements with corresponding
        to the supplied dataset instances or throw exception if
        this is not a valid collection of the specified type.
        """

    def _validation_failed(self, message):
        raise exceptions.ObjectAttributeInvalidException(message)
