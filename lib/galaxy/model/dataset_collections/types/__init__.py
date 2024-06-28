import logging
from abc import (
    ABCMeta,
    abstractmethod,
)
from typing import TYPE_CHECKING

from galaxy import exceptions

if TYPE_CHECKING:
    from galaxy.model import DatasetCollectionElement
    from galaxy.model.dataset_collections.builder import Elements

log = logging.getLogger(__name__)


class DatasetCollectionType(metaclass=ABCMeta):
    @abstractmethod
    def generate_elements(self, dataset_instances: "Elements") -> list["DatasetCollectionElement"]:
        """Generate DatasetCollectionElements with corresponding
        to the supplied dataset instances or throw exception if
        this is not a valid collection of the specified type.
        """


class BaseDatasetCollectionType(DatasetCollectionType):

    collection_type: str

    def _validation_failed(self, message):
        raise exceptions.ObjectAttributeInvalidException(message)
