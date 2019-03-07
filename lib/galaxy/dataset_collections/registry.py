from galaxy import model
from .types import (
    list,
    paired
)

PLUGIN_CLASSES = [list.ListDatasetCollectionType, paired.PairedDatasetCollectionType]


class DatasetCollectionTypesRegistry(object):

    def __init__(self, app):
        self.__plugins = dict([(p.collection_type, p()) for p in PLUGIN_CLASSES])

    def get(self, plugin_type):
        return self.__plugins[plugin_type]

    def prototype(self, plugin_type):
        plugin_type_object = self.get(plugin_type)
        if not hasattr(plugin_type_object, 'prototype_elements'):
            raise Exception("Cannot pre-determine structure for collection of type %s" % plugin_type)

        dataset_collection = model.DatasetCollection()
        elements = [e for e in plugin_type_object.prototype_elements()]
        dataset_collection.elements = elements
        return dataset_collection
