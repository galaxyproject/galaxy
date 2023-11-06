from tool_shed.structured_app import ToolShedApp
from tool_shed_client.schema import Version
from . import (
    depends,
    Router,
)

router = Router(tags=["configuration"])


@router.cbv
class FastAPIConfiguration:
    app: ToolShedApp = depends(ToolShedApp)

    @router.get(
        "/api/version",
        operation_id="configuration__version",
    )
    def version(self) -> Version:
        return Version(
            version_major=self.app.config.version_major,
            version=self.app.config.version,
            api_version="v2",
        )
