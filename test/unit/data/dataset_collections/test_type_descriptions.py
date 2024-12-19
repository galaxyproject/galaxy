from galaxy.model.dataset_collections.type_description import CollectionTypeDescriptionFactory


def test_simple_descriptions():
    factory = CollectionTypeDescriptionFactory(None)
    nested_type_description = factory.for_collection_type("list:paired")
    paired_type_description = factory.for_collection_type("paired")
    assert not nested_type_description.has_subcollections_of_type("list")
    assert not nested_type_description.has_subcollections_of_type("list:paired")
    assert nested_type_description.has_subcollections_of_type("paired")
    assert nested_type_description.has_subcollections_of_type(paired_type_description)
    assert nested_type_description.has_subcollections()
    assert not paired_type_description.has_subcollections()
    assert paired_type_description.rank_collection_type() == 'paired'
    assert nested_type_description.rank_collection_type() == 'list'
    assert nested_type_description.effective_collection_type(paired_type_description) == 'list'
    assert nested_type_description.effective_collection_type_description(paired_type_description).collection_type == 'list'
    assert nested_type_description.child_collection_type() == 'paired'
