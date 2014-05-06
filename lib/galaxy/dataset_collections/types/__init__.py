from galaxy import exceptions
from abc import ABCMeta
from abc import abstractmethod

from galaxy import model

import logging
log = logging.getLogger( __name__ )


class DatasetCollectionType(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def build_collection( self, dataset_instances ):
        """
        Build DatasetCollection with populated DatasetcollectionElement objects
        corresponding to the supplied dataset instances or throw exception if
        this is not a valid collection of the specified type.
        """


class BaseDatasetCollectionType( DatasetCollectionType ):

    def _validation_failed( self, message ):
        raise exceptions.ObjectAttributeInvalidException( message )

    def _new_collection_for_elements( self, elements ):
        dataset_collection = model.DatasetCollection( )
        for index, element in enumerate( elements ):
            element.element_index = index
            element.collection = dataset_collection
        dataset_collection.elements = elements
        return dataset_collection
