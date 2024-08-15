from enum import Enum
from typing import (
    List,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
)


class Requirement(str, Enum):
    """Available types of job sources (model classes) that produce dataset collections."""

    LOGGED_IN = "logged_in"
    NEW_HISTORY = "new_history"
    ADMIN = "admin"


class TourCore(BaseModel):
    name: str = Field(title="Name", description="Name of tour")
    description: str = Field(title="Description", description="Tour description")
    tags: List[str] = Field(title="Tags", description="Topic topic tags")
    requirements: List[Requirement] = Field(title="Requirements", description="Requirements to run the tour.")
    model_config = ConfigDict(use_enum_values=True)


class Tour(TourCore):
    id: str = Field(title="Identifier", description="Tour identifier")


class TourList(RootModel):
    root: List[Tour] = Field(title="List of tours", default=[])


class TourStep(BaseModel):
    title: Optional[str] = Field(None, title="Title", description="Title displayed in the header of the step container")
    content: Optional[str] = Field(None, title="Content", description="Text shown to the user")
    element: Optional[str] = Field(
        None, title="Element", description="CSS selector for the element to be described/clicked"
    )
    placement: Optional[str] = Field(
        None, title="Placement", description="Placement of the text box relative to the selected element"
    )
    preclick: Optional[Union[bool, List[str]]] = Field(
        None, title="Pre-click", description="Elements that receive a click() event before the step is shown"
    )
    postclick: Optional[Union[bool, List[str]]] = Field(
        None, title="Post-click", description="Elements that receive a click() event after the step is shown"
    )
    textinsert: Optional[str] = Field(
        None, title="Text-insert", description="Text to insert if element is a text box (e.g. tool search or upload)"
    )


class TourDetails(TourCore):
    title_default: Optional[str] = Field(None, title="Default title", description="Default title for each step")
    steps: List[TourStep] = Field(title="Steps", description="Tour steps")
