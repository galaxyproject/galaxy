import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model.dataset_collections.type_description import CollectionTypeDescriptionFactory

factory = CollectionTypeDescriptionFactory(None)


def c_t(collection_type: str):
    return factory.for_collection_type(collection_type)


def test_simple_descriptions():
    nested_type_description = c_t("list:paired")
    paired_type_description = c_t("paired")
    assert not nested_type_description.can_map_over("list")
    assert not nested_type_description.can_map_over("list:paired")
    assert nested_type_description.can_map_over("paired")
    assert nested_type_description.can_map_over(paired_type_description)
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
    assert list_type_description.can_map_over("paired_or_unpaired")
    paired_type_description = c_t("paired")
    assert not paired_type_description.can_map_over("paired_or_unpaired")

    nested_type_description = factory.for_collection_type("list:paired")
    assert nested_type_description.can_map_over("paired_or_unpaired")

    nested_list_type_description = factory.for_collection_type("list:list")
    assert nested_list_type_description.can_map_over("paired_or_unpaired")

    mixed_list_type_description = factory.for_collection_type("list:paired_or_unpaired")
    assert mixed_list_type_description.accepts("list:paired_or_unpaired")
    assert mixed_list_type_description.accepts("list:paired")
    assert mixed_list_type_description.accepts("list")


def test_sample_sheet_accepts_relation():
    """sample_sheet -> list matches; list -> sample_sheet does not.

    A sample_sheet candidate carries list-like structure plus column metadata,
    so it can satisfy a list-shaped requirement. A plain list candidate
    cannot satisfy a sample_sheet-shaped requirement because the column
    metadata is absent. ``accepts`` / ``can_map_over`` follow
    the convention ``requirement.accepts(candidate)`` /
    ``output.can_map_over(input)``.
    """
    sample_sheet = c_t("sample_sheet")
    sample_sheet_paired = c_t("sample_sheet:paired")
    sample_sheet_paired_or_unpaired = c_t("sample_sheet:paired_or_unpaired")
    list_type = c_t("list")
    paired_type = c_t("paired")

    # list requirement is satisfied by a sample_sheet candidate
    assert list_type.accepts("sample_sheet")
    assert c_t("list:paired").accepts("sample_sheet:paired")
    assert c_t("list:paired_or_unpaired").accepts("sample_sheet:paired_or_unpaired")

    # sample_sheet requirement is NOT satisfied by a plain list candidate
    assert not sample_sheet.accepts("list")
    assert not sample_sheet.accepts(list_type)
    assert not sample_sheet_paired.accepts("list:paired")
    assert not sample_sheet_paired_or_unpaired.accepts("list:paired_or_unpaired")
    assert not sample_sheet_paired_or_unpaired.accepts("list:paired")
    assert not sample_sheet_paired_or_unpaired.accepts("list")

    # sample_sheet <-> sample_sheet still works
    assert sample_sheet.accepts("sample_sheet")
    assert sample_sheet_paired.accepts("sample_sheet:paired")
    assert sample_sheet_paired_or_unpaired.accepts("sample_sheet")
    assert sample_sheet_paired_or_unpaired.accepts("sample_sheet:paired")

    # sample_sheet:paired has subcollections of type paired (plain input, OK)
    assert sample_sheet_paired.can_map_over("paired")
    assert sample_sheet_paired.can_map_over(paired_type)

    # sample_sheet has subcollections of type paired_or_unpaired (like list does)
    assert sample_sheet.can_map_over("paired_or_unpaired")

    # sample_sheet does NOT have subcollections of itself
    assert not sample_sheet.can_map_over("sample_sheet")
    assert not sample_sheet.can_map_over("list")

    # Map-over asymmetry: a plain list:* output cannot be mapped over a
    # sample_sheet-variant input (lacks column metadata).
    assert not c_t("list:list").can_map_over("sample_sheet")
    assert not c_t("list:list:paired").can_map_over("sample_sheet:paired")
    # but a sample_sheet:* output CAN map over a plain-list-variant input
    assert c_t("sample_sheet:paired").can_map_over("paired")

    # effective collection type works correctly
    assert sample_sheet_paired.effective_collection_type(paired_type) == "sample_sheet"


