"""Module for reasoning about structure of and matching hierarchical collections of data."""

from typing import (
    Optional,
    TYPE_CHECKING,
    Union,
)

from galaxy.model import DatasetCollectionElement

if TYPE_CHECKING:
    from galaxy.model import (
        DatasetCollection,
        HistoryDatasetCollectionAssociation,
    )
    from .type_description import CollectionTypeDescription

    CollectionLike = Union[DatasetCollectionElement, "HistoryDatasetCollectionAssociation"]


class Leaf:
    children_known = True

    def __len__(self):
        return 1

    @property
    def is_leaf(self):
        return True

    def clone(self):
        return self

    def multiply(self, other_structure):
        return other_structure.clone()

    def sliced_collection_type(self, collection):
        return input

    def __str__(self):
        return "Leaf[]"


leaf = Leaf()


class BaseTree:
    def __init__(self, collection_type_description):
        self.collection_type_description = collection_type_description


class UninitializedTree(BaseTree):
    children_known = False

    def clone(self):
        return self

    @property
    def is_leaf(self):
        return False

    def __len__(self):
        raise Exception("Unknown length")

    def multiply(self, other_structure):
        if other_structure.is_leaf:
            return self.clone()

        new_collection_type = self.collection_type_description.multiply(other_structure.collection_type_description)
        return UninitializedTree(new_collection_type)

    def __str__(self):
        return f"UninitializedTree[collection_type={self.collection_type_description}]"


class Tree(BaseTree):
    children_known = True

    def __init__(
        self, children, collection_type_description, when_values=None, columns_metadata=None, column_definitions=None
    ):
        super().__init__(collection_type_description)
        self.children = children
        self.when_values = when_values
        # columns_metadata is a dict mapping element_identifier to columns data
        self.columns_metadata = columns_metadata or {}
        self.column_definitions = column_definitions

    @staticmethod
    def for_dataset_collection(dataset_collection, collection_type_description):
        children = []
        columns_metadata = {}
        for element in dataset_collection.elements:
            if collection_type_description.has_subcollections():
                child_collection = element.child_collection
                subcollection_type_description = (
                    collection_type_description.subcollection_type_description()
                )  # Type description of children
                tree = Tree.for_dataset_collection(
                    child_collection, collection_type_description=subcollection_type_description
                )
                children.append((element.element_identifier, tree))
            else:
                children.append((element.element_identifier, leaf))
            # Capture columns metadata from sample sheet collections
            if element.columns is not None:
                columns_metadata[element.element_identifier] = element.columns
        return Tree(
            children,
            collection_type_description,
            columns_metadata=columns_metadata,
            column_definitions=dataset_collection.column_definitions,
        )

    def walk_collections(self, collection_dict):
        return self._walk_collections(collection_dict)

    def _walk_collections(self, collection_dict):
        for index, (_identifier, substructure) in enumerate(self.children):

            def get_element(collection):
                return collection[index]  # noqa: B023

            when_value = None
            if self.when_values:
                if len(self.when_values) == 1:
                    when_value = self.when_values[0]
                else:
                    when_value = self.when_values[index]

            if substructure.is_leaf:
                yield dict_map(get_element, collection_dict), when_value
            else:
                sub_collections = dict_map(lambda collection: get_element(collection).child_collection, collection_dict)
                for element, _when_value in substructure._walk_collections(sub_collections):
                    yield element, when_value

    @property
    def is_leaf(self):
        return False

    def compatible_shape(self, other_structure):
        """Symmetric sibling-matching check.

        Both sides have already passed connection-time edge validation;
        here we only compare shape. Uses ``compatible`` (not ``accepts``)
        so order of arrival does not change the answer.
        """
        if not self.collection_type_description.compatible(other_structure.collection_type_description):
            return False

        if len(self.children) != len(other_structure.children):
            return False

        for my_child, other_child in zip(self.children, other_structure.children):
            # At least one is nested collection...
            if my_child[1].is_leaf != other_child[1].is_leaf:
                return False

            if not my_child[1].is_leaf and not my_child[1].compatible_shape(other_child[1]):
                return False

        return True

    def __len__(self):
        return sum(len(c[1]) for c in self.children)

    def multiply(self, other_structure):
        if other_structure.is_leaf:
            return self.clone()

        new_collection_type = self.collection_type_description.multiply(other_structure.collection_type_description)
        new_children = []
        for identifier, structure in self.children:
            new_children.append((identifier, structure.multiply(other_structure)))

        # Preserve columns_metadata and column_definitions when multiplying
        return Tree(
            new_children,
            new_collection_type,
            columns_metadata=self.columns_metadata.copy(),
            column_definitions=self.column_definitions,
        )

    def clone(self):
        cloned_children = [(_[0], _[1].clone()) for _ in self.children]
        return Tree(
            cloned_children,
            self.collection_type_description,
            columns_metadata=self.columns_metadata.copy(),
            column_definitions=self.column_definitions,
        )

    def __str__(self):
        return f"Tree[collection_type={self.collection_type_description},children=({','.join(f'{identifier_and_element[0]}={identifier_and_element[1]}' for identifier_and_element in self.children)})]"


