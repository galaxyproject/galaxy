from typing import (
    List,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
)


class TourCore(BaseModel):
    name: str = Field(title="Name", description="Name of tour")
    description: str = Field(title="Description", description="Tour description")
    tags: List[str] = Field(title="Tags", description="Topic topic tags")


class Tour(TourCore):
    id: str = Field(title="Identifier", description="Tour identifier")


class TourList(BaseModel):
    __root__: List[Tour] = Field(title="List of tours", default=[])


class TourStep(BaseModel):
    title: Optional[str] = Field(title="Title", description="Title displayed in the header of the step container")
    content: Optional[str] = Field(title="Content", description="Text shown to the user")
    element: Optional[str] = Field(
        title="Element", description="JQuery selector for the element to be described/clicked"
    )
    placement: Optional[str] = Field(
        title="Placement", description="Placement of the text box relative to the selected element"
    )
    preclick: Optional[Union[bool, List[str]]] = Field(
        title="Pre-click", description="Elements that receive a click() event before the step is shown"
    )
    postclick: Optional[Union[bool, List[str]]] = Field(
        title="Post-click", description="Elements that receive a click() event after the step is shown"
    )
    textinsert: Optional[str] = Field(
        title="Text-insert", description="Text to insert if element is a text box (e.g. tool search or upload)"
    )


class TourDetails(TourCore):
    title_default: Optional[str] = Field(title="Default title", description="Default title for each step")
    steps: List[TourStep] = Field(title="Steps", description="Tour steps")
