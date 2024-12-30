from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model import DatasetCollectionElement
from . import BaseDatasetCollectionType
from .paired import (
    FORWARD_IDENTIFIER,
    REVERSE_IDENTIFIER,
)

SINGLETON_IDENTIFIER = "unpaired"


class PairedOrUnpairedDatasetCollectionType(BaseDatasetCollectionType):
    """ """

    collection_type = "paired_or_unpaired"

    def generate_elements(self, dataset_instances, **kwds):
        num_datasets = len(dataset_instances)
        if num_datasets > 2 or num_datasets < 1:
            raise RequestParameterInvalidException(
                "Incorrect number of datasets - 1 or 2 datasets is required to create a paired_or_unpaired collection"
            )

        if num_datasets == 2:
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
        else:
            if single_datasets := self._ensure_dataset_with_identifier(dataset_instances, SINGLETON_IDENTIFIER):
                single_association = DatasetCollectionElement(
                    element=single_datasets,
                    element_identifier=SINGLETON_IDENTIFIER,
                )
                yield single_association
