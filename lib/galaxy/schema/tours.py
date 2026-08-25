from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
)


class Requirement(str, Enum):
    """Requirements that must be met for a tour to be runnable. The client lets the user know if any of the requirements are not met."""

    LOGGED_IN = "logged_in"
    NEW_HISTORY = "new_history"
    ADMIN = "admin"


class Prerequisite(str, Enum):
    """Available prerequisite operations that can be tried when a step fails due to an element not being interactable."""

    ENSURE_HISTORY_PANEL_OPEN = "ensure_history_panel_open"
    ENSURE_TOOL_PANEL_OPEN = "ensure_tool_panel_open"
    ENSURE_UPLOAD_OPEN = "ensure_upload_open"


class TourCore(BaseModel):
    name: str = Field(title="Name", description="Name of tour")
    description: str = Field(title="Description", description="Tour description")
    tags: list[str] = Field(title="Tags", description="Topic topic tags")
    requirements: list[Requirement] = Field(title="Requirements", description="Requirements to run the tour.")
    model_config = ConfigDict(use_enum_values=True)


class Tour(TourCore):
    id: str = Field(title="Identifier", description="Tour identifier")


class TourList(RootModel):
    root: list[Tour] = Field(title="List of tours", default=[])


class TourStep(BaseModel):
    title: str | None = Field(
        default=None, title="Title", description="Title displayed in the header of the step container"
    )
    content: str | None = Field(default=None, title="Content", description="Text shown to the user")
    element: str | None = Field(
        default=None, title="Element", description="CSS selector for the element to be described/clicked"
    )
    placement: str | None = Field(
        default=None, title="Placement", description="Placement of the text box relative to the selected element"
    )
    preclick: bool | list[str] | None = Field(
        default=None, title="Pre-click", description="Elements that receive a click() event before the step is shown"
    )
    prerequisites: list[Prerequisite] | None = Field(
        default=None,
        title="Prerequisites",
        description="Prerequisite operations that can be tried when a step fails due to an element not being interactable",
    )
    postclick: bool | list[str] | None = Field(
        default=None, title="Post-click", description="Elements that receive a click() event after the step is shown"
    )
    textinsert: str | None = Field(
        default=None,
        title="Text-insert",
        description="Text to insert if element is a text box (e.g. tool search or upload)",
    )
    orphan: bool | None = Field(default=None, title="Orphan", description="If true, the step is an orphan step")
    stops_autoplay: bool | None = Field(
        default=None,
        title="Stops autoplay",
        description="If true, the step stops autoplaying the tour until the user clicks the next button. Typically set for steps that require a user action",
    )


class TourDetails(TourCore):
    title_default: str | None = Field(None, title="Default title", description="Default title for each step")
    steps: list[TourStep] = Field(title="Steps", description="Tour steps")
