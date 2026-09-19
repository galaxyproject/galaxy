"""The tool panel entry contract.

``ToolPanelEntry`` is the complete payload the tool panel and flat tool
listing emit per tool (``/api/tools``, ``/api/tool_panels/{view}``) — the
shape ``client/src/stores/toolStore.ts`` consumes. ``Tool.to_panel_entry``
produces it; :meth:`AbstractToolBox.get_tool_to_dict` serializes panels
exclusively through it.

Every field must be derivable without runtime state beyond the tool source
and toolbox registries (no job/user data), so a toolbox implementation can
serve the same payload from pre-computed metadata instead of a parsed
``Tool``. Additions to the panel payload belong here, not in ad-hoc dict
keys, so that alternative producers fail loudly when the contract grows.
"""

from typing import (
    Any,
    Literal,
)

from pydantic import (
    BaseModel,
    ConfigDict,
)


class ToolShedRepositoryInfo(BaseModel):
    name: str | None
    owner: str | None
    changeset_revision: str | None
    tool_shed: str | None


class ToolPanelEntry(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_class: str
    id: str
    name: str
    version: str
    description: str | None
    labels: list[Any]
    icon: str | None
    edam_operations: list[str]
    edam_topics: list[str]
    hidden: bool | str
    is_workflow_compatible: bool
    xrefs: list[dict[str, Any]]
    versions: list[str]
    hidden_versions: list[str]
    link: str
    has_parameters: bool
    panel_section_id: str | None
    panel_section_name: str | None
    form_style: Literal["regular", "special"]
    # Present only for dynamic tools.
    uuid: str | None = None
    # Present only for shed-installed tools.
    tool_shed_repository: ToolShedRepositoryInfo | None = None
    # Present only for admin users.
    config_file: str | None = None


__all__ = ("ToolPanelEntry", "ToolShedRepositoryInfo")
