"""Tests for galaxy.tool_util.workflow_state.connection_types.

Ports relevant test cases from terminals.test.ts and validates against
collection_semantics.yml examples.
"""

from galaxy.tool_util.collections import COLLECTION_TYPE_DESCRIPTION_FACTORY as factory
from galaxy.tool_util.workflow_state.connection_types import (
    ANY_COLLECTION_TYPE,
    can_map_over,
    can_match,
    collection_type_rank,
    effective_map_over,
    NULL_COLLECTION_TYPE,
)


def c_t(collection_type: str):
    return factory.for_collection_type(collection_type)


# -- Sentinel tests --


class TestNullCollectionType:
    def test_not_a_collection(self):
        assert not NULL_COLLECTION_TYPE.is_collection

    def test_collection_type_is_none(self):
        assert NULL_COLLECTION_TYPE.collection_type is None

    def test_rank_is_zero(self):
        assert NULL_COLLECTION_TYPE.rank == 0

    def test_cannot_match_anything(self):
        assert not can_match(NULL_COLLECTION_TYPE, c_t("list"))
        assert not can_match(c_t("list"), NULL_COLLECTION_TYPE)
        assert not can_match(NULL_COLLECTION_TYPE, NULL_COLLECTION_TYPE)

    def test_null_output_cannot_map_over(self):
        assert not can_map_over(NULL_COLLECTION_TYPE, c_t("list"))

    def test_collection_can_map_over_null_input(self):
        # Any collection can map over a plain dataset
        assert can_map_over(c_t("list"), NULL_COLLECTION_TYPE)
        assert can_map_over(c_t("paired"), NULL_COLLECTION_TYPE)

    def test_effective_map_over_null_output(self):
        assert effective_map_over(NULL_COLLECTION_TYPE, c_t("list")) is None


class TestAnyCollectionType:
    def test_is_a_collection(self):
        assert ANY_COLLECTION_TYPE.is_collection

    def test_collection_type_is_any(self):
        assert ANY_COLLECTION_TYPE.collection_type == "any"

    def test_rank_is_negative(self):
        assert ANY_COLLECTION_TYPE.rank == -1

    def test_matches_any_collection(self):
        assert can_match(c_t("list"), ANY_COLLECTION_TYPE)
        assert can_match(c_t("paired"), ANY_COLLECTION_TYPE)

    def test_does_not_match_null(self):
        assert not can_match(NULL_COLLECTION_TYPE, ANY_COLLECTION_TYPE)

    def test_cannot_map_over(self):
        assert not can_map_over(c_t("list"), ANY_COLLECTION_TYPE)
        assert not can_map_over(ANY_COLLECTION_TYPE, c_t("list"))


# -- Rank tests --


class TestCollectionTypeRank:
    def test_simple_types(self):
        assert collection_type_rank(c_t("list")) == 1
        assert collection_type_rank(c_t("paired")) == 1
        assert collection_type_rank(c_t("paired_or_unpaired")) == 1

    def test_nested_types(self):
        assert collection_type_rank(c_t("list:paired")) == 2
        assert collection_type_rank(c_t("list:list")) == 2
        assert collection_type_rank(c_t("list:paired_or_unpaired")) == 2

    def test_deeply_nested(self):
        assert collection_type_rank(c_t("list:list:paired")) == 3
        assert collection_type_rank(c_t("list:list:list")) == 3


# -- can_match tests --
# Convention: can_match(output_type, input_type) — "can this output satisfy this input?"
# In TS: inputType.canMatch(outputType) — called on receiving side with providing side as arg.
# The adapter handles the direction: it calls input_type.can_match_type(output_type).


