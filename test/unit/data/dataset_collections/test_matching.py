from galaxy.model.dataset_collections import (
    matching,
    query,
    registry,
    type_description,
)
from galaxy.model.dataset_collections.structure import UninitializedTree

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


def test_independent_mapping_axes_cross_product_in_stable_order():
    outer = list_instance(ids=["X", "Y"])
    inner = list_instance(ids=["P", "Q", "R"])
    to_match = matching.CollectionsToMatch()
    to_match.add("outer", outer, linked=False)
    to_match.add("inner", inner)

    matched = matching.MatchingCollections.for_collections(to_match, TYPE_DESCRIPTION_FACTORY)
    assert matched
    slices = list(matched.slice_collections())

    assert [
        (items["outer"].element_identifier, items["inner"].element_identifier, when_value)
        for items, when_value in slices
    ] == [
        ("X", "P", None),
        ("X", "Q", None),
        ("X", "R", None),
        ("Y", "P", None),
        ("Y", "Q", None),
        ("Y", "R", None),
    ]
    assert matched.structure.collection_type_description.collection_type == "list:list"


def test_linked_inputs_slice_in_zip_order():
    left = list_instance(ids=["L1", "L2"])
    right = list_instance(ids=["R1", "R2"])
    matched = build_matching_collections(("left", left), ("right", right))

    assert [
        (items["left"].element_identifier, items["right"].element_identifier)
        for items, _when_value in matched.slice_collections()
    ] == [("L1", "R1"), ("L2", "R2")]


def test_empty_axis_produces_no_slices_and_keeps_output_type():
    empty = collection_instance(collection_type="list", elements=[])
    matched = build_matching_collections(("empty", empty))

    assert list(matched.slice_collections()) == []
    assert matched.structure.collection_type_description.collection_type == "list"


def test_empty_outer_axis_short_circuits_unknown_inner_axis():
    empty = build_matching_collections(
        ("empty", collection_instance(collection_type="list", elements=[]))
    ).mapping_axes[0]
    unknown = matching.MatchingCollectionAxis(
        UninitializedTree(TYPE_DESCRIPTION_FACTORY.for_collection_type("list")),
        "unknown-inner",
    )
    matched = matching.MatchingCollections.from_axes([empty, unknown])

    assert list(matched.slice_collections()) == []
    assert matched.structure.collection_type_description.collection_type == "list:list"


def test_structure_only_axis_repeats_local_slices_and_conditions():
    outer = list_instance(ids=["X", "Y"])
    inner = list_instance(ids=["P", "Q", "R"])
    outer_match = build_matching_collections(("outer", outer))
    inner_match = build_matching_collections(("inner", inner))
    outer_match.when_values = [True, False]
    combined = inner_match.with_inherited_mapping(outer_match)

    slices = list(combined.slice_collections())

    assert [(items["inner"].element_identifier, when_value) for items, when_value in slices] == [
        ("P", True),
        ("Q", True),
        ("R", True),
        ("P", False),
        ("Q", False),
        ("R", False),
    ]
    assert combined.structure.collection_type_description.collection_type == "list:list"


def test_inherited_axis_preserves_identity_without_parent_binding():
    source = list_instance(ids=["X", "Y"])
    to_match = matching.CollectionsToMatch()
    to_match.add("source", source, axis_id=("invocation", 1, "boundary", 2))
    matched = matching.MatchingCollections.for_collections(to_match, TYPE_DESCRIPTION_FACTORY)
    assert matched

    local = build_matching_collections(("local", list_instance(ids=["P", "Q"])))
    combined = local.with_inherited_mapping(matched)

    assert combined.mapping_axes[0].axis_id == ("invocation", 1, "boundary", 2)
    assert "source" not in combined.bindings


def test_binding_can_span_multiple_axes():
    outer = build_matching_collections(("outer", list_instance(ids=["X", "Y"]))).mapping_axes[0]
    inner = build_matching_collections(("inner", list_instance(ids=["P", "Q", "R"]))).mapping_axes[0]
    nested = collection_instance(
        collection_type="list:list",
        elements=[
            collection_element("X", list_instance(ids=["XP", "XQ", "XR"]).collection),
            collection_element("Y", list_instance(ids=["YP", "YQ", "YR"]).collection),
        ],
    )
    combined = matching.MatchingCollections.from_axes(
        [outer, inner],
        bindings={
            "nested": matching.MatchingCollectionBinding(
                collection=nested,
                axis_indices=(0, 1),
            )
        },
    )

    slices = list(combined.slice_collections())

    assert [items["nested"].element_identifier for items, _when_value in slices] == [
        "XP",
        "XQ",
        "XR",
        "YP",
        "YQ",
        "YR",
    ]


