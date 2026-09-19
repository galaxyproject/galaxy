import json
from enum import Enum
from typing import (
    Annotated,
    Any,
    Literal,
    Union,
)

from pydantic import (
    AliasChoices,
    ConfigDict,
    Field,
    field_validator,
    HttpUrl,
    Json,
    TypeAdapter,
    UUID4,
)

from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import Model
from galaxy.schema.terms import HelpTerms
from galaxy.schema.types import CoercedStringType
from galaxy.tool_util_models.parameters import FileOrCollectionRequest
from galaxy.tool_util_models.sample_sheet import (
    SampleSheetColumnDefinitions,
    SampleSheetRow,
)
from galaxy.util.hash_util import HashFunctionNames

HELP_TERMS = HelpTerms()


class FetchBaseModel(Model):
    model_config = ConfigDict(populate_by_name=True)


class ElementsFromType(str, Enum):
    archive = "archive"
    bagit = "bagit"
    bagit_archive = "bagit_archive"
    directory = "directory"


AutoDecompressField = Field(False, description=HELP_TERMS.get_term("galaxy.dataFetch.auto_decompress"))


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
    collection_type: str | None = None
    tags: list[str] | None = None
    name: str | None = None
    column_definitions: SampleSheetColumnDefinitions | None = None
    rows: dict[str, SampleSheetRow] | None = None


class LibraryDestination(FetchBaseModel):
    type: Literal["library"]
    name: str = Field(..., description="Must specify a library name")
    description: str | None = Field(None, description="Description for library to create")
    synopsis: str | None = Field(None, description="Description for library to create")


class ExtraFiles(FetchBaseModel):
    items_from: str | None = None
    src: Src
    fuzzy_root: bool | None = Field(
        True,
        description="Prevent Galaxy from checking for a single file in a directory and re-interpreting the archive",
    )


class FetchDatasetHash(Model):
    hash_function: HashFunctionNames
    hash_value: str

    model_config = ConfigDict(extra="forbid")


class BaseDataElement(FetchBaseModel):
    name: CoercedStringType | None = None
    dbkey: str = Field("?", description=HELP_TERMS.get_term("galaxy.dataFetch.dbkey"))
    info: str | None = Field(None, description=HELP_TERMS.get_term("galaxy.dataFetch.info"))
    ext: str = Field("auto", description=HELP_TERMS.get_term("galaxy.dataFetch.ext"))
    space_to_tab: bool = Field(False, description=HELP_TERMS.get_term("galaxy.dataFetch.space_to_tab"))
    to_posix_lines: bool = Field(False, description=HELP_TERMS.get_term("galaxy.dataFetch.to_posix_lines"))
    deferred: bool = Field(False, description=HELP_TERMS.get_term("galaxy.dataFetch.deferred"))
    tags: list[str] | None = Field(None, description=HELP_TERMS.get_term("galaxy.dataFetch.tags"))
    created_from_basename: str | None = None
    extra_files: ExtraFiles | None = None
    auto_decompress: bool = AutoDecompressField
    items_from: ElementsFromType | None = Field(None, validation_alias=AliasChoices("items_from", "elements_from"))
    collection_type: str | None = None
    MD5: str | None = Field(None, description=HELP_TERMS.get_term("galaxy.dataFetch.MD5"))
    SHA1: str | None = Field(None, alias="SHA-1", description=HELP_TERMS.get_term("galaxy.dataFetch.SHA1"))
    SHA256: str | None = Field(None, alias="SHA-256", description=HELP_TERMS.get_term("galaxy.dataFetch.SHA256"))
    SHA512: str | None = Field(None, alias="SHA-512", description=HELP_TERMS.get_term("galaxy.dataFetch.SHA512"))
    hashes: list[FetchDatasetHash] | None = None
    description: str | None = None
    model_config = ConfigDict(extra="forbid")
    # It'd be nice to restrict this to just the top level and only if creating a collection
    row: SampleSheetRow | None = None


class FileDataElement(BaseDataElement):
    src: Literal["files"]


class PastedDataElement(BaseDataElement):
    src: Literal["pasted"]
    paste_content: CoercedStringType = Field(..., description=HELP_TERMS.get_term("galaxy.dataFetch.paste_content"))


class UrlDataElement(BaseDataElement):
    src: Literal["url"]
    url: str = Field(..., description="URL to upload")
    headers: dict[str, str] | None = Field(None, description="Optional headers to include in the URL fetch request")


class ServerDirElement(BaseDataElement):
    src: Literal["server_dir"]
    server_dir: str
    link_data_only: bool | None = None


