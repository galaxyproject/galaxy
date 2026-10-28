import pytest

from galaxy.tool_util.parser.interface import TestCollectionOutputDef
from galaxy.tool_util.verify.interactor import verify_collection


def _collection(n: int):
    elements = [{"element_identifier": f"e{i}", "element_type": "hda", "object": {}} for i in range(n)]
    return {"collection_type": "list", "elements": elements}


def _verify(attrib, n: int, element_count=None):
    output_def = TestCollectionOutputDef("out", attrib, {}, element_count=element_count)
    verify_collection(output_def, _collection(n), lambda *args, **kwd: None)


@pytest.mark.parametrize(
    "attrib,n",
    [
        ({}, 0),
        ({}, 2),
        ({"count": "2"}, 2),
        ({"min": "1"}, 2),
        ({"max": "2"}, 2),
        ({"min": "0"}, 0),
        ({"count": "0"}, 0),
        ({"max": "0"}, 0),
    ],
)
def test_verify_collection_size_pass(attrib, n):
    _verify(attrib, n)


@pytest.mark.parametrize(
    "attrib,n,message",
    [
        ({"count": "2"}, 1, "expected to have 2 elements, but it had 1"),
        ({"min": "2"}, 1, "expected to have at least 2 elements, but it had 1"),
        ({"max": "1"}, 2, "expected to have at most 1 elements, but it had 2"),
    ],
)
def test_verify_collection_size_fail(attrib, n, message):
    with pytest.raises(AssertionError, match=message):
        _verify(attrib, n)


def test_verify_collection_element_count_fail():
    with pytest.raises(AssertionError, match="expected to have 2 elements, but it had 1"):
        _verify({}, 1, element_count=2)
