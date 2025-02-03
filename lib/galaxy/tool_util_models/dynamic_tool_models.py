from typing import (
    Optional,
    Union,
)

from pydantic import BaseModel
from typing_extensions import Literal

from galaxy.tool_util_models import (
    DynamicToolSources,
    UserToolSource,
)


class BaseDynamicToolCreatePayload(BaseModel):
    active: Optional[bool] = None
    hidden: Optional[bool] = None


class DynamicToolCreatePayload(BaseDynamicToolCreatePayload):
    src: Literal["representation"] = "representation"
    representation: DynamicToolSources
    active: Optional[bool] = True
    hidden: Optional[bool] = False


class DynamicUnprivilegedToolCreatePayload(DynamicToolCreatePayload):
    representation: UserToolSource


class PathBasedDynamicToolCreatePayload(BaseDynamicToolCreatePayload):
    src: Literal["from_path"]
    path: str
    tool_directory: Optional[str] = None


DynamicToolPayload = Union[DynamicToolCreatePayload, PathBasedDynamicToolCreatePayload]
