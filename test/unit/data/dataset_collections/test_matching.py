from galaxy.model.dataset_collections import (
    matching,
    query,
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
    nested_list = nested_list = example_list_of_paired_datasets()
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
    nested_list = example_list_of_paired_datasets()
    assert_cannot_match(flat_list, nested_list)
    assert_cannot_match(nested_list, flat_list)
    assert_can_match((nested_list, "paired"), flat_list)


def test_query_can_match_list_to_list():
    flat_list = list_instance(ids=["data1", "data2", "data3"])
    q = query.HistoryQuery.from_collection_types(["list"], TYPE_DESCRIPTION_FACTORY)
    assert q.can_map_over(flat_list) is False
    assert q.direct_match(flat_list) is True


def test_query_can_match_list_of_paireds_to_paired():
    list_of_paired_datasets = example_list_of_paired_datasets()
    q = query.HistoryQuery.from_collection_types(["paired"], TYPE_DESCRIPTION_FACTORY)
    assert q.can_map_over(list_of_paired_datasets).collection_type == "paired"


def test_query_can_match_list_of_lists_to_paired():
    list_of_lists = example_list_of_lists()
    q = query.HistoryQuery.from_collection_types(["paired"], TYPE_DESCRIPTION_FACTORY)
    assert not q.can_map_over(list_of_lists)
    assert not q.direct_match(list_of_lists)


def test_query_can_match_list_of_lists_to_list():
    list_of_lists = example_list_of_lists()
    q = query.HistoryQuery.from_collection_types(["list"], TYPE_DESCRIPTION_FACTORY)
    assert q.can_map_over(list_of_lists).collection_type == "list"
    assert not q.direct_match(list_of_lists)


def test_query_can_match_list_of_paireds_to_list_or_paired():
    list_of_paired_datasets = example_list_of_paired_datasets()
    q = query.HistoryQuery.from_collection_types(["list", "paired"], TYPE_DESCRIPTION_FACTORY)
    assert q.can_map_over(list_of_paired_datasets).collection_type == "paired"
    assert q.direct_match(list_of_paired_datasets) is False


def test_query_can_match_list_of_lists_to_list_or_paired():
    list_of_lists = example_list_of_lists()
    q = query.HistoryQuery.from_collection_types(["list", "paired"], TYPE_DESCRIPTION_FACTORY)
    assert q.can_map_over(list_of_lists).collection_type == "list"
    assert q.direct_match(list_of_lists) is False


def test_query_always_direct_match_if_no_collection_type_on_input_specified():
    list_of_lists = example_list_of_lists()
    q = query.HistoryQuery.from_collection_types([], TYPE_DESCRIPTION_FACTORY)
    assert q.can_map_over(list_of_lists) is False
    assert q.direct_match(list_of_lists) is True


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


def example_list_of_paired_datasets():
    return list_instance(
        elements=[
            pair_element("data1"),
            pair_element("data2"),
            pair_element("data3"),
        ],
        collection_type="list:paired",
    )


def example_list_of_lists():
    return list_instance(
        elements=[
            list_instance(),
            list_instance(),
        ],
        collection_type="list:list",
    )


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
