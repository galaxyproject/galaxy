from galaxy import model
from .types import (
    list,
    paired,
)

PLUGIN_CLASSES = [list.ListDatasetCollectionType, paired.PairedDatasetCollectionType]


class DatasetCollectionTypesRegistry:
    def __init__(self):
        self.__plugins = {p.collection_type: p() for p in PLUGIN_CLASSES}

    def get(self, plugin_type):
        return self.__plugins[plugin_type]

    def prototype(self, plugin_type):
        plugin_type_object = self.get(plugin_type)
        if not hasattr(plugin_type_object, "prototype_elements"):
            raise Exception(f"Cannot pre-determine structure for collection of type {plugin_type}")

        dataset_collection = model.DatasetCollection()
        for e in plugin_type_object.prototype_elements():
            e.collection = dataset_collection
        return dataset_collection


DATASET_COLLECTION_TYPES_REGISTRY = DatasetCollectionTypesRegistry()
