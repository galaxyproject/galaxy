from abc import abstractmethod
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from ..panel import (
    HasPanelItems,
    panel_item_types,
    ToolPanelElements,
)


class ToolPanelViewModelType(str, Enum):
    default_type = 'default'
    generic = 'generic'
    activity = 'activity'
    ontology = 'ontology'
    publication = 'publication'
    training = 'training'


class ToolPanelViewModel(BaseModel):
    """A view of ToolPanelView objects serialized for the API."""
    id: str
    model_class: str
    name: str
    description: Optional[str]
    view_type: ToolPanelViewModelType
    searchable: bool  # Allow for more dynamic views that don't plug into fixed search indicies in the future...


class ToolBoxRegistry:
    """View of ToolBox provided to ToolPanelView to reason about tools loaded."""

    @abstractmethod
    def has_tool(self, tool_id: str) -> bool:
        """Return bool indicating if tool with specified id is loaded."""

    @abstractmethod
    def get_tool(self, tool_id: str):
        """Return tool with supplied tool id."""

    @abstractmethod
    def get_workflow(self, id: str):
        """Return workflow from panel with supplied id."""

    @abstractmethod
    def add_tool_to_tool_panel_view(self, tool, tool_panel_component: HasPanelItems) -> None:
        """Add tool to the tool panel view component (root or section)."""


class ToolPanelView:

    @abstractmethod
    def apply_view(self, base_tool_panel: ToolPanelElements, toolbox_registry: ToolBoxRegistry) -> ToolPanelElements:
        """Consume tool panel state and return custom tool panel view."""

    @abstractmethod
    def to_model(self) -> ToolPanelViewModel:
        """Convert abstract description to dictionary description to emit via the API."""


def walk_loaded_tools(tool_panel: ToolPanelElements, toolbox_registry: ToolBoxRegistry):
    for key, item_type, val in tool_panel.panel_items_iter():
        if item_type == panel_item_types.TOOL:
            tool_id = key.replace('tool_', '', 1)
            if toolbox_registry.has_tool(tool_id):
                yield (tool_id, key, val, val.name)
        elif item_type == panel_item_types.SECTION:
            for section_key, section_item_type, section_val in val.panel_items_iter():
                if section_item_type == panel_item_types.TOOL:
                    tool_id = section_key.replace('tool_', '', 1)
                    if toolbox_registry.has_tool(tool_id):
                        yield (tool_id, key, section_val, val.name)
