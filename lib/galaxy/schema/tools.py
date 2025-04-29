from typing import (
    Literal,
    Optional,
    Union,
)

from pydantic import BaseModel

from galaxy.tool_util.models import (
    DynamicToolSources,
    UserToolSource,
)


class BaseDynamicToolCreatePayload(BaseModel):
    active: Optional[bool] = None
    hidden: Optional[bool] = None
    uuid: Optional[str] = None


class DynamicToolCreatePayload(BaseDynamicToolCreatePayload):
    src: Literal["representation"] = "representation"
    representation: DynamicToolSources
    active: Optional[bool] = True
    hidden: Optional[bool] = False
    # TODO: split out, doesn't mean anything for unprivileged tools
    allow_load: Optional[bool] = True


class DynamicUnprivilegedToolCreatePayload(DynamicToolCreatePayload):
    representation: UserToolSource


class PathBasedDynamicToolCreatePayload(BaseDynamicToolCreatePayload):
    src: Literal["from_path"]
    path: str
    tool_directory: Optional[str] = None
    allow_load: bool = True


DynamicToolPayload = Union[DynamicToolCreatePayload, PathBasedDynamicToolCreatePayload]
