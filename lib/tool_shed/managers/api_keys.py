from galaxy.managers.api_keys import ApiKeyManager
from tool_shed.webapp.model import APIKeys, User


class ToolShedApiKeyManager(ApiKeyManager[APIKeys, User]):
    pass
