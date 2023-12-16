from tool_shed.structured_app import ToolShedApp
from tool_shed_client.schema import Version
from . import (
    depends,
    Router,
)

router = Router(tags=["configuration"])


@router.get(
    "/api/version",
    operation_id="configuration__version",
)
def version(app: ToolShedApp = depends(ToolShedApp)) -> Version:
    return Version(
        version_major=app.config.version_major,
        version=app.config.version,
        api_version="v2",
    )
