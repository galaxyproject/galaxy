from typing import TYPE_CHECKING

from galaxy.structured_app import BasicSharedApp

if TYPE_CHECKING:
    from tool_shed.repository_types.registry import Registry as RepositoryTypesRegistry
    from tool_shed.webapp.model import mapping


class ToolShedApp(BasicSharedApp):
    repository_types_registry: "RepositoryTypesRegistry"
    model: "mapping.ToolShedModelMapping"