class TestCanMatch:
    """Direct match tests — can output satisfy input without mapping?"""

    def test_exact_match(self):
        assert can_match(c_t("list"), c_t("list"))
        assert can_match(c_t("paired"), c_t("paired"))
        assert can_match(c_t("list:paired"), c_t("list:paired"))

    def test_paired_matches_paired_or_unpaired(self):
        # PAIRED_OR_UNPAIRED_CONSUMES_PAIRED
        assert can_match(c_t("paired"), c_t("paired_or_unpaired"))

    def test_paired_or_unpaired_does_not_match_paired(self):
        # PAIRED_OR_UNPAIRED_NOT_CONSUMED_BY_PAIRED
        assert not can_match(c_t("paired_or_unpaired"), c_t("paired"))

    def test_sample_sheet_matches_list(self):
        # SAMPLE_SHEET_MATCHES_LIST
        assert can_match(c_t("sample_sheet"), c_t("list"))

    def test_sample_sheet_normalization_is_symmetric(self):
        # can_match_type normalizes both sides (sample_sheet → list), so
        # list ↔ sample_sheet match bidirectionally at this level.
        # The asymmetry (LIST_NOT_MATCHES_SAMPLE_SHEET) is enforced at
        # the connection validation level, not in can_match_type.
        assert can_match(c_t("list"), c_t("sample_sheet"))

    def test_sample_sheet_paired_matches_list_paired(self):
        # SAMPLE_SHEET_PAIRED_MATCHES_LIST_PAIRED
        assert can_match(c_t("sample_sheet:paired"), c_t("list:paired"))

    def test_sample_sheet_paired_normalization_is_symmetric(self):
        # Same as above — normalization makes these equal at can_match level
        assert can_match(c_t("list:paired"), c_t("sample_sheet:paired"))

    def test_list_paired_matches_list_paired_or_unpaired(self):
        assert can_match(c_t("list:paired"), c_t("list:paired_or_unpaired"))

    def test_list_matches_list_paired_or_unpaired(self):
        assert can_match(c_t("list"), c_t("list:paired_or_unpaired"))

    def test_incompatible_types(self):
        assert not can_match(c_t("list"), c_t("paired"))
        assert not can_match(c_t("paired"), c_t("list"))
        assert not can_match(c_t("list:paired"), c_t("list:list"))

    def test_sample_sheet_paired_or_unpaired_matches_list_paired_or_unpaired(self):
        # SAMPLE_SHEET_PAIRED_OR_UNPAIRED_MATCHES_LIST_PAIRED_OR_UNPAIRED
        assert can_match(c_t("sample_sheet:paired_or_unpaired"), c_t("list:paired_or_unpaired"))


# -- can_map_over tests --
# Convention: can_map_over(output_type, input_type) — "can this output be mapped over this input?"
# The output has higher rank than the input and contains subcollections matching it.


class TestCanMapOver:
    """Map-over tests — can output be mapped over input?"""

    def test_list_over_dataset(self):
        # Any collection can map over a plain dataset (NULL)
        assert can_map_over(c_t("list"), NULL_COLLECTION_TYPE)
        assert can_map_over(c_t("paired"), NULL_COLLECTION_TYPE)
        assert can_map_over(c_t("list:paired"), NULL_COLLECTION_TYPE)

    def test_list_paired_over_paired(self):
        # MAPPING_LIST_PAIRED_OVER_PAIRED
        assert can_map_over(c_t("list:paired"), c_t("paired"))

    def test_list_paired_over_paired_or_unpaired(self):
        # MAPPING_LIST_PAIRED_OVER_PAIRED_OR_UNPAIRED
        assert can_map_over(c_t("list:paired"), c_t("paired_or_unpaired"))

    def test_list_list_over_list(self):
        # NESTED_LIST_REDUCTION — list:list over list (multi-data)
        assert can_map_over(c_t("list:list"), c_t("list"))

    def test_list_paired_not_over_list(self):
        # paired ≠ list
        assert not can_map_over(c_t("list:paired"), c_t("list"))

    def test_paired_not_over_list(self):
        # rank too low
        assert not can_map_over(c_t("paired"), c_t("list"))

    def test_list_over_paired_or_unpaired(self):
        # MAPPING_LIST_OVER_PAIRED_OR_UNPAIRED — via single_datasets
        assert can_map_over(c_t("list"), c_t("paired_or_unpaired"))

    def test_list_list_over_paired_or_unpaired(self):
        # MAPPING_LIST_LIST_OVER_PAIRED_OR_UNPAIRED
        assert can_map_over(c_t("list:list"), c_t("paired_or_unpaired"))

    def test_list_paired_or_unpaired_not_over_paired(self):
        # PAIRED_OR_UNPAIRED_NOT_CONSUMED_BY_PAIRED_WHEN_MAPPING
        assert not can_map_over(c_t("list:paired_or_unpaired"), c_t("paired"))

    def test_list_paired_or_unpaired_not_over_list(self):
        # PAIRED_OR_UNPAIRED_NOT_CONSUMED_BY_LIST_WHEN_MAPPING
        assert not can_map_over(c_t("list:paired_or_unpaired"), c_t("list"))

    def test_cannot_map_over_self(self):
        assert not can_map_over(c_t("list"), c_t("list"))
        assert not can_map_over(c_t("paired"), c_t("paired"))

    # -- Compound :paired_or_unpaired suffix cases (the bugfix) --

    def test_list_list_over_list_paired_or_unpaired(self):
        # MAPPING_LIST_LIST_OVER_LIST_PAIRED_OR_UNPAIRED
        assert can_map_over(c_t("list:list"), c_t("list:paired_or_unpaired"))

    def test_list_list_paired_over_list_paired_or_unpaired(self):
        assert can_map_over(c_t("list:list:paired"), c_t("list:paired_or_unpaired"))

    def test_list_list_list_over_list_paired_or_unpaired(self):
        assert can_map_over(c_t("list:list:list"), c_t("list:paired_or_unpaired"))

    def test_list_paired_not_over_list_paired_or_unpaired(self):
        # Same rank, after stripping :paired no remainder
        assert not can_map_over(c_t("list:paired"), c_t("list:paired_or_unpaired"))

    def test_paired_paired_not_over_list_paired_or_unpaired(self):
        # Higher ranks don't align
        assert not can_map_over(c_t("paired:paired"), c_t("list:paired_or_unpaired"))

    # -- sample_sheet mapping --

    def test_sample_sheet_paired_over_paired(self):
        # SAMPLE_SHEET_PAIRED_MAPPING_OVER_PAIRED
        assert can_map_over(c_t("sample_sheet:paired"), c_t("paired"))

    def test_sample_sheet_over_paired_or_unpaired(self):
        # SAMPLE_SHEET_MAPPING_OVER_PAIRED_OR_UNPAIRED
        assert can_map_over(c_t("sample_sheet"), c_t("paired_or_unpaired"))

    def test_null_cannot_map_over_anything(self):
        assert not can_map_over(NULL_COLLECTION_TYPE, c_t("list"))
        assert not can_map_over(NULL_COLLECTION_TYPE, NULL_COLLECTION_TYPE)

    def test_any_cannot_map_over(self):
        assert not can_map_over(c_t("list"), ANY_COLLECTION_TYPE)


