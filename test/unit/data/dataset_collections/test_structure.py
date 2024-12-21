from galaxy.model.dataset_collections.structure import get_structure
from galaxy.model.dataset_collections.type_description import CollectionTypeDescriptionFactory
from .test_matching import (
    list_of_lists_instance,
    list_paired_instance,
    pair_instance,
)

factory = CollectionTypeDescriptionFactory(None)


def test_get_structure_simple():
    paired_type_description = factory.for_collection_type("paired")
    tree = get_structure(pair_instance(), paired_type_description)
    assert len(tree.children) == 2
    assert tree.children[0][0] == "left"  # why not forward?
    assert tree.children[0][1].is_leaf


def test_get_structure_list_paired_over_paired():
    paired_type_description = factory.for_collection_type("list:paired")
    tree = get_structure(list_paired_instance(), paired_type_description, "paired")
    assert tree.collection_type_description.collection_type == "list"
    assert len(tree.children) == 3
    assert tree.children[0][0] == "data1"
    assert tree.children[0][1].is_leaf

def test_get_structure_list_of_lists():
    list_of_lists_type_description = factory.for_collection_type("list:list")
    tree = get_structure(list_of_lists_instance(), list_of_lists_type_description)
    assert tree.collection_type_description.collection_type == "list:list"
    assert len(tree.children) == 2
    assert tree.children[0][0] == "outer1"
    assert not tree.children[0][1].is_leaf


def test_get_structure_list_of_lists_over_list():
    list_of_lists_type_description = factory.for_collection_type("list:list")
    tree = get_structure(list_of_lists_instance(), list_of_lists_type_description, "list")
    assert tree.collection_type_description.collection_type == "list"
    assert len(tree.children) == 2
    assert tree.children[0][0] == "outer1"
    assert tree.children[0][1].is_leaf
