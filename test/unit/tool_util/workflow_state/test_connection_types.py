"""Tests for galaxy.tool_util.workflow_state.connection_types.

Algebra cases (can_match, can_map_over, effective_map_over) are driven by
connection_type_cases.yml so the same corpus can be consumed by the TS
connection validator in galaxy-tool-util-ts. Sentinel property tests that
aren't naturally table-shaped stay here.
"""

import os
from typing import Union

import pytest
import yaml

from galaxy.tool_util.collections import COLLECTION_TYPE_DESCRIPTION_FACTORY as factory
from galaxy.tool_util.workflow_state.connection_types import (
    ANY_COLLECTION_TYPE,
    can_map_over,
    can_match,
    collection_type_rank,
    compatible,
    effective_map_over,
    NULL_COLLECTION_TYPE,
)

CASES_YAML = os.path.join(os.path.dirname(__file__), "connection_type_cases.yml")


def c_t(collection_type: str):
    return factory.for_collection_type(collection_type)


def _resolve(token: Union[str, None]):
    """Resolve a YAML token to a collection type object.

    YAML ``NULL`` / ``null`` / ``~`` all parse to Python ``None``; we treat
    that as the NULL_COLLECTION_TYPE sentinel so the cases file can use the
    natural spelling without quoting.
    """
    if token is None:
        return NULL_COLLECTION_TYPE
    if token == "ANY":
        return ANY_COLLECTION_TYPE
    return c_t(token)


def _load_cases():
    with open(CASES_YAML) as f:
        cases = yaml.safe_load(f)
    ids = []
    for case in cases:
        ref = case.get("semantics_ref", "")
        ids.append(f"{case['op']}[{case['output']}|{case['input']}]{('@' + ref) if ref else ''}")
    return cases, ids


_CASES, _IDS = _load_cases()


@pytest.mark.parametrize("case", _CASES, ids=_IDS)
def test_connection_type_case(case):
    op = case["op"]
    output = _resolve(case["output"])
    input_type = _resolve(case["input"])
    expected = case["expected"]
    if op == "can_match":
        assert can_match(output, input_type) is expected
    elif op == "can_map_over":
        assert can_map_over(output, input_type) is expected
    elif op == "compatible":
        assert compatible(output, input_type) is expected
    elif op == "effective_map_over":
        result = effective_map_over(output, input_type)
        if expected is None:
            assert result is None
        else:
            assert result is not None
            assert result.collection_type == expected
    else:
        raise AssertionError(f"unknown op: {op}")


# -- Sentinel property tests (not naturally table-shaped) --


class TestNullCollectionType:
    def test_not_a_collection(self):
        assert not NULL_COLLECTION_TYPE.is_collection

    def test_collection_type_is_none(self):
        assert NULL_COLLECTION_TYPE.collection_type is None

    def test_rank_is_zero(self):
        assert NULL_COLLECTION_TYPE.rank == 0


class TestAnyCollectionType:
    def test_is_a_collection(self):
        assert ANY_COLLECTION_TYPE.is_collection

    def test_collection_type_is_any(self):
        assert ANY_COLLECTION_TYPE.collection_type == "any"

    def test_rank_is_negative(self):
        assert ANY_COLLECTION_TYPE.rank == -1


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
