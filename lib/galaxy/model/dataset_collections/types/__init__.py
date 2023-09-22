import logging
from abc import (
    ABCMeta,
    abstractmethod,
)

from galaxy import exceptions

log = logging.getLogger(__name__)


class DatasetCollectionType(metaclass=ABCMeta):
    @abstractmethod
    def generate_elements(self, dataset_instances):
        """Generate DatasetCollectionElements with corresponding
        to the supplied dataset instances or throw exception if
        this is not a valid collection of the specified type.
        """


class BaseDatasetCollectionType(DatasetCollectionType):
    def _validation_failed(self, message):
        raise exceptions.ObjectAttributeInvalidException(message)
