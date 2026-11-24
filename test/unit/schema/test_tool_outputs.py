import pytest
from pydantic import ValidationError

from galaxy.schema.tool_outputs import ToolOutputActions


@pytest.mark.parametrize(
    "rename, expected",
    [
        ("  sorted reads ", "sorted reads"),
        ("   ", None),
        ("", None),
    ],
)
def test_rename_is_stripped_and_blank_keeps_the_name(rename, expected):
    assert ToolOutputActions(rename=rename).rename == expected


@pytest.mark.parametrize("tag", ["two words", "name:", ".hidden", "group:x\ny"])
def test_rejects_invalid_tags(tag):
    with pytest.raises(ValidationError):
        ToolOutputActions(add_tags=[tag])


def test_rejects_too_long_rename():
    with pytest.raises(ValidationError):
        ToolOutputActions(rename="x" * 256)