def test_paired_accepts_relation():
    """paired_or_unpaired requirement is satisfied by paired candidate; reverse is not."""
    assert c_t("paired_or_unpaired").accepts("paired")
    assert not c_t("paired").accepts("paired_or_unpaired")
    # nested form
    assert c_t("list:paired_or_unpaired").accepts("list:paired")
    assert not c_t("list:paired").accepts("list:paired_or_unpaired")


def test_compatible():
    """``compatible`` is symmetric — order does not matter."""
    # same type
    assert c_t("list").compatible("list")
    assert c_t("paired").compatible("paired")

    # subtype pair (either order)
    assert c_t("paired").compatible("paired_or_unpaired")
    assert c_t("paired_or_unpaired").compatible("paired")
    assert c_t("list").compatible("sample_sheet")
    assert c_t("sample_sheet").compatible("list")
    assert c_t("list:paired").compatible("sample_sheet:paired")
    assert c_t("sample_sheet:paired").compatible("list:paired")

    # disjoint types
    assert not c_t("paired").compatible("list")
    assert not c_t("list").compatible("paired")
    assert not c_t("list:paired").compatible("list:list")
    assert not c_t("list:list").compatible("list:paired")


def test_effective_collection_type_paired_or_unpaired_over_paired():
    """Test effective_collection_type when paired_or_unpaired maps over paired."""
    assert c_t("list:paired").effective_collection_type("paired_or_unpaired") == "list"
    assert c_t("list:list:paired").effective_collection_type("paired_or_unpaired") == "list:list"
    assert c_t("list:paired_or_unpaired").effective_collection_type("paired_or_unpaired") == "list"


def test_endswith_colon_boundary():
    """Regression: endswith must require colon boundary to avoid partial matches.

    'list:paired_or_unpaired'.endswith('paired') was True because 'paired'
    is a substring at the end of 'paired_or_unpaired'. The fix requires
    ':paired' (with colon prefix) so only proper rank boundaries match.
    """
    # list:paired_or_unpaired does NOT have subcollections of type paired
    # PAIRED_OR_UNPAIRED_NOT_CONSUMED_BY_PAIRED_WHEN_MAPPING
    assert not c_t("list:paired_or_unpaired").can_map_over("paired")

    # But list:paired DOES have subcollections of type paired (proper boundary)
    assert c_t("list:paired").can_map_over("paired")

    # And list:list:paired_or_unpaired does NOT have subcollections of type paired
    assert not c_t("list:list:paired_or_unpaired").can_map_over("paired")

    # Existing cases still work
    assert c_t("list:list:paired").can_map_over("paired")
    assert c_t("list:list:paired").can_map_over("list:paired")
    assert not c_t("list:list:paired").can_map_over("list")


def test_compound_paired_or_unpaired_can_map_over():
    """Test compound :paired_or_unpaired suffix in can_map_over.

    Covers collection_semantics.yml examples:
    - MAPPING_LIST_LIST_OVER_LIST_PAIRED_OR_UNPAIRED
    - MAPPING_LIST_LIST_PAIRED_OVER_PAIRED_OR_UNPAIRED (via compound path)
    """
    # list:list can map over list:paired_or_unpaired
    assert c_t("list:list").can_map_over("list:paired_or_unpaired")

    # list:list:paired can map over list:paired_or_unpaired
    # (paired consumed by paired_or_unpaired, higher ranks list == list)
    assert c_t("list:list:paired").can_map_over("list:paired_or_unpaired")

    # list:list:list can map over list:paired_or_unpaired
    assert c_t("list:list:list").can_map_over("list:paired_or_unpaired")

    # list:paired cannot map over list:paired_or_unpaired — same rank,
    # after stripping :paired the higher ranks are equal (no remainder)
    assert not c_t("list:paired").can_map_over("list:paired_or_unpaired")

    # list cannot map over list:paired_or_unpaired — lower rank
    assert not c_t("list").can_map_over("list:paired_or_unpaired")

    # paired cannot map over list:paired_or_unpaired — higher ranks don't align
    assert not c_t("paired").can_map_over("list:paired_or_unpaired")

    # paired:paired cannot map over list:paired_or_unpaired — higher ranks
    # don't align (paired != list)
    assert not c_t("paired:paired").can_map_over("list:paired_or_unpaired")


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
