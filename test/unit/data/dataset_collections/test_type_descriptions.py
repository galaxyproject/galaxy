import pytest

from galaxy.exceptions import RequestParameterInvalidException
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


def test_sample_sheet_acts_like_list():
    """sample_sheet should behave like list for mapping/matching purposes."""
    sample_sheet = c_t("sample_sheet")
    sample_sheet_paired = c_t("sample_sheet:paired")
    sample_sheet_paired_or_unpaired = c_t("sample_sheet:paired_or_unpaired")
    list_type = c_t("list")
    paired_type = c_t("paired")

    # sample_sheet matches list
    assert sample_sheet.can_match_type("list")
    assert sample_sheet.can_match_type(list_type)
    assert list_type.can_match_type("sample_sheet")

    # sample_sheet:paired matches list:paired
    assert sample_sheet_paired.can_match_type("list:paired")
    assert c_t("list:paired").can_match_type("sample_sheet:paired")

    # sample_sheet:paired_or_unpaired matches list:paired_or_unpaired
    assert sample_sheet_paired_or_unpaired.can_match_type("list:paired_or_unpaired")
    # and can match list:paired and list (like list:paired_or_unpaired does)
    assert sample_sheet_paired_or_unpaired.can_match_type("list:paired")
    assert sample_sheet_paired_or_unpaired.can_match_type("list")
    assert sample_sheet_paired_or_unpaired.can_match_type("sample_sheet")
    assert sample_sheet_paired_or_unpaired.can_match_type("sample_sheet:paired")

    # sample_sheet:paired has subcollections of type paired
    assert sample_sheet_paired.has_subcollections_of_type("paired")
    assert sample_sheet_paired.has_subcollections_of_type(paired_type)

    # sample_sheet has subcollections of type paired_or_unpaired (like list does)
    assert sample_sheet.has_subcollections_of_type("paired_or_unpaired")

    # sample_sheet does NOT have subcollections of itself
    assert not sample_sheet.has_subcollections_of_type("sample_sheet")
    assert not sample_sheet.has_subcollections_of_type("list")

    # effective collection type works correctly
    assert sample_sheet_paired.effective_collection_type(paired_type) == "sample_sheet"


def test_validate():
    c_t("list").validate()
    c_t("list:paired").validate()
    c_t("list:list:list:list:paired:list").validate()
    c_t("paired:paired").validate()
    c_t("list:paired_or_unpaired").validate()
    c_t("paired_or_unpaired:paired").validate()

    with pytest.raises(RequestParameterInvalidException):
        c_t("foo").validate()

    with pytest.raises(RequestParameterInvalidException):
        c_t("listx").validate()

    with pytest.raises(RequestParameterInvalidException):
        c_t("list:list:paired_or").validate()
