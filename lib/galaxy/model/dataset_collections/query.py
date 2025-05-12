import logging
from typing import (
    List,
    Optional,
)

from typing_extensions import Protocol

log = logging.getLogger(__name__)


# protocols for things that look like Galaxy model HDCAs and collections for this module
class CollectionLike(Protocol):
    collection_type: str


class HdcaLike(Protocol):
    collection: CollectionLike


class DataCollectionParameterLike(Protocol):

    @property
    def collection_types(self) -> Optional[List[str]]:
        """Return a list of collection type strings the parameter accepts."""


class HistoryQuery:
    """An object for describing the collections to pull out of a history,
    used by DataCollectionToolParameter.
    """

    def __init__(self, **kwargs):
        self.collection_type_descriptions = kwargs.get("collection_type_descriptions", None)

    @staticmethod
    def from_collection_type(collection_type, collection_type_descriptions):
        kwargs = dict(collection_type_descriptions=[collection_type_descriptions.for_collection_type(collection_type)])
        return HistoryQuery(**kwargs)

    @staticmethod
    def from_collection_types(collection_types: Optional[List[str]], collection_type_descriptions):
        if collection_types:
            collection_type_descriptions = [
                collection_type_descriptions.for_collection_type(t) for t in collection_types
            ]
            # Place higher dimension descriptions first so subcollection mapping
            # (until we expose it to the user) will default to providing tool as much
            # data as possible. So a list:list:paired mapped to a tool that takes
            # list,paired,list:paired - will map over list:paired and create a flat list.
            collection_type_descriptions = sorted(collection_type_descriptions, key=lambda t: t.dimension, reverse=True)
        else:
            collection_type_descriptions = None
        kwargs = dict(collection_type_descriptions=collection_type_descriptions)
        return HistoryQuery(**kwargs)

    @staticmethod
    def from_parameter(param: DataCollectionParameterLike, collection_type_descriptions):
        """Take in a tool parameter element."""
        collection_types = param.collection_types
        return HistoryQuery.from_collection_types(collection_types, collection_type_descriptions)

    def direct_match(self, hdca: HdcaLike) -> bool:
        collection_type_descriptions = self.collection_type_descriptions
        if collection_type_descriptions is not None:
            for collection_type_description in collection_type_descriptions:
                matches = collection_type_description.can_match_type(hdca.collection.collection_type)
                if matches:
                    return True
            return False

        return True

    def can_map_over(self, hdca: HdcaLike):
        collection_type_descriptions = self.collection_type_descriptions
        if collection_type_descriptions is None:
            return False

        hdca_collection_type = hdca.collection.collection_type
        for collection_type_description in collection_type_descriptions:
            # See note about the way this is sorted above.
            if collection_type_description.is_subcollection_of_type(hdca_collection_type):
                return collection_type_description
        return False
