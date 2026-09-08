import pytest
from pydantic import ValidationError

from galaxy.schema.workflow.comments import WorkflowCommentModel


def test_comment_color_defaults_to_none():
    comment = WorkflowCommentModel(
        root={
            "id": 0,
            "type": "frame",
            "position": [0, 0],
            "size": [260, 180],
            "data": {"title": "Quality control"},
            "child_steps": [1],
        }
    )

    assert comment.root.color == "none"


def test_comment_color_rejects_unknown_value():
    with pytest.raises(ValidationError):
        WorkflowCommentModel(
            root={
                "id": 0,
                "type": "frame",
                "position": [0, 0],
                "size": [260, 180],
                "color": "chartreuse",
                "data": {"title": "Quality control"},
                "child_steps": [1],
            }
        )
