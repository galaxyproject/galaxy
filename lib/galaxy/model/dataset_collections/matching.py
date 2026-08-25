from typing import Optional

from galaxy import exceptions
from galaxy.model import (
    DatasetCollectionElement,
    HistoryDatasetCollectionAssociation,
)
from galaxy.util import bunch
from .structure import (
    get_collection,
    get_structure,
    leaf,
)

CANNOT_MATCH_ERROR_MESSAGE = "Cannot match collection types."


def _dataset_collection_key(dataset_collection) -> tuple[str, int]:
    collection_id = getattr(dataset_collection, "id", None)
    if collection_id is not None:
        return ("id", collection_id)
    return ("object", id(dataset_collection))


def mapped_collection_provenance(collection_instance) -> set[tuple[str, int]]:
    """Return the identities of the collections this instance was mapped from.

    Includes the collection itself, whatever it was copied from, and the inputs
    of any implicit collection creation that produced it. Implicit collections
    have the same element identifiers in the same order as the collections
    mapped over to create them, so two instances sharing an identity here can be
    matched up element by element.
    """
    provenance = set()
    pending = [collection_instance]
    visited = set()
    while pending:
        current = pending.pop()
        current_object_id = id(current)
        if current_object_id in visited:
            continue
        visited.add(current_object_id)

        adapting = getattr(current, "adapting", None)
        if adapting is not None:
            pending.append(adapting)

        if isinstance(current, DatasetCollectionElement):
            # Matching a DCE operates on its contained child collection. The
            # parent records where the element lives, not what is mapped over.
            if current.child_collection is not None:
                provenance.add(_dataset_collection_key(current.child_collection))
        elif isinstance(current, HistoryDatasetCollectionAssociation):
            if current.collection is not None:
                provenance.add(_dataset_collection_key(current.collection))
            copied_from = current.copied_from_history_dataset_collection_association
            if copied_from is not None:
                pending.append(copied_from)
            pending.extend(
                implicit_input.input_dataset_collection
                for implicit_input in current.implicit_input_collections
                if implicit_input.input_dataset_collection is not None
            )
        elif (collection := getattr(current, "collection", None)) is not None:
            provenance.add(_dataset_collection_key(collection))

    return provenance


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

    def __attempt_add_to_linked_match(
        self, input_name, hdca, child_collection, collection_type_description, subcollection_type
    ):
        structure = get_structure(
            child_collection, collection_type_description, leaf_subcollection_type=subcollection_type
        )
        if not self.linked_structure:
            self.linked_structure = structure
            self.collections[input_name] = hdca
            self.subcollection_types[input_name] = subcollection_type
        else:
            if not self.linked_structure.compatible_shape(structure):
                raise exceptions.MessageException(CANNOT_MATCH_ERROR_MESSAGE)
            self.collections[input_name] = hdca
            self.subcollection_types[input_name] = subcollection_type

    def slice_collections(self):
        self.linked_structure.when_values = self.when_values
        return self.linked_structure.walk_collections({k: get_collection(v) for k, v in self.collections.items()})

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
            self.action_tuples[input_name] = get_collection(collection_instance).dataset_action_tuples
        return self.action_tuples[input_name]

    def is_mapped_over(self, input_name):
        return input_name in self.collections

    def is_aligned_with(self, other: "MatchingCollections") -> bool:
        """Whether these collections match ``other`` element by element.

        True when the two matches share a collection they were mapped from,
        which means the same element identifiers in the same order. Only linked
        collections are considered - they share one structure and have already
        passed ``compatible_shape``, so a match on any one of them holds for all
        of them. Callers use this before moving positionally indexed state such
        as ``when_values`` from one match to the other.
        """
        other_provenance = set().union(
            *(mapped_collection_provenance(collection) for collection in other.collections.values())
        )
        return any(
            other_provenance.intersection(mapped_collection_provenance(collection))
            for collection in self.collections.values()
        )

    @staticmethod
    def for_collections(collections_to_match, collection_type_descriptions) -> Optional["MatchingCollections"]:
        if not collections_to_match.has_collections():
            return None

        matching_collections = MatchingCollections()
        for input_key, to_match in sorted(collections_to_match.items()):
            hdca = to_match.hdca
            # Resolve the contained collection: for an HDCA this is
            # hdca.collection; for a DCE it is dce.child_collection
            # (not dce.collection which is the *parent*).
            # Both collection_type_description and get_structure must
            # use the same collection so the type and elements agree.
            child_collection = get_collection(hdca)
            collection_type_description = collection_type_descriptions.for_collection_type(
                child_collection.collection_type
            )
            subcollection_type = to_match.subcollection_type

            if to_match.linked:
                matching_collections.__attempt_add_to_linked_match(
                    input_key, hdca, child_collection, collection_type_description, subcollection_type
                )
            else:
                structure = get_structure(
                    child_collection,
                    collection_type_description,
                    leaf_subcollection_type=subcollection_type,
                )
                matching_collections.unlinked_structures.append(structure)

        return matching_collections