class FtpImportElement(BaseDataElement):
    src: Literal["ftp_import"]
    ftp_path: str
    collection_type: str | None = None


class ItemsFromModel(Model):
    src: ItemsFromSrc
    path: str | None = None
    ftp_path: str | None = None
    server_dir: str | None = None
    url: str | None = None


class FtpImportTarget(BaseCollectionTarget):
    src: Literal["ftp_import"]
    ftp_path: str
    items_from: ElementsFromType | None = Field(None, validation_alias=AliasChoices("items_from", "elements_from"))


class PathDataElement(BaseDataElement):
    src: Literal["path"]
    path: str
    items_from: ElementsFromType | None = Field(None, validation_alias=AliasChoices("items_from", "elements_from"))
    link_data_only: bool | None = None


class CompositeDataElement(BaseDataElement):
    src: Literal["composite"]
    composite: "CompositeItems"
    metadata: dict[str, Any] | None = None


class CompositeItems(FetchBaseModel):
    elements: list[
        FileDataElement | PastedDataElement | UrlDataElement | PathDataElement | ServerDirElement | FtpImportElement
    ] = Field(..., validation_alias=AliasChoices("elements", "items"))


CompositeDataElement.model_rebuild()


class NestedElement(BaseDataElement):
    elements: list[Union["AnyElement", "NestedElement"]] = Field(
        ..., validation_alias=AliasChoices("elements", "items")
    )


AnyElement = Annotated[
    FileDataElement
    | PastedDataElement
    | UrlDataElement
    | PathDataElement
    | ServerDirElement
    | FtpImportElement
    | CompositeDataElement,
    Field(default_factory=None, discriminator="src"),
]


# Seems to be a bug in pydantic ... can't reuse AnyElement in more than one model
AnyElement2 = Annotated[
    FileDataElement
    | PastedDataElement
    | UrlDataElement
    | PathDataElement
    | ServerDirElement
    | FtpImportElement
    | CompositeDataElement,
    Field(default_factory=None, discriminator="src"),
]

NestedElement.model_rebuild()


class BaseDataTarget(BaseFetchDataTarget):
    destination: HdaDestination | LibraryFolderDestination | LibraryDestination = Field(..., discriminator="type")


class DataElementsTarget(BaseDataTarget):
    elements: list[AnyElement | NestedElement] = Field(..., validation_alias=AliasChoices("elements", "items"))


class DataElementsFromTarget(BaseDataTarget, ItemsFromModel):
    items_from: ElementsFromType = Field(..., alias="elements_from")


class HdcaDataItemsTarget(BaseCollectionTarget):
    elements: list[AnyElement2 | NestedElement] = Field(..., validation_alias=AliasChoices("elements", "items"))


class HdcaDataItemsFromTarget(BaseCollectionTarget, ItemsFromModel):
    items_from: ElementsFromType = Field(..., validation_alias=AliasChoices("items_from", "elements_from"))


class FilesPayload(Model):
    filename: str
    local_filename: str


class BaseDataPayload(FetchBaseModel):
    history_id: DecodedDatabaseIdField
    preferred_object_store_id: str | None = Field(
        None,
        description="Optional preferred storage location id used when creating fetched datasets.",
    )
    model_config = ConfigDict(extra="allow")
    landing_uuid: UUID4 | None = None

    @field_validator("targets", mode="before", check_fields=False)
    @classmethod
    def targets_string_to_json(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


Targets = list[
    DataElementsTarget | HdcaDataItemsTarget | DataElementsFromTarget | HdcaDataItemsFromTarget | FtpImportTarget
]


TargetsAdapter = TypeAdapter(Targets)


class FetchDataPayload(BaseDataPayload):
    targets: Targets


class FetchDataFormPayload(BaseDataPayload):
    targets: Json[Targets] | Targets


class DataLandingRequestState(Model):
    targets: Targets


FileOrCollectionRequests = list[FileOrCollectionRequest]

FileOrCollectionRequestsAdapter = TypeAdapter(FileOrCollectionRequests)


# Vaguely matches the schema.schema.ToolLandingState but we don't allow data_fetch to be called directly
# via the tool API so we have a more specific model here.
class CreateDataLandingPayload(Model):
    request_state: DataLandingRequestState
    client_secret: str | None = None
    public: bool = False
    origin: HttpUrl | None = None

    model_config = ConfigDict(extra="forbid")


class CreateFileLandingPayload(Model):
    request_state: FileOrCollectionRequests
    client_secret: str | None = None
    public: bool = False
    origin: HttpUrl | None = None

    model_config = ConfigDict(extra="forbid")
