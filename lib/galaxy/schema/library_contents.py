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
    RootModel,
)
from pydantic.functional_validators import field_validator
from typing_extensions import (
    Annotated,
    Literal,
)

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
    EncodedLibraryFolderDatabaseIdField,
    LibraryFolderDatabaseIdField,
    ModelClassField,
)
from galaxy.schema.schema import (
    Model,
    TagCollection,
)


class UploadOption(str, Enum):
    upload_file = "upload_file"
    upload_paths = "upload_paths"
    upload_directory = "upload_directory"


class CreateType(str, Enum):
    file = "file"
    folder = "folder"
    collection = "collection"


class LinkDataOnly(str, Enum):
    copy_files = "copy_files"
    link_to_files = "link_to_files"


class LibraryContentsCreatePayload(Model):
    create_type: CreateType = Field(
        ...,
        description="the type of item to create",
    )
    upload_option: UploadOption = Field(
        UploadOption.upload_file,
        description="the method to use for uploading files",
        deprecated=True,
    )
    folder_id: LibraryFolderDatabaseIdField = Field(
        ...,
        description="the encoded id of the parent folder of the new item",
    )
    tag_using_filenames: bool = Field(
        False,
        description="create tags on datasets using the file's original name",
    )
    tags: List[str] = Field(
        [],
        description="create the given list of tags on datasets",
    )
    from_hda_id: Optional[DecodedDatabaseIdField] = Field(
        None,
        description="(only if create_type is 'file') the encoded id of an accessible HDA to copy into the library",
    )
    from_hdca_id: Optional[DecodedDatabaseIdField] = Field(
        None,
        description="(only if create_type is 'file') the encoded id of an accessible HDCA to copy into the library",
    )
    ldda_message: str = Field(
        "",
        description="the new message attribute of the LDDA created",
    )
    extended_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="sub-dictionary containing any extended metadata to associate with the item",
    )

    @field_validator("tags", mode="before", check_fields=False)
    @classmethod
    def tags_string_to_json(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class LibraryContentsFileCreatePayload(LibraryContentsCreatePayload):
    dbkey: Union[str, list] = Field(
        "?",
        title="database key",
    )
    roles: str = Field(
        "",
        title="user selected roles",
    )
    file_type: Optional[str] = Field(
        None,
        title="file type",
    )
    server_dir: str = Field(
        "",
        description="(only if upload_option is 'upload_directory') relative path of the "
        "subdirectory of Galaxy ``library_import_dir`` (if admin) or "
        "``user_library_import_dir`` (if non-admin) to upload. "
        "All and only the files (i.e. no subdirectories) contained "
        "in the specified directory will be uploaded.",
    )
    filesystem_paths: str = Field(
        "",
        description="(only if upload_option is 'upload_paths' and the user is an admin) "
        "file paths on the Galaxy server to upload to the library, one file per line",
    )
    link_data_only: LinkDataOnly = Field(
        LinkDataOnly.copy_files,
        description="(only when upload_option is 'upload_directory' or 'upload_paths')."
        "Setting to 'link_to_files' symlinks instead of copying the files",
    )
    uuid: Optional[str] = Field(
        None,
        title="UUID of the dataset to upload",
    )
    upload_files: Optional[List[Dict[str, Any]]] = Field(
        None,
        title="list of the uploaded files",
    )

    # uploaded file fields
    model_config = ConfigDict(extra="allow")


class LibraryContentsFolderCreatePayload(LibraryContentsCreatePayload):
    name: str = Field(
        "",
        title="name of the folder to create",
    )
    description: str = Field(
        "",
        title="description of the folder to create",
    )


class LibraryContentsCollectionCreatePayload(LibraryContentsCreatePayload):
    collection_type: str = Field(
        ...,
        title="the type of collection to create",
    )
    element_identifiers: List[Dict[str, Any]] = Field(
        ...,
        title="list of dictionaries containing the element identifiers for the collection",
    )
    name: Optional[str] = Field(
        None,
        title="the name of the collection",
    )
    hide_source_items: bool = Field(
        False,
        description="if True, hide the source items in the collection",
    )
    copy_elements: bool = Field(
        False,
        description="if True, copy the elements into the collection",
    )


class LibraryContentsUpdatePayload(Model):
    converted_dataset_id: Optional[DecodedDatabaseIdField] = Field(
        None,
        title="the decoded id of the dataset",
    )


class LibraryContentsDeletePayload(Model):
    purge: bool = Field(
        False,
        description="if True, purge the library dataset",
    )


class LibraryContentsIndexResponse(Model):
    type: str
    name: str
    url: str


class LibraryContentsIndexFolderResponse(LibraryContentsIndexResponse):
    id: EncodedLibraryFolderDatabaseIdField


class LibraryContentsIndexDatasetResponse(LibraryContentsIndexResponse):
    id: EncodedDatabaseIdField


class LibraryContentsIndexListResponse(RootModel):
    root: List[Union[LibraryContentsIndexFolderResponse, LibraryContentsIndexDatasetResponse]]


class LibraryContentsShowResponse(Model):
    name: str
    genome_build: Optional[str]
    update_time: str
    parent_library_id: EncodedDatabaseIdField


class LibraryContentsShowFolderResponse(LibraryContentsShowResponse):
    model_class: Annotated[Literal["LibraryFolder"], ModelClassField(Literal["LibraryFolder"])]
    id: EncodedLibraryFolderDatabaseIdField
    parent_id: Optional[EncodedLibraryFolderDatabaseIdField]
    description: str
    item_count: int
    deleted: bool
    library_path: List[str]


class LibraryContentsShowDatasetResponse(LibraryContentsShowResponse):
    model_class: Annotated[Literal["LibraryDataset"], ModelClassField(Literal["LibraryDataset"])]
    id: EncodedDatabaseIdField
    ldda_id: EncodedDatabaseIdField
    folder_id: EncodedLibraryFolderDatabaseIdField
    state: str
    file_name: str
    created_from_basename: Optional[str]
    uploaded_by: Optional[str]
    message: Optional[str]
    date_uploaded: str
    file_size: int
    file_ext: str
    data_type: str
    misc_info: Optional[str]
    misc_blurb: Optional[str]
    peek: Optional[str]
    uuid: str
    tags: TagCollection

    # metadata fields
    model_config = ConfigDict(extra="allow")


class LibraryContentsCreateResponse(Model):
    name: str
    url: str


class LibraryContentsCreateFolderResponse(LibraryContentsCreateResponse):
    id: EncodedLibraryFolderDatabaseIdField


class LibraryContentsCreateFileResponse(LibraryContentsCreateResponse):
    id: EncodedDatabaseIdField


class LibraryContentsCreateFolderListResponse(RootModel):
    root: List[LibraryContentsCreateFolderResponse]


class LibraryContentsCreateFileListResponse(RootModel):
    root: List[LibraryContentsCreateFileResponse]


class LibraryContentsCreateDatasetResponse(Model):
    # id, library_dataset_id, parent_library_id should change to EncodedDatabaseIdField latter
    # because they are encoded ids in _copy_hda_to_library_folder and _copy_hdca_to_library_folder
    # functions that are shared by LibraryFolderContentsService too
    id: str
    hda_ldda: str
    model_class: Annotated[
        Literal["LibraryDatasetDatasetAssociation"], ModelClassField(Literal["LibraryDatasetDatasetAssociation"])
    ]
    name: str
    deleted: bool
    visible: bool
    state: str
    library_dataset_id: str
    file_size: int
    file_name: str
    update_time: str
    file_ext: str
    data_type: str
    genome_build: str
    misc_info: Optional[str]
    misc_blurb: Optional[str]
    created_from_basename: Optional[str]
    uuid: str
    parent_library_id: str

    # metadata fields
    model_config = ConfigDict(extra="allow")


class LibraryContentsCreateDatasetCollectionResponse(RootModel):
    root: List[LibraryContentsCreateDatasetResponse]


class LibraryContentsDeleteResponse(Model):
    id: EncodedDatabaseIdField
    deleted: bool


class LibraryContentsPurgedResponse(LibraryContentsDeleteResponse):
    purged: bool


AnyLibraryContentsShowResponse = Union[
    LibraryContentsShowFolderResponse,
    LibraryContentsShowDatasetResponse,
]

AnyLibraryContentsCreatePayload = Union[
    LibraryContentsFolderCreatePayload, LibraryContentsFileCreatePayload, LibraryContentsCollectionCreatePayload
]

AnyLibraryContentsCreateResponse = Union[
    LibraryContentsCreateFolderListResponse,
    LibraryContentsCreateFileListResponse,
    LibraryContentsCreateDatasetCollectionResponse,
    LibraryContentsCreateDatasetResponse,
]