def tool_output_to_structure(get_sliced_input_collection_structure, tool_output, collections_manager):
    if not tool_output.collection:
        tree = leaf
    else:
        collection_type_descriptions = collections_manager.collection_type_descriptions
        # Okay this is ToolCollectionOutputStructure not a Structure - different
        # concepts of structure.
        structured_like = tool_output.structure.structured_like
        collection_type = tool_output.structure.collection_type
        if structured_like:
            tree = get_sliced_input_collection_structure(structured_like)
            if collection_type and tree.collection_type_description.collection_type != collection_type:
                # See tool paired_collection_map_over_structured_like - type should
                # override structured_like if they disagree.
                tree = UninitializedTree(collection_type_descriptions.for_collection_type(collection_type))
        else:
            # Can't pre-compute the structure in this case, see if we can find a collection type.
            if collection_type is None and tool_output.structure.collection_type_source:
                collection_type = get_sliced_input_collection_structure(
                    tool_output.structure.collection_type_source
                ).collection_type_description.collection_type

            if not collection_type:
                raise Exception(f"Failed to determine collection type for mapping over output {tool_output.name}")

            tree = UninitializedTree(collection_type_descriptions.for_collection_type(collection_type))

    if not tree.children_known and tree.collection_type_description.collection_type == "paired":
        # TODO: We don't need to return UninitializedTree for pairs I think, we should build
        # a paired tree for the known structure here.
        pass
    return tree


def dict_map(func, input_dict):
    return {k: func(v) for k, v in input_dict.items()}


def get_collection(
    dataset_collection_instance: "CollectionLike",
) -> "DatasetCollection":
    """Return the DatasetCollection contained by a collection instance.

    A DatasetCollectionElement has two collection references:
      - ``collection``: the **parent** collection this element belongs to
      - ``child_collection``: the nested collection this element *contains*

    An HDCA has one:
      - ``collection``: the collection it wraps

    This helper returns the *contained* collection in both cases
    (child_collection for DCE, collection for HDCA/adapters) and is
    intended for callers that still hold a wrapper object and need a
    DatasetCollection to pass to ``get_structure`` or ``walk_collections``.
    """
    if (
        isinstance(dataset_collection_instance, DatasetCollectionElement)
        and dataset_collection_instance.child_collection
    ):
        return dataset_collection_instance.child_collection
    return dataset_collection_instance.collection


def get_structure(
    collection: "DatasetCollection",
    collection_type_description: "CollectionTypeDescription",
    leaf_subcollection_type: Optional[str] = None,
):
    """Build a Tree (or UninitializedTree) describing a collection's shape.

    ``collection_type_description`` controls the depth of the tree:
    elements below ``leaf_subcollection_type`` are treated as leaves.
    """
    if leaf_subcollection_type:
        if not collection_type_description.has_subcollections_of_type(leaf_subcollection_type):
            # The described collection IS the leaf subcollection (no deeper
            # structure to strip). Don't enumerate its elements; just record
            # the type so multiply() can combine it with the mapping structure.
            return UninitializedTree(
                collection_type_description.collection_type_description_factory.for_collection_type(
                    leaf_subcollection_type
                )
            )
        # Strip the leaf type from the description so it becomes a leaf
        # in the resulting tree. E.g. "list:paired" with
        # leaf_subcollection_type="paired" → description becomes "list".
        collection_type_description = collection_type_description.effective_collection_type_description(
            leaf_subcollection_type
        )
    return Tree.for_dataset_collection(collection, collection_type_description)
