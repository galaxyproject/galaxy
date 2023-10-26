from typing import (
    List,
    Optional,
    Tuple,
    Union,
)

from pydantic import BaseModel
from typing_extensions import Literal


class BaseComment(BaseModel):
    id: int
    colour: Literal["none", "black", "blue", "turquoise", "green", "lime", "orange", "yellow", "red", "pink"]
    position: Tuple[float, float]
    size: Tuple[float, float]


class TextCommentData(BaseModel):
    bold: Optional[bool]
    italic: Optional[bool]
    size: int
    text: str


class TextComment(BaseComment):
    type: Literal["text"]
    data: TextCommentData


class MarkdownCommentData(BaseModel):
    text: str


class MarkdownComment(BaseComment):
    type: Literal["markdown"]
    data: MarkdownCommentData


class FrameCommentData(BaseModel):
    title: str


class FrameComment(BaseComment):
    type: Literal["frame"]
    data: FrameCommentData
    child_comments: Optional[List[int]]
    child_steps: Optional[List[int]]


class FreehandCommentData(BaseModel):
    thickness: int
    line: List[Tuple[float, float]]


class FreehandComment(BaseComment):
    type: Literal["freehand"]
    data: FreehandCommentData


class WorkflowCommentModel(BaseModel):
    __root__: Union[TextComment, MarkdownComment, FrameComment, FreehandComment]
