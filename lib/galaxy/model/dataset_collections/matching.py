from typing import Optional

from galaxy import exceptions
from galaxy.util import bunch
from .structure import (
    get_structure,
    leaf,
)

CANNOT_MATCH_ERROR_MESSAGE = "Cannot match collection types."


class CollectionsToMatch:
    """Structure representing a set of collections that need to be matched up
    when running tools (possibly workflows in the future as well).
    """

    def __init__(self):
        self.collections = {}

    def add(self, input_name, hdca, subcollection_type=None, linked=True):
        self.collections[input_name] = bunch.Bunch(
            hdca=hdca,
            subcollection_type=subcollection_type,
            linked=linked,
        )

    def has_collections(self):
        return len(self.collections) > 0

    def items(self):
        return self.collections.items()


class MatchingCollections:
    """Structure holding the result of matching a list of collections
    together. This class being different than the class above and being
    created in the DatasetCollectionManager layer may seem like
    overkill but I suspect in the future plugins will be subtypable for
    instance so matching collections will need to make heavy use of the
    dataset collection type registry managed by the dataset collections
    service - hence the complexity now.
    """

    def __init__(self):
        self.linked_structure = None
        self.unlinked_structures = []
        self.collections = {}
        self.subcollection_types = {}
        self.action_tuples = {}
        self.when_values = None

    def __attempt_add_to_linked_match(self, input_name, hdca, collection_type_description, subcollection_type):
        structure = get_structure(hdca, collection_type_description, leaf_subcollection_type=subcollection_type)
        if not self.linked_structure:
            self.linked_structure = structure
            self.collections[input_name] = hdca
            self.subcollection_types[input_name] = subcollection_type
        else:
            if not self.linked_structure.can_match(structure):
                raise exceptions.MessageException(CANNOT_MATCH_ERROR_MESSAGE)
            self.collections[input_name] = hdca
            self.subcollection_types[input_name] = subcollection_type

    def slice_collections(self):
        self.linked_structure.when_values = self.when_values
        return self.linked_structure.walk_collections(self.collections)

    def subcollection_mapping_type(self, input_name):
        return self.subcollection_types[input_name]

    @property
    def structure(self):
        """Yield cross product of all unlinked collections structures to linked collection structure."""
        effective_structure = leaf
        for unlinked_structure in self.unlinked_structures:
            effective_structure = effective_structure.multiply(unlinked_structure)
        linked_structure = self.linked_structure
        if linked_structure is None:
            linked_structure = leaf
        effective_structure = effective_structure.multiply(linked_structure)
        effective_structure.when_values = self.when_values
        return None if effective_structure.is_leaf else effective_structure

    def map_over_action_tuples(self, input_name):
        if input_name not in self.action_tuples:
            collection_instance = self.collections[input_name]
            self.action_tuples[input_name] = collection_instance.collection.dataset_action_tuples
        return self.action_tuples[input_name]

    def is_mapped_over(self, input_name):
        return input_name in self.collections

    @staticmethod
    def for_collections(collections_to_match, collection_type_descriptions) -> Optional["MatchingCollections"]:
        if not collections_to_match.has_collections():
            return None

        matching_collections = MatchingCollections()
        for input_key, to_match in sorted(collections_to_match.items()):
            hdca = to_match.hdca
            collection_type_description = collection_type_descriptions.for_collection_type(
                hdca.collection.collection_type
            )
            subcollection_type = to_match.subcollection_type

            if to_match.linked:
                matching_collections.__attempt_add_to_linked_match(
                    input_key, hdca, collection_type_description, subcollection_type
                )
            else:
                structure = get_structure(hdca, collection_type_description, leaf_subcollection_type=subcollection_type)
                matching_collections.unlinked_structures.append(structure)

        return matching_collections
