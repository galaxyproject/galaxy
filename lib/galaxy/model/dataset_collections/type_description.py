from typing import Union

from .registry import DATASET_COLLECTION_TYPES_REGISTRY


class CollectionTypeDescriptionFactory:
    def __init__(self, type_registry=DATASET_COLLECTION_TYPES_REGISTRY):
        # taking in type_registry though not using it, because we will someday
        # I think.
        self.type_registry = type_registry

    def for_collection_type(self, collection_type):
        assert collection_type is not None
        return CollectionTypeDescription(collection_type, self)


class CollectionTypeDescription:
    """Abstraction over dataset collection type that ties together string
    reprentation in database/model with type registry.

    >>> factory = CollectionTypeDescriptionFactory(None)
    >>> nested_type_description = factory.for_collection_type("list:paired")
    >>> paired_type_description = factory.for_collection_type("paired")
    >>> nested_type_description.has_subcollections_of_type("list")
    False
    >>> nested_type_description.has_subcollections_of_type("list:paired")
    False
    >>> nested_type_description.has_subcollections_of_type("paired")
    True
    >>> nested_type_description.has_subcollections_of_type(paired_type_description)
    True
    >>> nested_type_description.has_subcollections()
    True
    >>> paired_type_description.has_subcollections()
    False
    >>> paired_type_description.rank_collection_type()
    'paired'
    >>> nested_type_description.rank_collection_type()
    'list'
    >>> nested_type_description.effective_collection_type(paired_type_description)
    'list'
    >>> nested_type_description.effective_collection_type_description(paired_type_description).collection_type
    'list'
    >>> nested_type_description.child_collection_type()
    'paired'
    """

    collection_type: str

    def __init__(self, collection_type: Union[str, "CollectionTypeDescription"], collection_type_description_factory):
        if isinstance(collection_type, CollectionTypeDescription):
            self.collection_type = collection_type.collection_type
        else:
            self.collection_type = collection_type
        self.collection_type_description_factory = collection_type_description_factory
        self.__has_subcollections = self.collection_type.find(":") > 0

    def child_collection_type(self):
        rank_collection_type = self.rank_collection_type()
        return self.collection_type[len(rank_collection_type) + 1 :]

    def child_collection_type_description(self):
        child_collection_type = self.child_collection_type()
        return self.collection_type_description_factory.for_collection_type(child_collection_type)

    def effective_collection_type_description(self, subcollection_type):
        effective_collection_type = self.effective_collection_type(subcollection_type)
        return self.collection_type_description_factory.for_collection_type(effective_collection_type)

    def effective_collection_type(self, subcollection_type):
        if hasattr(subcollection_type, "collection_type"):
            subcollection_type = subcollection_type.collection_type

        if not self.has_subcollections_of_type(subcollection_type):
            raise ValueError(f"Cannot compute effective subcollection type of {subcollection_type} over {self}")

        return self.collection_type[: -(len(subcollection_type) + 1)]

    def has_subcollections_of_type(self, other_collection_type):
        """Take in another type (either flat string or another
        CollectionTypeDescription) and determine if this collection contains
        subcollections matching that type.

        The way this is used in map/reduce it seems to make the most sense
        for this to return True if these subtypes are proper (i.e. a type
        is not considered to have subcollections of its own type).
        """
        if hasattr(other_collection_type, "collection_type"):
            other_collection_type = other_collection_type.collection_type
        collection_type = self.collection_type
        return collection_type.endswith(other_collection_type) and collection_type != other_collection_type

    def is_subcollection_of_type(self, other_collection_type):
        if not hasattr(other_collection_type, "collection_type"):
            other_collection_type = self.collection_type_description_factory.for_collection_type(other_collection_type)
        return other_collection_type.has_subcollections_of_type(self)

    def can_match_type(self, other_collection_type):
        if hasattr(other_collection_type, "collection_type"):
            other_collection_type = other_collection_type.collection_type
        collection_type = self.collection_type
        return other_collection_type == collection_type

    def subcollection_type_description(self):
        if not self.__has_subcollections:
            raise ValueError(f"Cannot generate subcollection type description for flat type {self.collection_type}")
        subcollection_type = self.collection_type.split(":", 1)[1]
        return self.collection_type_description_factory.for_collection_type(subcollection_type)

    def has_subcollections(self):
        return self.__has_subcollections

    def rank_collection_type(self):
        """Return the top-level collection type corresponding to this
        collection type. For instance the "rank" type of a list of paired
        data ("list:paired") is "list".
        """
        return self.collection_type.split(":")[0]

    def rank_type_plugin(self):
        return self.collection_type_description_factory.type_registry.get(self.rank_collection_type())

    @property
    def dimension(self):
        return len(self.collection_type.split(":")) + 1

    def multiply(self, other_collection_type):
        collection_type = map_over_collection_type(self, other_collection_type)
        return self.collection_type_description_factory.for_collection_type(collection_type)

    def __str__(self):
        return f"CollectionTypeDescription[{self.collection_type}]"


def map_over_collection_type(mapped_over_collection_type, target_collection_type):
    if hasattr(mapped_over_collection_type, "collection_type"):
        mapped_over_collection_type = mapped_over_collection_type.collection_type

    if not target_collection_type:
        return mapped_over_collection_type
    else:
        if hasattr(target_collection_type, "collection_type"):
            target_collection_type = target_collection_type.collection_type

        return f"{mapped_over_collection_type}:{target_collection_type}"


COLLECTION_TYPE_DESCRIPTION_FACTORY = CollectionTypeDescriptionFactory()
