from typing import TYPE_CHECKING

from galaxy.structured_app import BasicSharedApp

if TYPE_CHECKING:
    from tool_shed.managers.tool_state_cache import ToolStateCache
    from tool_shed.repository_registry import Registry as RepositoryRegistry
    from tool_shed.repository_types.registry import Registry as RepositoryTypesRegistry
    from tool_shed.util.hgweb_config import HgWebConfigManager
    from tool_shed.webapp.model import mapping
    from tool_shed.webapp.security import CommunityRBACAgent


class ToolShedApp(BasicSharedApp):
    repository_types_registry: "RepositoryTypesRegistry"
    model: "mapping.ToolShedModelMapping"
    repository_registry: "RepositoryRegistry"
    hgweb_config_manager: "HgWebConfigManager"
    security_agent: "CommunityRBACAgent"
    tool_state_cache: "ToolStateCache"