def test_refined_linked_axis_broadcasts_prefix_binding_across_suffix():
    outer = build_matching_collections(("outer", list_instance(ids=["X", "Y"]))).mapping_axes[0]
    inner = collection_instance(
        collection_type="list:paired",
        elements=[
            collection_element("P", collection("paired", [hda_element("PF"), hda_element("PR")])),
            collection_element("Q", collection("paired", [hda_element("QF"), hda_element("QR")])),
        ],
    )
    refined_inner = build_matching_collections(("inner", inner)).mapping_axes[0]
    nested = collection_instance(
        collection_type="list:list:paired",
        elements=[
            collection_element("X", inner.collection),
            collection_element(
                "Y",
                collection(
                    "list:paired",
                    [
                        collection_element("P", collection("paired", [hda_element("YPF"), hda_element("YPR")])),
                        collection_element("Q", collection("paired", [hda_element("YQF"), hda_element("YQR")])),
                    ],
                ),
            ),
        ],
    )
    peer = collection_instance(
        collection_type="list:list",
        elements=[
            collection_element("X", list_instance(ids=["XP", "XQ"]).collection),
            collection_element("Y", list_instance(ids=["YP", "YQ"]).collection),
        ],
    )
    combined = matching.MatchingCollections.from_axes(
        [outer, refined_inner],
        bindings={
            "nested": matching.MatchingCollectionBinding(
                collection=nested,
                axis_indices=(0, 1),
                axis_path_slices=((0, None), (0, None)),
            ),
            "peer": matching.MatchingCollectionBinding(
                collection=peer,
                axis_indices=(0, 1),
                axis_path_slices=((0, None), (0, 1)),
            ),
        },
    )

    slices = list(combined.slice_collections())
    assert [items["peer"].element_identifier for items, _when in slices] == [
        "XP",
        "XP",
        "XQ",
        "XQ",
        "YP",
        "YP",
        "YQ",
        "YQ",
    ]
    assert [items["nested"].element_identifier for items, _when in slices] == [
        "PF",
        "PR",
        "QF",
        "QR",
        "YPF",
        "YPR",
        "YQF",
        "YQR",
    ]


def test_nested_axis_conditions_are_indexed_by_leaf_coordinate():
    nested = collection_instance(
        collection_type="list:list",
        elements=[
            collection_element("X", list_instance(ids=["XP", "XQ"]).collection),
            collection_element("Y", list_instance(ids=["YP", "YQ"]).collection),
        ],
    )
    matched = build_matching_collections(("nested", nested))
    matched.when_values = [True, False, True, False]

    assert [when_value for _items, when_value in matched.slice_collections()] == [True, False, True, False]


def test_product_condition_can_depend_on_every_axis():
    outer = build_matching_collections(("outer", list_instance(ids=["X", "Y"]))).mapping_axes[0]
    inner_match = build_matching_collections(("inner", list_instance(ids=["P", "Q", "R"])))
    inherited = matching.MatchingCollections.from_axes([outer])
    combined = inner_match.with_inherited_mapping(inherited)
    combined.when_values = [True, False, True, False, True, False]

    assert [when_value for _items, when_value in combined.slice_collections()] == [
        True,
        False,
        True,
        False,
        True,
        False,
    ]


def test_equal_axis_identity_is_shared_when_composing_mapping():
    source = list_instance(ids=["X", "Y"])
    inherited = build_matching_collections_with_axis_id("boundary", source)
    local = build_matching_collections_with_axis_id("tool_input", source)
    local.mapping_axes[0].axis_id = inherited.mapping_axes[0].axis_id

    combined = local.with_inherited_mapping(inherited)

    assert len(combined.mapping_axes) == 1
    assert [items["tool_input"].element_identifier for items, _when in combined.slice_collections()] == ["X", "Y"]


