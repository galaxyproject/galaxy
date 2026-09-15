import pytest
from pydantic import ValidationError

from galaxy.model import WorkflowComment
from galaxy.schema.workflow.comments import WorkflowCommentModel


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


def test_comment_color_defaults_to_none():
    comment = WorkflowCommentModel.model_validate(_comment_dict())

    assert comment.root.color == "none"


def test_comment_color_accepts_none():
    comment = WorkflowCommentModel.model_validate(_comment_dict(color=None))

    assert comment.root.color is None


def test_comment_color_accepts_named_color():
    comment = WorkflowCommentModel.model_validate(_comment_dict(color="red"))

    assert comment.root.color == "red"


def test_comment_color_rejects_unknown_value():
    with pytest.raises(ValidationError):
        WorkflowCommentModel.model_validate(_comment_dict(color="chartreuse"))


@pytest.mark.parametrize("comment_dict", [_comment_dict(), _comment_dict(color=None)])
def test_comment_color_is_normalized_during_import(comment_dict):
    comment = WorkflowComment.from_dict(comment_dict)

    assert comment.color == "none"


def test_null_database_comment_color_is_normalized_during_export():
    comment = WorkflowComment.from_dict(_comment_dict())
    comment.color = None

    assert comment.to_dict()["color"] == "none"
