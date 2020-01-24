import logging
from abc import (
    ABCMeta,
    abstractmethod
)

import six

from galaxy import exceptions

log = logging.getLogger(__name__)


@six.add_metaclass(ABCMeta)
class DatasetCollectionType(object):

    @abstractmethod
    def generate_elements(self, dataset_instances):
        """ Generate DatasetCollectionElements with corresponding
        to the supplied dataset instances or throw exception if
        this is not a valid collection of the specified type.
        """


class BaseDatasetCollectionType(DatasetCollectionType):

    def _validation_failed(self, message):
        raise exceptions.ObjectAttributeInvalidException(message)
