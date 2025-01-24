from typing import TYPE_CHECKING

from galaxy.structured_app import BasicSharedApp

if TYPE_CHECKING:
    from tool_shed.managers.model_cache import ModelCache
    from tool_shed.repository_registry import RegistryInterface
    from tool_shed.repository_types.registry import Registry as RepositoryTypesRegistry
    from tool_shed.util.hgweb_config import HgWebConfigManager
    from tool_shed.webapp.model import mapping
    from tool_shed.webapp.security import CommunityRBACAgent


class ToolShedApp(BasicSharedApp):
    repository_types_registry: "RepositoryTypesRegistry"
    model: "mapping.ToolShedModelMapping"
    repository_registry: "RegistryInterface"
    hgweb_config_manager: "HgWebConfigManager"
    security_agent: "CommunityRBACAgent"
    model_cache: "ModelCache"