def test_inherited_axis_covers_locally_rediscovered_suffix():
    source = collection_instance(
        collection_type="list:list:list",
        elements=[
            collection_element(
                "X",
                collection(
                    "list:list",
                    [
                        collection_element("P", list_instance(ids=["XP1", "XP2"]).collection),
                        collection_element("Q", list_instance(ids=["XQ1", "XQ2"]).collection),
                    ],
                ),
            )
        ],
    )
    inherited_to_match = matching.CollectionsToMatch()
    inherited_to_match.add(
        "boundary",
        source,
        subcollection_type=TYPE_DESCRIPTION_FACTORY.for_collection_type("list"),
        axis_id="boundary-axis",
    )
    inherited = matching.MatchingCollections.for_collections(inherited_to_match, TYPE_DESCRIPTION_FACTORY)
    assert inherited
    assert inherited.structure.collection_type_description.collection_type == "list:list"

    local_to_match = matching.CollectionsToMatch()
    local_to_match.add(
        "tool_input",
        source,
        subcollection_type=TYPE_DESCRIPTION_FACTORY.for_collection_type("list:list"),
        axis_id="boundary-axis",
    )
    local = matching.MatchingCollections.for_collections(local_to_match, TYPE_DESCRIPTION_FACTORY)
    assert local
    assert local.structure.collection_type_description.collection_type == "list"

    combined = local.with_inherited_mapping(inherited)

    assert len(combined.mapping_axes) == 1
    assert [items["tool_input"].element_identifier for items, _when in combined.slice_collections()] == ["P", "Q"]


def test_inherited_axis_can_be_refined_by_ragged_materialized_output():
    outer = list_instance(ids=["X", "Y"])
    inherited = build_matching_collections_with_axis_id("boundary", outer)
    inherited.when_values = [True, False]
    inherited = inherited.without_bindings()
    nested = collection_instance(
        collection_type="list:list",
        elements=[
            collection_element("X", list_instance(ids=["XP", "XQ"]).collection),
            collection_element("Y", list_instance(ids=["YR", "YS", "YT"]).collection),
        ],
    )
    nested_structure = build_matching_collections(("nested", nested)).mapping_axes[0].structure

    refined = inherited.refine_axis(("source-terminal", "boundary"), nested_structure)
    refined.bindings = {
        "nested": matching.MatchingCollectionBinding(
            collection=nested,
            axis_indices=(0,),
            axis_path_slices=((0, None),),
        ),
        "outer": matching.MatchingCollectionBinding(
            collection=outer,
            axis_indices=(0,),
            axis_path_slices=((0, 1),),
        ),
    }

    slices = list(refined.slice_collections())
    assert refined.structure.collection_type_description.collection_type == "list:list"
    assert [items["nested"].element_identifier for items, _when in slices] == ["XP", "XQ", "YR", "YS", "YT"]
    assert [items["outer"].element_identifier for items, _when in slices] == ["X", "X", "Y", "Y", "Y"]
    assert [when for _items, when in slices] == [True, True, False, False, False]


def test_empty_inherited_axis_can_be_refined_without_unknown_cardinality():
    empty_outer = collection_instance(collection_type="list", elements=[])
    inherited = build_matching_collections_with_axis_id("boundary", empty_outer).without_bindings()
    empty_nested = collection_instance(collection_type="list:list", elements=[])
    nested_structure = build_matching_collections(("nested", empty_nested)).mapping_axes[0].structure

    refined = inherited.refine_axis(("source-terminal", "boundary"), nested_structure)

    assert list(refined.slice_collections()) == []
    assert refined.structure.collection_type_description.collection_type == "list:list"


def test_primary_axis_component_always_selects_the_complete_refined_path():
    nested = collection_instance(
        collection_type="list:list",
        elements=[collection_element("X", list_instance(ids=["XP", "XQ"]).collection)],
    )
    structure = build_matching_collections(("nested", nested)).mapping_axes[0].structure

    axis = matching.MatchingCollectionAxis(
        structure,
        "linked",
        (("source-local", 0, 2), ("linked", 0, 1), ("linked", 0, 2)),
    )

    assert axis.component_path_slice("linked") == (0, 2)
    assert [component for component in axis.components() if component[0] == "linked"] == [("linked", 0, 2)]


