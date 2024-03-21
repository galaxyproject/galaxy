from typing import (
    List,
    Optional,
    Tuple,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
    RootModel,
)
from typing_extensions import Literal


class BaseComment(BaseModel):
    id: int = Field(..., description="Unique identifier for this comment. Determined by the comments order")
    color: Literal["none", "black", "blue", "turquoise", "green", "lime", "orange", "yellow", "red", "pink"] = Field(
        ..., description="Color this comment is displayed as. The exact color hex is determined by the client"
    )
    position: Tuple[float, float] = Field(..., description="[x, y] position of this comment in the Workflow")
    size: Tuple[float, float] = Field(..., description="[width, height] size of this comment")


class TextCommentData(BaseModel):
    bold: Optional[bool] = Field(
        default=None, description="If the Comments text is bold. Absent is interpreted as false"
    )
    italic: Optional[bool] = Field(
        default=None, description="If the Comments text is italic. Absent is interpreted as false"
    )
    size: int = Field(..., description="Relative size (1 -> 100%) of the text compared to the default text sitz")
    text: str = Field(..., description="The plaintext text of this comment")


class TextComment(BaseComment):
    type: Literal["text"]
    data: TextCommentData


class MarkdownCommentData(BaseModel):
    text: str = Field(..., description="The unrendered source Markdown for this Comment")


class MarkdownComment(BaseComment):
    type: Literal["markdown"]
    data: MarkdownCommentData


class FrameCommentData(BaseModel):
    title: str = Field(..., description="The Frames title")


class FrameComment(BaseComment):
    type: Literal["frame"]
    data: FrameCommentData
    child_comments: Optional[List[int]] = Field(
        default=None, description="A list of ids (see `id`) of all Comments which are encompassed by this Frame"
    )
    child_steps: Optional[List[int]] = Field(
        default=None, description="A list of ids of all Steps (see WorkflowStep.id) which are encompassed by this Frame"
    )


class FreehandCommentData(BaseModel):
    thickness: int = Field(..., description="Width of the Line in pixels")
    line: List[Tuple[float, float]] = Field(
        ...,
        description="List of [x, y] coordinates determining the unsmoothed line. Smoothing is done client-side using Catmull-Rom",
    )


class FreehandComment(BaseComment):
    type: Literal["freehand"]
    data: FreehandCommentData


class WorkflowCommentModel(RootModel):
    root: Union[TextComment, MarkdownComment, FrameComment, FreehandComment] = Field(..., discriminator="type")
