from typing import (
    Literal,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BaseFile(Model):
    class_: Literal["File"] = Field(..., alias="class")
    filetype: Optional[str] = Field(None, description="Datatype extension for uploaded dataset.")
    dbkey: Optional[str] = None
    decompress: Optional[bool] = False
    to_posix_line: Optional[bool] = None
    space_to_tab: Optional[bool] = Field(None, description="If set, spaces in text datasets will be converted to tabs.")
    deferred: Optional[bool] = Field(
        None,
        description="If set, datasets will not be stored on disk, but will be downloaded when used as inputs. Can only be used if a remote URI is used instead of a local file.",
    )
    name: Optional[str] = Field(None, description="Name of dataset in history.")
    info: Optional[str] = None
    tags: Optional[list[str]] = Field(None, description="Tags to apply to uploaded dataset.")


class BaseFileElement(BaseFile):
    identifier: str


class LocationFile(BaseFile):
    location: str
    path: Optional[str] = None


class PathFile(BaseFile):
    path: str


class CompositeDataFile(BaseFile):
    location: Optional[str] = None
    path: Optional[str] = None
    composite_data: list[dict[Literal["path"], str]]


class LocationFileElement(BaseFileElement):
    location: str
    path: Optional[str] = None


class PathFileElement(BaseFileElement):
    path: str


class CompositeDataFileElement(BaseFileElement):
    location: Optional[str] = None
    path: Optional[str] = None
    composite_data: list[dict[Literal["path"], str]]


File = Union[LocationFile, PathFile, CompositeDataFile]
FileElement = Union[LocationFileElement, PathFileElement, CompositeDataFileElement]


class CollectionElement(BaseModel):
    class_: Literal["Collection"] = Field(..., alias="class")
    identifier: str
    elements: list[Union["CollectionElement", FileElement]]
    type: str = "list"  # is this correct ?


class Collection(BaseModel):
    class_: Literal["Collection"] = Field(..., alias="class")
    collection_type: str = "list"  # is this correct ?
    elements: list[Union[CollectionElement, FileElement]]


JobParamTypes = Union[str, int, float, bool, Collection, File]
AnyJobParam = Union[dict[str, Optional[Union[JobParamTypes, list[JobParamTypes]]]], str]


class Job(RootModel):
    root: AnyJobParam
