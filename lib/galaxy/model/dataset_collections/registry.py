from galaxy import model
from .types import (
    BaseDatasetCollectionType,
    paired,
    paired_or_unpaired,
    record,
    sample_sheet,
)
from .types.list import ListDatasetCollectionType

PLUGIN_CLASSES: list[type[BaseDatasetCollectionType]] = [
    ListDatasetCollectionType,
    paired.PairedDatasetCollectionType,
    record.RecordDatasetCollectionType,
    paired_or_unpaired.PairedOrUnpairedDatasetCollectionType,
    sample_sheet.SampleSheetDatasetCollectionType,
]


class DatasetCollectionTypesRegistry:
    def __init__(self):
        self.__plugins = {p.collection_type: p() for p in PLUGIN_CLASSES}

    def get(self, plugin_type):
        return self.__plugins[plugin_type]

    def prototype(self, plugin_type, fields=None):
        plugin_type_object = self.get(plugin_type)
        if not hasattr(plugin_type_object, "prototype_elements"):
            raise Exception(f"Cannot pre-determine structure for collection of type {plugin_type}")

        dataset_collection = model.DatasetCollection()
        for e in plugin_type_object.prototype_elements(fields=fields):
            e.collection = dataset_collection
        return dataset_collection


DATASET_COLLECTION_TYPES_REGISTRY = DatasetCollectionTypesRegistry()
