import logging
import re
from typing import Optional

from .definitions import (
    ExcludeTool,
    ExcludeToolRegex,
    ExcludeTypes,
    ExpandedRootContent,
    Label,
    Section,
    SectionAlias,
    StaticToolBoxView,
    Tool,
    Workflow,
)
from .interface import (
    ToolBoxRegistry,
    ToolPanelView,
    ToolPanelViewModel,
    ToolPanelViewModelType,
)
from ..panel import (
    panel_item_types,
    ToolPanelElements,
    ToolSection,
    ToolSectionLabel,
)


log = logging.getLogger(__name__)


def build_filter(excludes_):
    excludes = excludes_ or []

    def filter_function(panel_key, panel_value):
        for exclude in excludes:
            if panel_key.startswith("tool_"):
                if isinstance(exclude, ExcludeTool):
                    if panel_value.id == exclude.tool_id:
                        return False
                    if panel_value.old_id == exclude.tool_id:
                        return False

                if isinstance(exclude, ExcludeToolRegex):
                    if re.match(exclude.tool_id_regex, panel_value.id):
                        return False
                    if re.match(exclude.tool_id_regex, panel_value.old_id):
                        return False

            if isinstance(exclude, ExcludeTypes):
                if panel_key.startswith("label_") and "label" in exclude.types:
                    return False
                if panel_key.startswith("tool_") and "tool" in exclude.types:
                    return False
                if panel_key.startswith("workflow_") and "workflow" in exclude.types:
                    return False

        return True

    return filter_function


class StaticToolPanelView(ToolPanelView):
    _definition: StaticToolBoxView

    def __init__(self, definition: StaticToolBoxView):
        self._definition = definition

    def apply_view(self, base_tool_panel: ToolPanelElements, toolbox_registry: ToolBoxRegistry) -> ToolPanelElements:

        def apply_filter(definition, elems):
            excludes = self._all_excludes(definition)
            if excludes:
                elems.apply_filter(build_filter(excludes))

        def definition_with_items_to_panel(definition, allow_sections: bool = True, items=None):
            new_panel = ToolPanelElements()
            if items is None:
                items = definition.items_expanded
            for element in items:
                if element.content_type == "section":
                    assert allow_sections
                    section_def: Section = element
                    section: ToolSection
                    assert section_def.id is not None or section_def.name is not None
                    if element.items:
                        panel = definition_with_items_to_panel(section_def, allow_sections=False)
                        section = ToolSection()
                        if section_def.name is not None:
                            name = section_def.name
                        else:
                            assert section_def.id is not None
                            name = section_def.id
                        section.name = name
                        if section_def.id is not None:
                            section.id = section_def.id
                        else:
                            # TODO: there has to be tool shed code to do this in a consistent way... where is it?
                            section.id = name.replace(" ", "-").lower()
                        section.elems = panel
                    else:
                        closest_section = base_tool_panel.closest_section(section_def.id, section_def.name)
                        if closest_section is None:
                            log.warning(f"Failed to find matching section for (id, name) = ({section_def.id}, {section_def.name})")
                            continue
                        section = closest_section.copy()
                        if section_def.id is not None:
                            section.id = section_def.id
                        if section_def.name is not None:
                            section.name = section_def.name
                        apply_filter(section_def, section.elems)
                    new_panel.append_section(section.id, section)
                elif element.content_type == "section_alias":
                    assert allow_sections
                    closest_section = base_tool_panel.closest_section(element.section, element.section)
                    if closest_section is None:
                        log.warning(f"Failed to find matching section for (id, name) = ({element.section}, {element.section})")
                        continue
                    section = closest_section.copy()
                    apply_filter(element, section.elems)
                    new_panel.append_section(section.id, section)
                elif element.content_type == "label":
                    as_dict = {
                        "id": element.id or element.text.lower().replace(" ", "-"),
                        "text": element.text,
                        "type": "label",
                    }
                    label = ToolSectionLabel(as_dict)
                    key = f"label_{label.id}"
                    new_panel[key] = label
                elif element.content_type == "tool":
                    tool_id = element.id
                    if not toolbox_registry.has_tool(tool_id):
                        log.warning(f"Failed to find tool_id {tool_id} from parent toolbox, cannot load into panel view")
                        continue
                    tool = toolbox_registry.get_tool(tool_id)
                    toolbox_registry.add_tool_to_tool_panel_view(tool, new_panel)
                elif element.content_type == "workflow":
                    workflow_def: Workflow = element
                    workflow = toolbox_registry.get_workflow(element.id)
                    panel_id = f"workflow_{workflow_def.id}"
                    new_panel[panel_id] = workflow
                elif element.content_type == "items_from":
                    closest_section = base_tool_panel.closest_section(element.items_from, element.items_from)
                    if closest_section is None:
                        log.warning(f"Failed to find matching section for (id, name) = ({element.items_from}, None)")
                        continue
                    elems = closest_section.elems.copy()
                    apply_filter(element, elems)
                    for key, item in elems.items():
                        new_panel[key] = item
                else:
                    raise AssertionError("Unknown static toolbox configuration element encountered.")

            excludes = self._all_excludes(definition)
            if excludes:
                new_panel.apply_filter(build_filter(excludes))

            return new_panel

        root_defintion = self._definition
        root_items = root_defintion.items_expanded
        if root_items is None:
            root_items = []
            # No items found, use base tool panel and apply filters to that...
            for (_, panel_type, panel_value) in base_tool_panel.panel_items_iter():
                item: Optional[ExpandedRootContent] = None
                if panel_type == panel_item_types.TOOL:
                    item = Tool(
                        id=panel_value.id,
                    )
                elif panel_type == panel_item_types.SECTION:
                    item = SectionAlias(
                        section=panel_value.id,
                    )
                elif panel_type == panel_item_types.LABEL:
                    item = Label(
                        id=panel_value.id,
                        text=panel_value.text,
                    )
                elif panel_type == panel_item_types.WORKFLOW:
                    item = Workflow(
                        id=panel_value.id,
                    )
                if item is None:
                    raise Exception("Unknown panel item type encountered.")
                root_items.append(item)

        return definition_with_items_to_panel(root_defintion, items=root_items)

    def _all_excludes(self, has_excludes):
        excludes = has_excludes.excludes or []
        if has_excludes != self._definition and self._definition.excludes:
            excludes.extend(self._definition.excludes)
        return excludes

    def to_model(self) -> ToolPanelViewModel:
        model_id = self._definition.id
        name = self._definition.name
        description = self._definition.description
        view_type = ToolPanelViewModelType[self._definition.view_type.value]
        model_class = self.__class__.__name__
        return ToolPanelViewModel(
            id=model_id,
            name=name,
            description=description,
            model_class=model_class,
            view_type=view_type,
            searchable=True,
        )
