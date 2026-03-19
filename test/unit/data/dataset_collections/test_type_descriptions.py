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


def test_effective_collection_type_paired_or_unpaired_over_paired():
    """Test effective_collection_type when paired_or_unpaired maps over paired."""
    assert c_t("list:paired").effective_collection_type("paired_or_unpaired") == "list"
    assert c_t("list:paired_or_unpaired").effective_collection_type("paired_or_unpaired") == "list"


def test_endswith_colon_boundary():
    """Regression: endswith must require colon boundary to avoid partial matches.

    'list:paired_or_unpaired'.endswith('paired') was True because 'paired'
    is a substring at the end of 'paired_or_unpaired'. The fix requires
    ':paired' (with colon prefix) so only proper rank boundaries match.
    """
    # list:paired_or_unpaired does NOT have subcollections of type paired
    # PAIRED_OR_UNPAIRED_NOT_CONSUMED_BY_PAIRED_WHEN_MAPPING
    assert not c_t("list:paired_or_unpaired").has_subcollections_of_type("paired")

    # But list:paired DOES have subcollections of type paired (proper boundary)
    assert c_t("list:paired").has_subcollections_of_type("paired")

    # And list:list:paired_or_unpaired does NOT have subcollections of type paired
    assert not c_t("list:list:paired_or_unpaired").has_subcollections_of_type("paired")

    # Existing cases still work
    assert c_t("list:list:paired").has_subcollections_of_type("paired")
    assert c_t("list:list:paired").has_subcollections_of_type("list:paired")
    assert not c_t("list:list:paired").has_subcollections_of_type("list")


def test_compound_paired_or_unpaired_has_subcollections():
    """Test compound :paired_or_unpaired suffix in has_subcollections_of_type.

    Covers collection_semantics.yml examples:
    - MAPPING_LIST_LIST_OVER_LIST_PAIRED_OR_UNPAIRED
    - MAPPING_LIST_LIST_PAIRED_OVER_PAIRED_OR_UNPAIRED (via compound path)
    """
    # list:list can map over list:paired_or_unpaired
    assert c_t("list:list").has_subcollections_of_type("list:paired_or_unpaired")

    # list:list:paired can map over list:paired_or_unpaired
    # (paired consumed by paired_or_unpaired, higher ranks list == list)
    assert c_t("list:list:paired").has_subcollections_of_type("list:paired_or_unpaired")

    # list:list:list can map over list:paired_or_unpaired
    assert c_t("list:list:list").has_subcollections_of_type("list:paired_or_unpaired")

    # list:paired cannot map over list:paired_or_unpaired — same rank,
    # after stripping :paired the higher ranks are equal (no remainder)
    assert not c_t("list:paired").has_subcollections_of_type("list:paired_or_unpaired")

    # list cannot map over list:paired_or_unpaired — lower rank
    assert not c_t("list").has_subcollections_of_type("list:paired_or_unpaired")

    # paired cannot map over list:paired_or_unpaired — higher ranks don't align
    assert not c_t("paired").has_subcollections_of_type("list:paired_or_unpaired")

    # paired:paired cannot map over list:paired_or_unpaired — higher ranks
    # don't align (paired != list)
    assert not c_t("paired:paired").has_subcollections_of_type("list:paired_or_unpaired")


def test_compound_paired_or_unpaired_effective_collection_type():
    """Test effective_collection_type with compound :paired_or_unpaired."""
    # list:list over list:paired_or_unpaired → list
    assert c_t("list:list").effective_collection_type("list:paired_or_unpaired") == "list"

    # list:list:paired over list:paired_or_unpaired → list
    # (peel off list and paired_or_unpaired ranks, then strip :paired)
    assert c_t("list:list:paired").effective_collection_type("list:paired_or_unpaired") == "list"

    # list:list:list over list:paired_or_unpaired → list:list
    assert c_t("list:list:list").effective_collection_type("list:paired_or_unpaired") == "list:list"


def test_effective_collection_type_paired_or_unpaired_non_paired():
    """Test that paired_or_unpaired acts like single_datasets for non-paired collections."""
    # list over paired_or_unpaired → list (full type preserved, like single_datasets)
    assert c_t("list").effective_collection_type("paired_or_unpaired") == "list"
    # list:list over paired_or_unpaired → list:list
    assert c_t("list:list").effective_collection_type("paired_or_unpaired") == "list:list"


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
