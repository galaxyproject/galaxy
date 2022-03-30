from abc import abstractmethod
from enum import Enum
from typing import (
    Dict,
    Optional,
    Tuple,
)

from galaxy.util.dictifiable import Dictifiable
from galaxy.util.odict import odict
from .parser import ensure_tool_conf_item


class panel_item_types(str, Enum):
    TOOL = "TOOL"
    WORKFLOW = "WORKFLOW"
    SECTION = "SECTION"
    LABEL = "LABEL"


class HasPanelItems:
    """ """

    @abstractmethod
    def panel_items(self):
        """Return an ordered dictionary-like object describing tool panel
        items (such as workflows, tools, labels, and sections).
        """

    def panel_items_iter(self):
        """Iterate through panel items each represented as a tuple of
        (panel_key, panel_type, panel_content).
        """
        for panel_key, panel_value in self.panel_items().items():
            if panel_value is None:
                continue
            panel_type = panel_item_types.SECTION
            if panel_key.startswith("tool_"):
                panel_type = panel_item_types.TOOL
            elif panel_key.startswith("label_"):
                panel_type = panel_item_types.LABEL
            elif panel_key.startswith("workflow_"):
                panel_type = panel_item_types.WORKFLOW
            yield (panel_key, panel_type, panel_value)


class ToolSection(Dictifiable, HasPanelItems):
    """
    A group of tools with similar type/purpose that will be displayed as a
    group in the user interface.
    """

    dict_collection_visible_keys = ["id", "name", "version", "description", "links"]

    def __init__(self, item=None):
        """Build a ToolSection from an ElementTree element or a dictionary."""
        if item is None:
            item = dict()
        self.name = item.get("name") or ""
        self.id = item.get("id") or ""
        self.version = item.get("version") or ""
        self.description = item.get("description") or None
        self.links = item.get("links") or None
        self.elems = ToolPanelElements()

    def copy(self):
        copy = ToolSection()
        copy.name = self.name
        copy.id = self.id
        copy.version = self.version
        copy.description = self.description
        copy.links = self.links
        copy.elems.update(self.elems)
        return copy

    def to_dict(self, trans, link_details=False, tool_help=False, toolbox=None):
        """Return a dict that includes section's attributes."""

        section_dict = super().to_dict()
        section_elts = []
        kwargs = dict(trans=trans, link_details=link_details, tool_help=tool_help)
        for elt in self.elems.values():
            if hasattr(elt, "tool_type") and toolbox:
                section_elts.append(toolbox.get_tool_to_dict(trans, elt, tool_help=tool_help))
            else:
                section_elts.append(elt.to_dict(**kwargs))
        section_dict["elems"] = section_elts

        return section_dict

    def panel_items(self):
        return self.elems


class ToolSectionLabel(Dictifiable):
    """
    A label for a set of tools that can be displayed above groups of tools
    and sections in the user interface
    """

    dict_collection_visible_keys = ["id", "text", "version", "description", "links"]

    def __init__(self, item):
        """Build a ToolSectionLabel from an ElementTree element or a
        dictionary.
        """
        item = ensure_tool_conf_item(item)
        self.text = item.get("text")
        self.id = item.get("id")
        self.version = item.get("version") or ""
        self.description = item.get("description") or None
        self.links = item.get("links", None)

    def to_dict(self, **kwds):
        return super().to_dict()


class ToolPanelElements(odict, HasPanelItems):
    """Represents an ordered dictionary of tool entries - abstraction
    used both by tool panel itself (normal and integrated) and its sections.
    """

    _section_by_tool: Dict[str, Tuple[str, str]] = {}

    def record_section_for_tool_id(self, tool_id: str, key: str, val: str):
        self._section_by_tool[tool_id] = (key, val)

    def get_section_for_tool_id(self, tool_id: str) -> Tuple[Optional[str], Optional[str]]:
        if tool_id in self._section_by_tool:
            return self._section_by_tool[tool_id]
        return (None, None)

    def replace_tool_for_id(self, tool_id: str, new_tool) -> None:
        tool_key = f"tool_{tool_id}"
        for key, val in self.items():
            if key == tool_key:
                self[key] = new_tool
                break
            elif key.startswith("section"):
                if tool_key in val.elems:
                    self[key].elems[tool_key] = new_tool
                    break

    def get_or_create_section(
        self, sec_id: str, sec_nm: str, description: Optional[str] = None, links: Optional[Dict[str, str]] = None
    ) -> ToolSection:
        if sec_id not in self:
            section = ToolSection(
                {"id": sec_id, "name": sec_nm, "description": description, "version": "", "links": links}
            )
            self[sec_id] = section
        else:
            section = self[sec_id]
        return section

    def remove_tool(self, tool_id: str) -> None:
        tool_key = f"tool_{tool_id}"
        for key, val in self.items():
            if key == tool_key:
                del self[key]
                break
            elif key.startswith("section"):
                if tool_key in val.elems:
                    del self[key].elems[tool_key]
                    break

    def update_or_append(self, index: int, key: str, value) -> None:
        if key in self or index is None:
            self[key] = value
        else:
            self.insert(index, key, value)

    def get_label(self, label: str) -> Optional[ToolSection]:
        for element in self.values():
            if isinstance(element, ToolSection) and element.name == label:
                return element
        return None

    def has_tool_with_id(self, tool_id: str) -> bool:
        key = f"tool_{tool_id}"
        return key in self

    def replace_tool(self, previous_tool_id: str, new_tool_id: str, tool) -> None:
        previous_key = f"tool_{previous_tool_id}"
        new_key = f"tool_{new_tool_id}"
        index = self.keys().index(previous_key)
        del self[previous_key]
        self.insert(index, new_key, tool)

    def index_of_tool_id(self, tool_id: str) -> Optional[int]:
        query_key = f"tool_{tool_id}"
        for index, target_key in enumerate(self.keys()):
            if query_key == target_key:
                return index
        return None

    def insert_tool(self, index: int, tool) -> None:
        key = f"tool_{tool.id}"
        self.insert(index, key, tool)

    def get_tool_with_id(self, tool_id: str):
        key = f"tool_{tool_id}"
        return self[key]

    def append_tool(self, tool) -> None:
        key = f"tool_{tool.id}"
        self[key] = tool

    def stub_tool(self, key: str) -> None:
        key = f"tool_{key}"
        self[key] = None

    def stub_workflow(self, key: str) -> None:
        key = f"workflow_{key}"
        self[key] = None

    def stub_label(self, key: str) -> None:
        key = f"label_{key}"
        self[key] = None

    def append_section(self, key: str, section: ToolSection) -> None:
        self[key] = section

    def panel_items(self):
        return self

    def walk_sections(self):
        for key, item in self.items():
            if isinstance(item, ToolSection):
                yield (key, item)

    def closest_section(self, target_section_id: Optional[str], target_section_name: Optional[str]):
        for (section_id, section) in self.walk_sections():
            if section_id == target_section_id:
                return section

        for (_, section) in self.walk_sections():
            if section.name == target_section_name:
                return section

        return None

    def apply_filter(self, f):
        to_remove = []

        for key, item in self.items():
            if not f(key, item):
                to_remove.append(key)

        for key in to_remove:
            del self[key]

    def copy(self) -> "ToolPanelElements":
        the_copy = ToolPanelElements()
        the_copy.update(self)
        return the_copy

    def has_item_recursive(self, item):
        """Check panel and section elements for supplied item."""
        for value in self.values():
            if value == item:
                return True
            if isinstance(value, ToolSection):
                if item in value.elems.values():
                    return True
        return False