# -- effective_map_over tests --


class TestEffectiveMapOver:
    """Compute remainder collection type after mapping."""

    def test_list_paired_over_paired(self):
        result = effective_map_over(c_t("list:paired"), c_t("paired"))
        assert result is not None
        assert result.collection_type == "list"

    def test_list_paired_over_paired_or_unpaired(self):
        result = effective_map_over(c_t("list:paired"), c_t("paired_or_unpaired"))
        assert result is not None
        assert result.collection_type == "list"

    def test_list_list_over_list(self):
        result = effective_map_over(c_t("list:list"), c_t("list"))
        assert result is not None
        assert result.collection_type == "list"

    def test_list_over_paired_or_unpaired(self):
        # paired_or_unpaired acts like single_datasets — full type preserved
        result = effective_map_over(c_t("list"), c_t("paired_or_unpaired"))
        assert result is not None
        assert result.collection_type == "list"

    def test_list_list_over_paired_or_unpaired(self):
        result = effective_map_over(c_t("list:list"), c_t("paired_or_unpaired"))
        assert result is not None
        assert result.collection_type == "list:list"

    def test_list_list_paired_over_paired_or_unpaired(self):
        result = effective_map_over(c_t("list:list:paired"), c_t("paired_or_unpaired"))
        assert result is not None
        assert result.collection_type == "list:list"

    # -- Compound :paired_or_unpaired suffix cases --

    def test_list_list_over_list_paired_or_unpaired(self):
        # MAPPING_LIST_LIST_OVER_LIST_PAIRED_OR_UNPAIRED
        result = effective_map_over(c_t("list:list"), c_t("list:paired_or_unpaired"))
        assert result is not None
        assert result.collection_type == "list"

    def test_list_list_paired_over_list_paired_or_unpaired(self):
        result = effective_map_over(c_t("list:list:paired"), c_t("list:paired_or_unpaired"))
        assert result is not None
        assert result.collection_type == "list"

    def test_list_list_list_over_list_paired_or_unpaired(self):
        result = effective_map_over(c_t("list:list:list"), c_t("list:paired_or_unpaired"))
        assert result is not None
        assert result.collection_type == "list:list"

    # -- Map over dataset (NULL) --

    def test_list_over_dataset(self):
        result = effective_map_over(c_t("list"), NULL_COLLECTION_TYPE)
        assert result is not None
        assert result.collection_type == "list"

    def test_list_paired_over_dataset(self):
        result = effective_map_over(c_t("list:paired"), NULL_COLLECTION_TYPE)
        assert result is not None
        assert result.collection_type == "list:paired"

    # -- sample_sheet --

    def test_sample_sheet_paired_over_paired(self):
        result = effective_map_over(c_t("sample_sheet:paired"), c_t("paired"))
        assert result is not None
        assert result.collection_type == "sample_sheet"

    # -- Returns None for incompatible --

    def test_incompatible_returns_none(self):
        assert effective_map_over(c_t("paired"), c_t("list")) is None
        assert effective_map_over(c_t("list:paired"), c_t("list")) is None
        assert effective_map_over(NULL_COLLECTION_TYPE, c_t("list")) is None

    def test_self_returns_none(self):
        assert effective_map_over(c_t("list"), c_t("list")) is None
