from .types import list
from .types import paired


PLUGIN_CLASSES = [list.ListDatasetCollectionType, paired.PairedDatasetCollectionType]


class DatasetCollectionTypesRegistry(object):

    def __init__( self, app ):
        self.__plugins = dict( [ ( p.collection_type, p() ) for p in PLUGIN_CLASSES ] )

    def get( self, plugin_type ):
        return self.__plugins[ plugin_type ]
