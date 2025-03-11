import logging
from abc import (
    ABCMeta,
    abstractmethod,
)

from galaxy import exceptions

log = logging.getLogger(__name__)


class DatasetCollectionType(metaclass=ABCMeta):
    @abstractmethod
    def generate_elements(self, dataset_instances: dict, **kwds):
        """Generate DatasetCollectionElements with corresponding
        to the supplied dataset instances or throw exception if
        this is not a valid collection of the specified type.
        """


class BaseDatasetCollectionType(DatasetCollectionType):
    def _validation_failed(self, message):
        raise exceptions.ObjectAttributeInvalidException(message)

    def _ensure_dataset_with_identifier(self, dataset_instances: dict, name: str):
        dataset_instance = dataset_instances.get(name)
        if dataset_instance is None:
            raise exceptions.ObjectAttributeInvalidException(
                f"An element with the identifier {name} is required to create this collection type"
            )
        return dataset_instance
