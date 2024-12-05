from typing import (
    Literal,
    Optional,
    Union,
)

from pydantic import BaseModel

from galaxy.tool_util.models import DynamicToolSources


class BaseDynamicToolCreatePayload(BaseModel):
    allow_load: bool = True
    uuid: Optional[str] = None
    active: Optional[bool] = None
    hidden: Optional[bool] = None
    tool_directory: Optional[str] = None


class DynamicToolCreatePayload(BaseDynamicToolCreatePayload):
    src: Literal["representation"] = "representation"
    representation: DynamicToolSources


class PathBasedDynamicToolCreatePayload(BaseDynamicToolCreatePayload):
    src: Literal["from_path"]
    path: str


DynamicToolPayload = Union[DynamicToolCreatePayload, PathBasedDynamicToolCreatePayload]
