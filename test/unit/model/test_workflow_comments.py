import pytest

from galaxy.model import WorkflowComment


def _comment_dict(**kwds):
    comment = {
        "id": 0,
        "type": "frame",
        "position": [0, 0],
        "size": [260, 180],
        "data": {"title": "Quality control"},
        "child_steps": [1],
    }
    comment.update(kwds)
    return comment


@pytest.mark.parametrize("comment_dict", [_comment_dict(), _comment_dict(color=None)])
def test_comment_color_is_normalized_during_import(comment_dict):
    comment = WorkflowComment.from_dict(comment_dict)

    assert comment.color == "none"


def test_null_database_comment_color_is_normalized_during_export():
    comment = WorkflowComment.from_dict(_comment_dict())
    comment.color = None

    assert comment.to_dict()["color"] == "none"


def test_named_comment_color_is_preserved_during_import_and_export():
    comment = WorkflowComment.from_dict(_comment_dict(color="red"))

    assert comment.color == "red"
    assert comment.to_dict()["color"] == "red"
