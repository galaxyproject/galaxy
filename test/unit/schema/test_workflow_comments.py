import pytest
from pydantic import ValidationError

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