def test_same_collection_in_distinct_semantic_roles_remains_two_axes():
    source = list_instance(ids=["X", "Y"])
    inherited = build_matching_collections_with_axis_id("boundary", source)
    local = build_matching_collections_with_axis_id("tool_input", source)

    combined = local.with_inherited_mapping(inherited)

    assert len(combined.mapping_axes) == 2
    assert [items["tool_input"].element_identifier for items, _when in combined.slice_collections()] == [
        "X",
        "Y",
        "X",
        "Y",
    ]


def test_valid_collection_subcollection_matching():
    flat_list = list_instance(ids=["data1", "data2", "data3"])
    nested_list = example_list_of_paired_datasets()
    assert_cannot_match(flat_list, nested_list)
    assert_cannot_match(nested_list, flat_list)
    assert_can_match((nested_list, "paired"), flat_list)


# Sibling matching is symmetric: paired and paired_or_unpaired can be
# zipped under a common map-over regardless of arrival order. The
# substitution-rejection sentiment (paired_or_unpaired cannot be
# substituted *where paired is required*) is a connection-time concern
# tested in test_type_descriptions.py::test_paired_accepts_relation.
def test_paired_and_paired_or_unpaired_match_symmetric():
    paired = pair_instance()
    optional_paired = paired_or_unpaired_pair_instance()
    assert_can_match(optional_paired, paired)
    assert_can_match(paired, optional_paired)


def test_paired_or_unpaired_with_one_element_rejected_against_paired():
    """Cardinality safety: 1-element paired_or_unpaired cannot zip with 2-element paired."""
    paired = pair_instance()
    one_element_optional = collection_instance(
        collection_type="paired_or_unpaired",
        elements=[hda_element("unpaired")],
    )
    assert_cannot_match(paired, one_element_optional)
    assert_cannot_match(one_element_optional, paired)


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


def build_matching_collections(*named_items):
    to_match = matching.CollectionsToMatch()
    for name, collection in named_items:
        to_match.add(name, collection)
    matched = matching.MatchingCollections.for_collections(to_match, TYPE_DESCRIPTION_FACTORY)
    assert matched
    return matched


def build_matching_collections_with_axis_id(name, collection):
    to_match = matching.CollectionsToMatch()
    to_match.add(name, collection, axis_id=("source-terminal", name))
    matched = matching.MatchingCollections.for_collections(to_match, TYPE_DESCRIPTION_FACTORY)
    assert matched
    return matched


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


def list_element(element_identifier, list_collection=None):
    return collection_element(element_identifier, list_collection or list_instance().collection)


def list_of_lists_instance():
    return list_instance(
        elements=[
            list_element("outer1"),
            list_element("outer2"),
        ]
    )


def pair_instance():
    paired_collection_instance = collection_instance(
        collection_type="paired",
        elements=[
            hda_element("left"),
            hda_element("right"),
        ],
    )
    return paired_collection_instance


def list_paired_instance():
    return list_instance(
        elements=[
            pair_element("data1"),
            pair_element("data2"),
            pair_element("data3"),
        ],
        collection_type="list:paired",
    )


def list_of_paired_and_unpaired_instance():
    return collection_instance(
        collection_type="list:paired_or_unpaired",
        elements=[
            collection_element(
                "el1",
                collection(
                    "paired_or_unpaired",
                    [
                        hda_element("forward"),
                        hda_element("reverse"),
                    ],
                ),
            ),
            collection_element(
                "el2",
                collection(
                    "paired_or_unpaired",
                    [
                        hda_element("unpaired"),
                    ],
                ),
            ),
        ],
    )


def paired_or_unpaired_pair_instance():
    paired_collection_instance = collection_instance(
        collection_type="paired_or_unpaired",
        elements=[
            hda_element("forward"),
            hda_element("reverse"),
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
        self.column_definitions = None

    def __getitem__(self, index):
        return self.elements[index]


class MockCollectionElement:
    def __init__(self, element_identifier, collection):
        self.element_identifier = element_identifier
        self.child_collection = collection
        self.hda = None
        self.columns = None


class MockHDAElement:
    def __init__(self, element_identifier):
        self.element_identifier = element_identifier
        self.child_collection = False
        self.hda = object()
        self.columns = None


collection_instance = MockCollectionInstance
collection = MockCollection
collection_element = MockCollectionElement
hda_element = MockHDAElement
