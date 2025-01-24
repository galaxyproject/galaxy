from galaxy.model.dataset_collections import (
    matching,
    registry,
    type_description,
)

TYPE_REGISTRY = registry.DatasetCollectionTypesRegistry()
TYPE_DESCRIPTION_FACTORY = type_description.CollectionTypeDescriptionFactory(TYPE_REGISTRY)


def test_pairs_match():
    assert_can_match(pair_instance(), pair_instance())


def test_lists_of_same_cardinality_match():
    assert_can_match(list_instance(), list_instance())


def test_nested_lists_match():
    nested_list = list_instance(
        elements=[
            pair_element("data1"),
            pair_element("data2"),
            pair_element("data3"),
        ],
        collection_type="list:paired",
    )
    assert_can_match(nested_list, nested_list)


def test_different_types_cannot_match():
    assert_cannot_match(list_instance(), pair_instance())
    assert_cannot_match(pair_instance(), list_instance())


def test_lists_of_different_cardinality_do_not_match():
    list_1 = list_instance(ids=["data1", "data2"])
    list_2 = list_instance(ids=["data1", "data2", "data3"])
    assert_cannot_match(list_1, list_2)
    assert_cannot_match(list_2, list_1)


def test_valid_collection_subcollection_matching():
    flat_list = list_instance(ids=["data1", "data2", "data3"])
    nested_list = list_instance(
        elements=[
            pair_element("data11"),
            pair_element("data21"),
            pair_element("data31"),
        ],
        collection_type="list:paired",
    )
    assert_cannot_match(flat_list, nested_list)
    assert_cannot_match(nested_list, flat_list)
    assert_can_match((nested_list, "paired"), flat_list)


def assert_can_match(*items):
    to_match = build_collections_to_match(*items)
    matching.MatchingCollections.for_collections(to_match, TYPE_DESCRIPTION_FACTORY)


def assert_cannot_match(*items):
    to_match = build_collections_to_match(*items)
    threw_exception = False
    try:
        matching.MatchingCollections.for_collections(to_match, TYPE_DESCRIPTION_FACTORY)
    except Exception:
        threw_exception = True
    assert threw_exception


def build_collections_to_match(*items):
    to_match = matching.CollectionsToMatch()

    for i, item in enumerate(items):
        if isinstance(item, tuple):
            collection_instance, subcollection_type = item
        else:
            collection_instance, subcollection_type = item, None
        to_match.add(f"input_{i}", collection_instance, subcollection_type)
    return to_match


def pair_element(element_identifier):
    return collection_element(element_identifier, pair_instance().collection)


def pair_instance():
    paired_collection_instance = collection_instance(
        collection_type="paired",
        elements=[
            hda_element("left"),
            hda_element("right"),
        ],
    )
    return paired_collection_instance


def list_instance(collection_type="list", elements=None, ids=None):
    if not elements:
        if ids is None:
            ids = ["data1", "data2"]
        elements = [hda_element(_) for _ in ids]
    list_collection_instance = collection_instance(collection_type=collection_type, elements=elements)
    return list_collection_instance


class MockCollectionInstance:
    def __init__(self, collection_type, elements):
        self.collection = MockCollection(collection_type, elements)


class MockCollection:
    def __init__(self, collection_type, elements):
        self.collection_type = collection_type
        self.elements = elements
        self.populated = True


class MockCollectionElement:
    def __init__(self, element_identifier, collection):
        self.element_identifier = element_identifier
        self.child_collection = collection
        self.hda = None


class MockHDAElement:
    def __init__(self, element_identifier):
        self.element_identifier = element_identifier
        self.child_collection = False
        self.hda = object()


collection_instance = MockCollectionInstance
collection = MockCollection
collection_element = MockCollectionElement
hda_element = MockHDAElement
