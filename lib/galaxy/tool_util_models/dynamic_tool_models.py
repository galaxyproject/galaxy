from typing import Literal

from pydantic import BaseModel

from galaxy.tool_util_models import (
    DynamicToolSources,
    UserToolSource,
)


class BaseDynamicToolCreatePayload(BaseModel):
    active: bool | None = None
    hidden: bool | None = None


class DynamicToolCreatePayload(BaseDynamicToolCreatePayload):
    src: Literal["representation"] = "representation"
    representation: DynamicToolSources
    active: bool | None = True
    hidden: bool | None = False


class DynamicUnprivilegedToolCreatePayload(DynamicToolCreatePayload):
    representation: UserToolSource


class PathBasedDynamicToolCreatePayload(BaseDynamicToolCreatePayload):
    src: Literal["from_path"]
    path: str
    tool_directory: str | None = None


DynamicToolPayload = DynamicToolCreatePayload | PathBasedDynamicToolCreatePayload
