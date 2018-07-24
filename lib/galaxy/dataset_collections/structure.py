""" Module for reasoning about structure of and matching hierarchical collections of data.
"""
import logging

import six

log = logging.getLogger(__name__)


@six.python_2_unicode_compatible
class Leaf(object):
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


class BaseTree(object):

    def __init__(self, collection_type_description):
        self.collection_type_description = collection_type_description


@six.python_2_unicode_compatible
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
        return "UninitializedTree[collection_type=%s]" % self.collection_type_description


@six.python_2_unicode_compatible
class Tree(BaseTree):
    children_known = True

    def __init__(self, children, collection_type_description):
        super(Tree, self).__init__(collection_type_description)
        self.children = children

    @staticmethod
    def for_dataset_collection(dataset_collection, collection_type_description):
        children = []
        for element in dataset_collection.elements:
            if collection_type_description.has_subcollections():
                child_collection = element.child_collection
                subcollection_type_description = collection_type_description.subcollection_type_description()  # Type description of children
                tree = Tree.for_dataset_collection(child_collection, collection_type_description=subcollection_type_description)
                children.append((element.element_identifier, tree))
            else:
                children.append((element.element_identifier, leaf))
        return Tree(children, collection_type_description)

    def walk_collections(self, hdca_dict):
        return self._walk_collections(dict_map(lambda hdca: hdca.collection, hdca_dict))

    def _walk_collections(self, collection_dict):
        for index, (identifier, substructure) in enumerate(self.children):
            def element(collection):
                return collection[index]

            if substructure.is_leaf:
                yield dict_map(element, collection_dict)
            else:
                sub_collections = dict_map(lambda collection: element(collection).child_collection, collection_dict)
                for element in substructure._walk_collections(sub_collections):
                    yield element

    @property
    def is_leaf(self):
        return False

    def can_match(self, other_structure):
        if not self.collection_type_description.can_match_type(other_structure.collection_type_description):
            return False

        if len(self.children) != len(other_structure.children):
            return False

        for my_child, other_child in zip(self.children, other_structure.children):
            # At least one is nested collection...
            if my_child[1].is_leaf != other_child[1].is_leaf:
                return False

            if not my_child[1].is_leaf and not my_child[1].can_match(other_child[1]):
                return False

        return True

    def __len__(self):
        return sum([len(c[1]) for c in self.children])

    def multiply(self, other_structure):
        if other_structure.is_leaf:
            return self.clone()

        new_collection_type = self.collection_type_description.multiply(other_structure.collection_type_description)
        new_children = []
        for (identifier, structure) in self.children:
            new_children.append((identifier, structure.multiply(other_structure)))

        return Tree(new_children, new_collection_type)

    def clone(self):
        cloned_children = [(_[0], _[1].clone()) for _ in self.children]
        return Tree(cloned_children, self.collection_type_description)

    def __str__(self):
        return "Tree[collection_type=%s,children=%s]" % (self.collection_type_description, ",".join(map(lambda identifier_and_element: "%s=%s" % (identifier_and_element[0], identifier_and_element[1]), self.children)))


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
                collection_type = get_sliced_input_collection_structure(tool_output.structure.collection_type_source).collection_type_description.collection_type

            if not collection_type:
                raise Exception("Failed to determine collection type for mapping over output %s" % tool_output.name)

            tree = UninitializedTree(collection_type_descriptions.for_collection_type(collection_type))

    if not tree.children_known and tree.collection_type_description.collection_type == "paired":
        # TODO: We don't need to return UninitializedTree for pairs I think, we should build
        # a paired tree for the known structure here.
        pass
    return tree


def dict_map(func, input_dict):
    return dict((k, func(v)) for k, v in input_dict.items())


def get_structure(dataset_collection_instance, collection_type_description, leaf_subcollection_type=None):
    if leaf_subcollection_type:
        collection_type_description = collection_type_description.effective_collection_type_description(leaf_subcollection_type)
        if hasattr(dataset_collection_instance, 'child_collection'):
            collection_type_description = collection_type_description.collection_type_description_factory.for_collection_type(leaf_subcollection_type)
            return UninitializedTree(collection_type_description)

    collection = dataset_collection_instance.collection
    return Tree.for_dataset_collection(collection, collection_type_description)
