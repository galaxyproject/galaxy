from galaxy.model.dataset_collections.type_description import CollectionTypeDescriptionFactory

factory = CollectionTypeDescriptionFactory(None)


def c_t(collection_type: str):
    return factory.for_collection_type(collection_type)


def test_simple_descriptions():
    nested_type_description = c_t("list:paired")
    paired_type_description = c_t("paired")
    assert not nested_type_description.has_subcollections_of_type("list")
    assert not nested_type_description.has_subcollections_of_type("list:paired")
    assert nested_type_description.has_subcollections_of_type("paired")
    assert nested_type_description.has_subcollections_of_type(paired_type_description)
    assert nested_type_description.has_subcollections()
    assert not paired_type_description.has_subcollections()
    assert paired_type_description.rank_collection_type() == "paired"
    assert nested_type_description.rank_collection_type() == "list"
    assert nested_type_description.effective_collection_type(paired_type_description) == "list"
    assert (
        nested_type_description.effective_collection_type_description(paired_type_description).collection_type == "list"
    )
    assert nested_type_description.child_collection_type() == "paired"


def test_paired_or_unpaired_handling():
    list_type_description = c_t("list")
    assert list_type_description.has_subcollections_of_type("paired_or_unpaired")
    paired_type_description = c_t("paired")
    assert not paired_type_description.has_subcollections_of_type("paired_or_unpaired")

    nested_type_description = factory.for_collection_type("list:paired")
    assert nested_type_description.has_subcollections_of_type("paired_or_unpaired")

    nested_list_type_description = factory.for_collection_type("list:list")
    assert nested_list_type_description.has_subcollections_of_type("paired_or_unpaired")

    mixed_list_type_description = factory.for_collection_type("list:paired_or_unpaired")
    assert mixed_list_type_description.can_match_type("list:paired_or_unpaired")
    assert mixed_list_type_description.can_match_type("list:paired")
    assert mixed_list_type_description.can_match_type("list")
