import json
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import (
    ConfigDict,
    Field,
    field_validator,
    Json,
)
from typing_extensions import (
    Annotated,
    Literal,
)

from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import Model
from galaxy.schema.types import CoercedStringType


class FetchBaseModel(Model):
    model_config = ConfigDict(populate_by_name=True)


class ElementsFromType(str, Enum):
    archive = "archive"
    bagit = "bagit"
    bagit_archive = "bagit_archive"
    directory = "directory"


AutoDecompressField = Field(False, description="Decompress compressed data before sniffing?")


class BaseFetchDataTarget(FetchBaseModel):
    auto_decompress: bool = AutoDecompressField


class ItemsFromSrc(str, Enum):
    url = "url"
    files = "files"
    path = "path"
    ftp_import = "ftp_import"
    server_dir = "server_dir"


class Src(str, Enum):
    url = "url"
    pasted = "pasted"
    files = "files"
    path = "path"
    composite = "composite"
    ftp_import = "ftp_import"
    server_dir = "server_dir"


class DestinationType(str, Enum):
    library = "library"
    library_folder = "library_folder"
    hdcas = "hdcas"
    hdas = "hdas"


class HdaDestination(FetchBaseModel):
    type: Literal["hdas"]


class HdcaDestination(FetchBaseModel):
    type: Literal["hdca"]


class LibraryFolderDestination(FetchBaseModel):
    type: Literal["library_folder"]
    library_folder_id: DecodedDatabaseIdField  # For some reason this folder ID must NOT have the 'F' prefix


class BaseCollectionTarget(BaseFetchDataTarget):
    destination: HdcaDestination
    collection_type: Optional[str] = None
    tags: Optional[List[str]] = None
    name: Optional[str] = None


class LibraryDestination(FetchBaseModel):
    type: Literal["library"]
    name: str = Field(..., description="Must specify a library name")
    description: Optional[str] = Field(None, description="Description for library to create")
    synopsis: Optional[str] = Field(None, description="Description for library to create")


class ExtraFiles(FetchBaseModel):
    items_from: Optional[str] = None
    src: Src
    fuzzy_root: Optional[bool] = Field(
        True,
        description="Prevent Galaxy from checking for a single file in a directory and re-interpreting the archive",
    )


class FetchDatasetHash(Model):
    hash_function: Literal["MD5", "SHA-1", "SHA-256", "SHA-512"]
    hash_value: str

    model_config = ConfigDict(extra="forbid")


class BaseDataElement(FetchBaseModel):
    name: Optional[CoercedStringType] = None
    dbkey: str = Field("?")
    info: Optional[str] = None
    ext: str = Field("auto")
    space_to_tab: bool = False
    to_posix_lines: bool = False
    deferred: bool = False
    tags: Optional[List[str]] = None
    created_from_basename: Optional[str] = None
    extra_files: Optional[ExtraFiles] = None
    auto_decompress: bool = AutoDecompressField
    items_from: Optional[ElementsFromType] = Field(None, alias="elements_from")
    collection_type: Optional[str] = None
    MD5: Optional[str] = None
    SHA1: Optional[str] = Field(None, alias="SHA-1")
    SHA256: Optional[str] = Field(None, alias="SHA-256")
    SHA512: Optional[str] = Field(None, alias="SHA-512")
    hashes: Optional[List[FetchDatasetHash]] = None
    description: Optional[str] = None
    model_config = ConfigDict(extra="forbid")


class FileDataElement(BaseDataElement):
    src: Literal["files"]


class PastedDataElement(BaseDataElement):
    src: Literal["pasted"]
    paste_content: CoercedStringType = Field(..., description="Content to upload")


class UrlDataElement(BaseDataElement):
    src: Literal["url"]
    url: str = Field(..., description="URL to upload")


class ServerDirElement(BaseDataElement):
    src: Literal["server_dir"]
    server_dir: str
    link_data_only: Optional[bool] = None


class FtpImportElement(BaseDataElement):
    src: Literal["ftp_import"]
    ftp_path: str
    collection_type: Optional[str] = None


class ItemsFromModel(Model):
    src: ItemsFromSrc
    path: Optional[str] = None
    ftp_path: Optional[str] = None
    server_dir: Optional[str] = None
    url: Optional[str] = None


class FtpImportTarget(BaseCollectionTarget):
    src: Literal["ftp_import"]
    ftp_path: str
    items_from: Optional[ElementsFromType] = Field(None, alias="elements_from")


class PathDataElement(BaseDataElement):
    src: Literal["path"]
    path: str
    items_from: Optional[ElementsFromType] = Field(None, alias="elements_from")
    link_data_only: Optional[bool] = None


class CompositeDataElement(BaseDataElement):
    src: Literal["composite"]
    composite: "CompositeItems"
    metadata: Optional[Dict[str, Any]] = None


class CompositeItems(FetchBaseModel):
    items: List[
        Union[FileDataElement, PastedDataElement, UrlDataElement, PathDataElement, ServerDirElement, FtpImportElement]
    ] = Field(..., alias="elements")


CompositeDataElement.model_rebuild()


class NestedElement(BaseDataElement):
    items: List[Union["AnyElement", "NestedElement"]] = Field(..., alias="elements")


AnyElement = Annotated[
    Union[
        FileDataElement,
        PastedDataElement,
        UrlDataElement,
        PathDataElement,
        ServerDirElement,
        FtpImportElement,
        CompositeDataElement,
    ],
    Field(default_factory=None, discriminator="src"),
]


# Seems to be a bug in pydantic ... can't reuse AnyElement in more than one model
AnyElement2 = Annotated[
    Union[
        FileDataElement,
        PastedDataElement,
        UrlDataElement,
        PathDataElement,
        ServerDirElement,
        FtpImportElement,
        CompositeDataElement,
    ],
    Field(default_factory=None, discriminator="src"),
]

NestedElement.model_rebuild()


class BaseDataTarget(BaseFetchDataTarget):
    destination: Union[HdaDestination, LibraryFolderDestination, LibraryDestination] = Field(..., discriminator="type")


class DataElementsTarget(BaseDataTarget):
    items: List[Union[AnyElement, NestedElement]] = Field(..., alias="elements")


class DataElementsFromTarget(BaseDataTarget, ItemsFromModel):
    items_from: ElementsFromType = Field(..., alias="elements_from")


class HdcaDataItemsTarget(BaseCollectionTarget):
    items: List[Union[AnyElement2, NestedElement]] = Field(..., alias="elements")


class HdcaDataItemsFromTarget(BaseCollectionTarget, ItemsFromModel):
    items_from: ElementsFromType = Field(..., alias="elements_from")


class FilesPayload(Model):
    filename: str
    local_filename: str


class BaseDataPayload(FetchBaseModel):
    history_id: DecodedDatabaseIdField
    model_config = ConfigDict(extra="allow")

    @field_validator("targets", mode="before", check_fields=False)
    @classmethod
    def targets_string_to_json(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


Targets = List[
    Union[
        DataElementsTarget,
        HdcaDataItemsTarget,
        DataElementsFromTarget,
        HdcaDataItemsFromTarget,
        FtpImportTarget,
    ]
]


class FetchDataPayload(BaseDataPayload):
    targets: Targets


class FetchDataFormPayload(BaseDataPayload):
    targets: Union[Json[Targets], Targets]
