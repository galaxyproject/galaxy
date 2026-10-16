"""Thin shim over galaxy.tool_util.collections.

Re-exports the core collection type description classes and adds back the
registry coupling (rank_type_plugin) that requires galaxy-data's model layer.
"""

from galaxy.tool_util.collections import (  # noqa: F401 — re-exports
    _normalize_collection_type,
    CollectionTypeDescription as _BaseCollectionTypeDescription,
    CollectionTypeDescriptionFactory as _BaseFactory,
    map_over_collection_type,
)
from .registry import DATASET_COLLECTION_TYPES_REGISTRY


class CollectionTypeDescriptionFactory(_BaseFactory):
    def __init__(self, type_registry=DATASET_COLLECTION_TYPES_REGISTRY):
        super().__init__(type_registry=type_registry)

    def for_collection_type(self, collection_type, fields=None):
        assert collection_type is not None
        return CollectionTypeDescription(collection_type, self, fields=fields)


class CollectionTypeDescription(_BaseCollectionTypeDescription):
    """Collection type description with registry-backed rank_type_plugin."""

    def rank_type_plugin(self):
        return self.collection_type_description_factory.type_registry.get(self.rank_collection_type())


COLLECTION_TYPE_DESCRIPTION_FACTORY = CollectionTypeDescriptionFactory()
