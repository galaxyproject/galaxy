"""This module contains general pydantic models and common schema field annotations for them."""

import base64
from datetime import (
    date,
    datetime,
)
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    AnyUrl,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    Json,
    model_validator,
    RootModel,
    UUID4,
)
from pydantic_core import core_schema
from typing_extensions import (
    Annotated,
    Literal,
)

from galaxy.schema import partial_model
from galaxy.schema.bco import XrefItem
from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
    EncodedLibraryFolderDatabaseIdField,
    is_optional,
    LibraryFolderDatabaseIdField,
    literal_to_value,
    ModelClassField,
)
from galaxy.schema.types import (
    OffsetNaiveDatetime,
    RelativeUrl,
)
from galaxy.util.hash_util import HashFunctionNameEnum
from galaxy.util.sanitize_html import sanitize_html

USER_MODEL_CLASS = Literal["User"]
GROUP_MODEL_CLASS = Literal["Group"]
HDA_MODEL_CLASS = Literal["HistoryDatasetAssociation"]
DC_MODEL_CLASS = Literal["DatasetCollection"]
DCE_MODEL_CLASS = Literal["DatasetCollectionElement"]
HDCA_MODEL_CLASS = Literal["HistoryDatasetCollectionAssociation"]
HISTORY_MODEL_CLASS = Literal["History"]
JOB_MODEL_CLASS = Literal["Job"]
STORED_WORKFLOW_MODEL_CLASS = Literal["StoredWorkflow"]
PAGE_MODEL_CLASS = Literal["Page"]
INVOCATION_MODEL_CLASS = Literal["WorkflowInvocation"]
INVOCATION_STEP_MODEL_CLASS = Literal["WorkflowInvocationStep"]
INVOCATION_REPORT_MODEL_CLASS = Literal["Report"]
IMPLICIT_COLLECTION_JOBS_MODEL_CLASS = Literal["ImplicitCollectionJobs"]

OptionalNumberT = Annotated[Optional[Union[int, float]], Field(None)]

TAG_ITEM_PATTERN = r"^([^\s.:])+(\.[^\s.:]+)*(:\S+)?$"


class DatasetState(str, Enum):
    NEW = "new"
    UPLOAD = "upload"
    QUEUED = "queued"
    RUNNING = "running"
    OK = "ok"
    EMPTY = "empty"
    ERROR = "error"
    PAUSED = "paused"
    SETTING_METADATA = "setting_metadata"
    FAILED_METADATA = "failed_metadata"
    # Non-deleted, non-purged datasets that don't have physical files.
    # These shouldn't have objectstores attached -
    # 'deferred' can be materialized for jobs using
    # attached DatasetSource objects but 'discarded'
    # cannot (e.g. imported histories). These should still
    # be able to have history contents associated (normal HDAs?)
    DEFERRED = "deferred"
    DISCARDED = "discarded"

    @classmethod
    def values(self):
        return self.__members__.values()


class JobState(str, Enum):
    NEW = "new"
    RESUBMITTED = "resubmitted"
    UPLOAD = "upload"
    WAITING = "waiting"
    QUEUED = "queued"
    RUNNING = "running"
    OK = "ok"
    ERROR = "error"
    FAILED = "failed"
    PAUSED = "paused"
    DELETING = "deleting"
    DELETED = "deleted"
    STOPPING = "stop"
    STOPPED = "stopped"
    SKIPPED = "skipped"


class DatasetCollectionPopulatedState(str, Enum):
    NEW = "new"  # New dataset collection, unpopulated elements
    OK = "ok"  # Collection elements populated (HDAs may or may not have errors)
    FAILED = "failed"  # some problem populating state, won't be populated


# Generic and common Field annotations that can be reused across models

RelativeUrlField = Annotated[
    RelativeUrl,
    Field(
        ...,
        title="URL",
        description="The relative URL to access this item.",
        # TODO: also deprecate on python side, https://github.com/pydantic/pydantic/issues/2255
        json_schema_extra={"deprecated": True},
    ),
]

DownloadUrlField: RelativeUrl = Field(
    ...,
    title="Download URL",
    description="The URL to download this item from the server.",
)

AnnotationField: Optional[str] = Field(
    ...,
    title="Annotation",
    description="An annotation to provide details or to help understand the purpose and usage of this item.",
)

AccessibleField: bool = Field(
    ...,
    title="Accessible",
    description="Whether this item is accessible to the current user due to permissions.",
)

DatasetCollectionId = Annotated[EncodedDatabaseIdField, Field(..., title="Dataset Collection ID")]
DatasetCollectionElementId = Annotated[EncodedDatabaseIdField, Field(..., title="Dataset Collection Element ID")]
HistoryID = Annotated[EncodedDatabaseIdField, Field(..., title="History ID")]
HistoryDatasetAssociationId = Annotated[EncodedDatabaseIdField, Field(..., title="History Dataset Association ID")]
JobId = Annotated[EncodedDatabaseIdField, Field(..., title="Job ID")]


DatasetStateField = Annotated[
    DatasetState,
    BeforeValidator(lambda v: "discarded" if v == "deleted" else v),
    Field(..., title="State", description="The current state of this dataset."),
]

CreateTimeField = Field(
    title="Create Time",
    description="The time and date this item was created.",
)

UpdateTimeField = Field(
    title="Update Time",
    description="The last time and date this item was updated.",
)

CollectionType = str  # str alias for now

CollectionTypeField = Field(
    title="Collection Type",
    description=(
        "The type of the collection, can be `list`, `paired`, or define subcollections using `:` "
        "as separator like `list:paired` or `list:list`."
    ),
)

OptionalCollectionTypeField = Field(
    None,
    title="Collection Type",
    description=(
        "The type of the collection, can be `list`, `paired`, or define subcollections using `:` "
        "as separator like `list:paired` or `list:list`."
    ),
)

PopulatedStateField: DatasetCollectionPopulatedState = Field(
    ...,
    title="Populated State",
    description=(
        "Indicates the general state of the elements in the dataset collection:"
        "- 'new': new dataset collection, unpopulated elements."
        "- 'ok': collection elements populated (HDAs may or may not have errors)."
        "- 'failed': some problem populating, won't be populated."
    ),
)

PopulatedStateMessageField: Optional[str] = Field(
    None,
    title="Populated State Message",
    description="Optional message with further information in case the population of the dataset collection failed.",
)

ElementCountField = Annotated[
    Optional[int],
    Field(
        None,
        title="Element Count",
        description=(
            "The number of elements contained in the dataset collection. "
            "It may be None or undefined if the collection could not be populated."
        ),
    ),
]

PopulatedField = Annotated[
    bool,
    Field(
        None,
        title="Populated",
        description="Whether the dataset collection elements (and any subcollections elements) were successfully populated.",
    ),
]

ElementsField: List["DCESummary"] = Field(
    [],
    title="Elements",
    description="The summary information of each of the elements inside the dataset collection.",
)

UuidField = Annotated[
    UUID4,
    Field(
        ...,
        title="UUID",
        description="Universal unique identifier for this dataset.",
    ),
]

GenomeBuildField: Optional[str] = Field(
    "?",
    title="Genome Build",
    description="TODO",
)

ContentsUrlField = Annotated[
    RelativeUrl,
    Field(
        ...,
        title="Contents URL",
        description="The relative URL to access the contents of this History.",
    ),
]

UserId = Annotated[EncodedDatabaseIdField, Field(title="ID", description="Encoded ID of the user")]
UserEmailField = Field(title="Email", description="Email of the user")
UserDescriptionField = Field(title="Description", description="Description of the user")
UserNameField = Field(default=..., title="user_name", description="The name of the user.")
QuotaPercentField = Field(
    default=None, title="Quota percent", description="Percentage of the storage quota applicable to the user."
)
UserDeletedField = Field(default=..., title="Deleted", description=" User is deleted")
PreferredObjectStoreIdField = Field(
    default=None,
    title="Preferred Object Store ID",
    description="The ID of the object store that should be used to store new datasets in this history.",
)

TotalDiskUsageField = Field(
    default=...,
    title="Total disk usage",
    description="Size of all non-purged, unique datasets of the user in bytes.",
)
NiceTotalDiskUsageField = Field(
    default=...,
    title="Nice total disc usage",
    description="Size of all non-purged, unique datasets of the user in a nice format.",
)
FlexibleUserIdType = Union[DecodedDatabaseIdField, Literal["current"]]


class Model(BaseModel):
    """Base model definition with common configuration used by all derived models."""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True, protected_namespaces=())


class RequireOneSetOption(Model):
    # TODO: model in json schema
    @model_validator(mode="after")
    def check_some_ids_passed(self):
        if not self.model_fields_set:
            raise ValueError("Specify at least one ID to apply actions to")
        return self


class BaseUserModel(Model):
    id: UserId
    username: str = UserNameField
    email: str = UserEmailField
    deleted: bool = UserDeletedField


class WithModelClass:
    model_class: str

    @model_validator(mode="before")
    @classmethod
    def set_default(cls, data):
        if isinstance(data, dict):
            if "model_class" not in data and issubclass(cls, BaseModel):
                model_class_annotation = cls.model_fields["model_class"].annotation
                if is_optional(model_class_annotation):
                    return data
                data = data.copy()
                data["model_class"] = literal_to_value(model_class_annotation)
        return data


class UserModel(BaseUserModel, WithModelClass):
    """User in a transaction context."""

    active: bool = Field(title="Active", description="User is active")
    model_class: USER_MODEL_CLASS = ModelClassField(USER_MODEL_CLASS)
    last_password_change: Optional[datetime] = Field(title="Last password change", description="")


class LimitedUserModel(Model):
    """This is used when config options (expose_user_name and expose_user_email) are in place."""

    id: UserId
    username: Optional[str] = None
    email: Optional[str] = None


MaybeLimitedUserModel = Union[UserModel, LimitedUserModel]


class DiskUsageUserModel(Model):
    total_disk_usage: float = TotalDiskUsageField
    nice_total_disk_usage: str = NiceTotalDiskUsageField


class CreatedUserModel(UserModel, DiskUsageUserModel):
    preferred_object_store_id: Optional[str] = PreferredObjectStoreIdField


class AnonUserModel(DiskUsageUserModel):
    quota_percent: Optional[float] = QuotaPercentField


class DetailedUserModel(BaseUserModel, AnonUserModel):
    is_admin: bool = Field(default=..., title="Is admin", description="User is admin")
    purged: bool = Field(default=..., title="Purged", description="User is purged")
    preferences: Dict[Any, Any] = Field(default=..., title="Preferences", description="Preferences of the user")
    preferred_object_store_id: Optional[str] = PreferredObjectStoreIdField
    quota: str = Field(default=..., title="Quota", description="Quota applicable to the user")
    quota_bytes: Optional[int] = Field(
        default=None, title="Quota in bytes", description="Quota applicable to the user in bytes."
    )
    tags_used: List[str] = Field(default=..., title="Tags used", description="Tags used by the user")


class UserUpdatePayload(Model):
    active: Annotated[Optional[bool], Field(None, title="Active", description="User is active")]
    username: Annotated[Optional[str], Field(None, title="Username", description="The name of the user.")]
    preferred_object_store_id: Annotated[Optional[str], PreferredObjectStoreIdField]


class UserCreationPayload(Model):
    password: str = Field(default=..., title="user_password", description="The password of the user.")
    email: str = UserEmailField
    username: str = UserNameField


class RemoteUserCreationPayload(Model):
    remote_user_email: str = UserEmailField


class UserDeletionPayload(Model):
    purge: bool = Field(
        default=False,
        title="Purge user",
        description="Purge the user. Deprecated, please use the `purge` query parameter instead.",
        json_schema_extra={"deprecated": True},
    )


class FavoriteObject(Model):
    object_id: str = Field(
        default=..., title="Object ID", description="The id of an object the user wants to favorite."
    )


class FavoriteObjectsSummary(Model):
    tools: List[str] = Field(default=..., title="Favorite tools", description="The name of the tools the user favored.")


class FavoriteObjectType(str, Enum):
    tools = "tools"


class DeletedCustomBuild(Model):
    message: str = Field(
        default=..., title="Deletion message", description="Confirmation of the custom build deletion."
    )


class CustomBuildBaseModel(Model):
    name: str = Field(default=..., title="Name", description="The name of the custom build.")


class CustomBuildLenType(str, Enum):
    file = "file"
    fasta = "fasta"
    text = "text"


# TODO Evaluate if the titles and descriptions are fitting
class CustomBuildCreationPayload(CustomBuildBaseModel):
    len_type: CustomBuildLenType = Field(
        default=...,
        alias="len|type",
        title="Length type",
        description="The type of the len file.",
    )
    len_value: str = Field(
        default=...,
        alias="len|value",
        title="Length value",
        description="The content of the length file.",
    )


class CreatedCustomBuild(CustomBuildBaseModel):
    len: EncodedDatabaseIdField = Field(default=..., title="Length", description="The primary id of the len file.")
    count: Optional[str] = Field(default=None, title="Count", description="The number of chromosomes/contigs.")
    fasta: Optional[EncodedDatabaseIdField] = Field(
        default=None, title="Fasta", description="The primary id of the fasta file from a history."
    )
    linecount: Optional[EncodedDatabaseIdField] = Field(
        default=None, title="Line count", description="The primary id of a linecount dataset."
    )


class CustomBuildModel(CreatedCustomBuild):
    id: str = Field(default=..., title="ID", description="The ID of the custom build.")


class CustomBuildsCollection(RootModel):
    root: List[CustomBuildModel] = Field(
        default=..., title="Custom builds collection", description="The custom builds associated with the user."
    )


class GroupModel(Model, WithModelClass):
    """User group model"""

    model_class: GROUP_MODEL_CLASS = ModelClassField(GROUP_MODEL_CLASS)
    id: DecodedDatabaseIdField = Field(
        ...,  # ...
        title="ID",
        description="Encoded group ID",
    )
    name: str = Field(
        ...,  # ...
        title="Name",
        description="The name of the group.",
    )


class JobSourceType(str, Enum):
    """Available types of job sources (model classes) that produce dataset collections."""

    Job = "Job"
    ImplicitCollectionJobs = "ImplicitCollectionJobs"
    WorkflowInvocation = "WorkflowInvocation"


class HistoryContentType(str, Enum):
    """Available types of History contents."""

    dataset = "dataset"
    dataset_collection = "dataset_collection"


class HistoryImportArchiveSourceType(str, Enum):
    """Available types of History archive sources."""

    url = "url"
    file = "file"


class DCEType(str, Enum):  # TODO: suspiciously similar to HistoryContentType
    """Available types of dataset collection elements."""

    hda = "hda"
    dataset_collection = "dataset_collection"


class DatasetSourceType(str, Enum):
    hda = "hda"
    ldda = "ldda"


class DataItemSourceType(str, Enum):
    hda = "hda"
    ldda = "ldda"
    hdca = "hdca"
    dce = "dce"
    dc = "dc"


class ColletionSourceType(str, Enum):
    hda = "hda"
    ldda = "ldda"
    hdca = "hdca"
    new_collection = "new_collection"


class HistoryContentSource(str, Enum):
    hda = "hda"
    hdca = "hdca"
    library = "library"
    library_folder = "library_folder"
    new_collection = "new_collection"


DatasetCollectionInstanceType = Literal["history", "library"]


TagItem = Annotated[str, Field(..., pattern=TAG_ITEM_PATTERN)]


class TagCollection(RootModel):
    """Represents the collection of tags associated with an item."""

    root: List[TagItem] = Field(
        default=...,
        title="Tags",
        description="The collection of tags associated with an item.",
        examples=["COVID-19", "#myFancyTag", "covid19.galaxyproject.org"],
    )


class MetadataFile(Model):
    """Metadata file associated with a dataset."""

    file_type: str = Field(
        ...,
        title="File Type",
        description="TODO",
    )
    download_url: RelativeUrl = DownloadUrlField


class DatasetPermissions(Model):
    """Role-based permissions for accessing and managing a dataset."""

    manage: List[DecodedDatabaseIdField] = Field(
        [],
        title="Management",
        description="The set of roles (encoded IDs) that can manage this dataset.",
    )
    access: List[DecodedDatabaseIdField] = Field(
        [],
        title="Access",
        description="The set of roles (encoded IDs) that can access this dataset.",
    )


class Hyperlink(Model):
    """Represents some text with an Hyperlink."""

    target: str = Field(
        ..., title="Target", description="Specifies where to open the linked document.", examples=["_blank"]
    )
    href: Annotated[RelativeUrl, Field(..., title="Href", description="The URL of the linked document.")]
    text: str = Field(
        ...,
        title="Text",
        description="The text placeholder for the link.",
    )


class DisplayApp(Model):
    """Basic linked information about an application that can display certain datatypes."""

    label: str = Field(
        ...,
        title="Label",
        description="The label or title of the Display Application.",
    )
    links: List[Hyperlink] = Field(
        ...,
        title="Links",
        description="The collection of link details for this Display Application.",
    )


class Visualization(Model):  # TODO annotate this model
    # TODO[pydantic]: The following keys were removed: `json_encoders`.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-config for more information.
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )


class HistoryItemBase(Model):
    """Basic information provided by items contained in a History."""

    id: EncodedDatabaseIdField
    name: Optional[str] = Field(
        title="Name",
        description="The name of the item.",
    )
    history_id: HistoryID
    hid: int = Field(
        ...,
        title="HID",
        description="The index position of this item in the History.",
    )
    deleted: bool = Field(
        ...,
        title="Deleted",
        description="Whether this item is marked as deleted.",
    )
    visible: bool = Field(
        ...,
        title="Visible",
        description="Whether this item is visible or hidden to the user by default.",
    )


class HistoryItemCommon(HistoryItemBase):
    """Common information provided by items contained in a History."""

    type_id: Optional[str] = Field(
        default=None,
        title="Type - ID",
        description="The type and the encoded ID of this item. Used for caching.",
        examples=["dataset-616e371b2cc6c62e"],
    )
    type: str = Field(
        ...,
        title="Type",
        description="The type of this item.",
    )
    create_time: Optional[datetime] = CreateTimeField
    update_time: Optional[datetime] = UpdateTimeField
    url: RelativeUrlField
    tags: TagCollection


class HDACommon(HistoryItemCommon):
    history_content_type: Annotated[
        Literal["dataset"],
        Field(
            title="History Content Type",
            description="This is always `dataset` for datasets.",
        ),
    ]
    copied_from_ldda_id: Optional[EncodedDatabaseIdField] = None


class HDASummary(HDACommon):
    """History Dataset Association summary information."""

    dataset_id: EncodedDatabaseIdField = Field(
        ...,
        title="Dataset ID",
        description="The encoded ID of the dataset associated with this item.",
    )
    state: DatasetStateField
    extension: Optional[str] = Field(
        ...,
        title="Extension",
        description="The extension of the dataset.",
        examples=["txt"],
    )
    purged: bool = Field(
        ...,
        title="Purged",
        description="Whether this dataset has been removed from disk.",
    )
    genome_build: Optional[str] = GenomeBuildField


class HDAInaccessible(HDACommon):
    """History Dataset Association information when the user can not access it."""

    accessible: Literal[False]
    state: DatasetStateField


HdaLddaField = Field(
    DatasetSourceType.hda,
    title="HDA or LDDA",
    description="Whether this dataset belongs to a history (HDA) or a library (LDDA).",
)


class DatasetValidatedState(str, Enum):
    UNKNOWN = "unknown"
    INVALID = "invalid"
    OK = "ok"


class DatasetHash(Model):
    model_class: Literal["DatasetHash"] = ModelClassField(Literal["DatasetHash"])
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="Encoded ID of the dataset hash.",
    )
    hash_function: HashFunctionNameEnum = Field(
        ...,
        title="Hash Function",
        description="The hash function used to generate the hash.",
    )
    hash_value: str = Field(
        ...,
        title="Hash Value",
        description="The hash value.",
    )
    extra_files_path: Optional[str] = Field(
        None,
        title="Extra Files Path",
        description="The path to the extra files used to generate the hash.",
    )


class DatasetSource(Model):
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="Encoded ID of the dataset source.",
    )
    source_uri: Annotated[RelativeUrl, Field(..., title="Source URI", description="The URI of the dataset source.")]
    extra_files_path: Annotated[
        Optional[str], Field(None, title="Extra Files Path", description="The path to the extra files.")
    ]
    transform: Annotated[
        Optional[List[Any]],  # TODO: type this
        Field(
            None,
            title="Transform",
            description="The transformations applied to the dataset source.",
        ),
    ]


class HDADetailed(HDASummary, WithModelClass):
    """History Dataset Association detailed information."""

    model_class: Annotated[HDA_MODEL_CLASS, ModelClassField(HDA_MODEL_CLASS)]
    hda_ldda: DatasetSourceType = HdaLddaField
    accessible: bool = AccessibleField
    misc_info: Optional[str] = Field(
        default=None,
        title="Miscellaneous Information",
        description="TODO",
    )
    misc_blurb: Optional[str] = Field(
        default=None,
        title="Miscellaneous Blurb",
        description="TODO",
    )
    file_ext: str = Field(  # Is this a duplicate of HDASummary.extension?
        ...,
        title="File extension",
        description="The extension of the file.",
    )
    file_size: int = Field(
        ...,
        title="File Size",
        description="The file size in bytes.",
    )
    resubmitted: bool = Field(
        ...,
        title="Resubmitted",
        description="Whether the job creating this dataset has been resubmitted.",
    )
    metadata: Optional[Any] = Field(  # TODO: create pydantic model for metadata?
        default=None,
        title="Metadata",
        description="The metadata associated with this dataset.",
    )
    meta_files: List[MetadataFile] = Field(
        ...,
        title="Metadata Files",
        description="Collection of metadata files associated with this dataset.",
    )
    data_type: str = Field(
        ...,
        title="Data Type",
        description="The fully qualified name of the class implementing the data type of this dataset.",
        examples=["galaxy.datatypes.data.Text"],
    )
    peek: Optional[str] = Field(
        default=None,
        title="Peek",
        description="A few lines of contents from the start of the file.",
    )
    creating_job: str = Field(
        ...,
        title="Creating Job ID",
        description="The encoded ID of the job that created this dataset.",
    )
    rerunnable: bool = Field(
        ...,
        title="Rerunnable",
        description="Whether the job creating this dataset can be run again.",
    )
    uuid: UuidField
    permissions: DatasetPermissions = Field(
        ...,
        title="Permissions",
        description="Role-based access and manage control permissions for the dataset.",
    )
    file_name: Optional[str] = Field(
        default=None,
        title="File Name",
        description="The full path to the dataset file.",
    )
    display_apps: List[DisplayApp] = Field(
        ...,
        title="Display Applications",
        description="Contains new-style display app urls.",
    )
    display_types: List[DisplayApp] = Field(
        ...,
        title="Legacy Display Applications",
        description="Contains old-style display app urls.",
        # https://github.com/pydantic/pydantic/issues/2255
        # deprecated=False,  # TODO: Should this field be deprecated in favor of display_apps?
    )
    validated_state: DatasetValidatedState = Field(
        ...,
        title="Validated State",
        description="The state of the datatype validation for this dataset.",
    )
    validated_state_message: Optional[str] = Field(
        None,
        title="Validated State Message",
        description="The message with details about the datatype validation result for this dataset.",
    )
    annotation: Optional[str] = AnnotationField
    download_url: RelativeUrl = DownloadUrlField
    type: Annotated[
        Literal["file"],
        Field(
            title="Type",
            description="This is always `file` for datasets.",
        ),
    ] = "file"
    api_type: Annotated[
        Literal["file"],
        Field(
            title="API Type",
            description="TODO",
            json_schema_extra={
                "deprecated": True
            },  # TODO: Should this field be deprecated as announced in release 16.04?
        ),
    ] = "file"
    created_from_basename: Optional[str] = Field(
        None,
        title="Created from basename",
        description="The basename of the output that produced this dataset.",  # TODO: is that correct?
    )
    hashes: Annotated[
        List[DatasetHash],
        Field(
            ...,
            title="Hashes",
            description="The list of hashes associated with this dataset.",
        ),
    ]
    drs_id: Annotated[
        str,
        Field(
            ...,
            title="DRS ID",
            description="The DRS ID of the dataset.",
        ),
    ]
    sources: Annotated[
        List[DatasetSource],
        Field(
            ...,
            title="Sources",
            description="The list of sources associated with this dataset.",
        ),
    ]
    copied_from_history_dataset_association_id: Annotated[
        Optional[EncodedDatabaseIdField], Field(None, description="ID of HDA this HDA was copied from.")
    ]


class HDAExtended(HDADetailed):
    """History Dataset Association extended information."""

    tool_version: str = Field(
        ...,
        title="Tool Version",
        description="The version of the tool that produced this dataset.",
    )
    parent_id: Optional[DecodedDatabaseIdField] = Field(
        None,
        title="Parent ID",
        description="TODO",
    )
    designation: Optional[str] = Field(
        None,
        title="Designation",
        description="TODO",
    )


class DCSummary(Model, WithModelClass):
    """Dataset Collection summary information."""

    model_class: DC_MODEL_CLASS = ModelClassField(DC_MODEL_CLASS)
    id: DatasetCollectionId
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    collection_type: CollectionType = CollectionTypeField
    populated_state: DatasetCollectionPopulatedState = PopulatedStateField
    populated_state_message: Optional[str] = PopulatedStateMessageField
    element_count: ElementCountField


class HDAObject(Model, WithModelClass):
    """History Dataset Association Object"""

    # TODO: Does it need to be serialized differently from HDASummary ?
    # If so at least merge models
    id: HistoryDatasetAssociationId
    model_class: HDA_MODEL_CLASS = ModelClassField(HDA_MODEL_CLASS)
    state: DatasetStateField
    hda_ldda: DatasetSourceType = HdaLddaField
    history_id: HistoryID
    tags: List[str]
    copied_from_ldda_id: Optional[EncodedDatabaseIdField] = None
    accessible: Optional[bool] = None
    purged: bool
    model_config = ConfigDict(extra="allow")


class DCObject(Model, WithModelClass):
    """Dataset Collection Object"""

    id: DatasetCollectionId
    model_class: DC_MODEL_CLASS = ModelClassField(DC_MODEL_CLASS)
    collection_type: CollectionType = CollectionTypeField
    populated: PopulatedField
    element_count: ElementCountField
    contents_url: Optional[ContentsUrlField] = None
    elements: List["DCESummary"] = ElementsField


class DCESummary(Model, WithModelClass):
    """Dataset Collection Element summary information."""

    id: DatasetCollectionElementId
    model_class: DCE_MODEL_CLASS = ModelClassField(DCE_MODEL_CLASS)
    element_index: int = Field(
        ...,
        title="Element Index",
        description="The position index of this element inside the collection.",
    )
    element_identifier: str = Field(
        ...,
        title="Element Identifier",
        description="The actual name of this element.",
    )
    element_type: Optional[DCEType] = Field(
        None,
        title="Element Type",
        description="The type of the element. Used to interpret the `object` field.",
    )
    object: Optional[Union[HDAObject, HDADetailed, DCObject]] = Field(
        None,
        title="Object",
        description="The element's specific data depending on the value of `element_type`.",
    )


DCObject.model_rebuild()


class DCDetailed(DCSummary):
    """Dataset Collection detailed information."""

    populated: PopulatedField
    elements: List[DCESummary] = ElementsField


class HDCJobStateSummary(Model):
    """Overview of the job states working inside a dataset collection."""

    all_jobs: int = Field(
        0,
        title="All jobs",
        description="Total number of jobs associated with a dataset collection.",
    )
    new: int = Field(
        0,
        title="New jobs",
        description="Number of jobs in the `new` state.",
    )
    waiting: int = Field(
        0,
        title="Waiting jobs",
        description="Number of jobs in the `waiting` state.",
    )
    running: int = Field(
        0,
        title="Running jobs",
        description="Number of jobs in the `running` state.",
    )
    error: int = Field(
        0,
        title="Jobs with errors",
        description="Number of jobs in the `error` state.",
    )
    paused: int = Field(
        0,
        title="Paused jobs",
        description="Number of jobs in the `paused` state.",
    )
    skipped: int = Field(
        0,
        title="Skipped jobs",
        description="Number of jobs that were skipped due to conditional workflow step execution.",
    )
    deleted_new: int = Field(
        0,
        title="Deleted new jobs",
        description="Number of jobs in the `deleted_new` state.",
    )
    resubmitted: int = Field(
        0,
        title="Resubmitted jobs",
        description="Number of jobs in the `resubmitted` state.",
    )
    queued: int = Field(
        0,
        title="Queued jobs",
        description="Number of jobs in the `queued` state.",
    )
    ok: int = Field(
        0,
        title="OK jobs",
        description="Number of jobs in the `ok` state.",
    )
    failed: int = Field(
        0,
        title="Failed jobs",
        description="Number of jobs in the `failed` state.",
    )
    deleted: int = Field(
        0,
        title="Deleted jobs",
        description="Number of jobs in the `deleted` state.",
    )
    upload: int = Field(
        0,
        title="Upload jobs",
        description="Number of jobs in the `upload` state.",
    )


class HDCACommon(HistoryItemCommon):
    history_content_type: Annotated[
        Literal["dataset_collection"],
        Field(
            title="History Content Type",
            description="This is always `dataset_collection` for dataset collections.",
        ),
    ]


class HDCASummary(HDCACommon, WithModelClass):
    """History Dataset Collection Association summary information."""

    model_class: HDCA_MODEL_CLASS = ModelClassField(HDCA_MODEL_CLASS)
    type: Annotated[
        Literal["collection"],
        Field(
            title="Type",
            description="This is always `collection` for dataset collections.",
        ),
    ] = "collection"

    collection_type: CollectionType = CollectionTypeField
    populated_state: DatasetCollectionPopulatedState = PopulatedStateField
    populated_state_message: Optional[str] = PopulatedStateMessageField
    element_count: ElementCountField
    elements_datatypes: Set[str] = Field(
        ..., description="A set containing all the different element datatypes in the collection."
    )
    job_source_id: Optional[EncodedDatabaseIdField] = Field(
        None,
        title="Job Source ID",
        description="The encoded ID of the Job that produced this dataset collection. Used to track the state of the job.",
    )
    job_source_type: Optional[JobSourceType] = Field(
        None,
        title="Job Source Type",
        description="The type of job (model class) that produced this dataset collection. Used to track the state of the job.",
    )
    job_state_summary: Optional[HDCJobStateSummary] = Field(
        None,
        title="Job State Summary",
        description="Overview of the job states working inside the dataset collection.",
    )
    contents_url: ContentsUrlField
    collection_id: DatasetCollectionId


class HDCADetailed(HDCASummary):
    """History Dataset Collection Association detailed information."""

    populated: PopulatedField
    elements: List[DCESummary] = ElementsField
    implicit_collection_jobs_id: Optional[EncodedDatabaseIdField] = Field(
        None,
        description="Encoded ID for the ICJ object describing the collection of jobs corresponding to this collection",
    )


class HistoryContentItemBase(Model):
    """Identifies a dataset or collection contained in a History."""

    history_content_type: HistoryContentType = Field(
        ...,
        title="Content Type",
        description="The type of this item.",
    )


class HistoryContentItem(HistoryContentItemBase):
    id: DecodedDatabaseIdField


class EncodedHistoryContentItem(HistoryContentItemBase):
    id: EncodedDatabaseIdField


class UpdateContentItem(HistoryContentItem):
    """Used for updating a particular history item. All fields are optional."""

    model_config = ConfigDict(use_enum_values=True, extra="allow")


class UpdateHistoryContentsBatchPayload(Model):
    """Contains property values that will be updated for all the history `items` provided."""

    items: List[UpdateContentItem] = Field(
        ...,
        title="Items",
        description="A list of content items to update with the changes.",
    )
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "items": [{"history_content_type": "dataset", "id": "string"}],
                "visible": False,
            }
        },
    )


class HistoryContentItemOperation(str, Enum):
    hide = "hide"
    unhide = "unhide"
    delete = "delete"
    undelete = "undelete"
    purge = "purge"
    change_datatype = "change_datatype"
    change_dbkey = "change_dbkey"
    add_tags = "add_tags"
    remove_tags = "remove_tags"


class BulkOperationParams(Model):
    type: str


class ChangeDatatypeOperationParams(BulkOperationParams):
    type: Literal["change_datatype"]
    datatype: str


class ChangeDbkeyOperationParams(BulkOperationParams):
    type: Literal["change_dbkey"]
    dbkey: str


class TagOperationParams(BulkOperationParams):
    type: Union[Literal["add_tags"], Literal["remove_tags"]]
    tags: List[str]


AnyBulkOperationParams = Union[
    ChangeDatatypeOperationParams,
    ChangeDbkeyOperationParams,
    TagOperationParams,
]


class HistoryContentBulkOperationPayload(Model):
    operation: HistoryContentItemOperation
    items: Optional[List[HistoryContentItem]] = None
    params: Optional[AnyBulkOperationParams] = None


class BulkOperationItemError(Model):
    item: EncodedHistoryContentItem
    error: str


class HistoryContentBulkOperationResult(Model):
    success_count: int
    errors: List[BulkOperationItemError]


class UpdateHistoryContentsPayload(Model):
    """Can contain arbitrary/dynamic fields that will be updated for a particular history item."""

    name: Optional[str] = Field(
        None,
        title="Name",
        description="The new name of the item.",
    )
    deleted: Optional[bool] = Field(
        None,
        title="Deleted",
        description="Whether this item is marked as deleted.",
    )
    visible: Optional[bool] = Field(
        None,
        title="Visible",
        description="Whether this item is visible in the history.",
    )
    annotation: Optional[str] = Field(
        None,
        title="Annotation",
        description="A user-defined annotation for this item.",
    )
    tags: Optional[TagCollection] = Field(
        None,
        title="Tags",
        description="A list of tags to add to this item.",
    )
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "visible": False,
                "annotation": "Test",
            }
        },
    )


class HistorySummary(Model, WithModelClass):
    """History summary information."""

    model_class: HISTORY_MODEL_CLASS = ModelClassField(HISTORY_MODEL_CLASS)
    id: HistoryID
    name: str = Field(
        ...,
        title="Name",
        description="The name of the history.",
    )
    deleted: bool = Field(
        ...,
        title="Deleted",
        description="Whether this item is marked as deleted.",
    )
    purged: bool = Field(
        ...,
        title="Purged",
        description="Whether this item has been permanently removed.",
    )
    archived: bool = Field(
        ...,
        title="Archived",
        description="Whether this item has been archived and is no longer active.",
    )
    url: RelativeUrlField
    published: bool = Field(
        ...,
        title="Published",
        description="Whether this resource is currently publicly available to all users.",
    )
    count: int = Field(
        ...,
        title="Count",
        description="The number of items in the history.",
    )
    annotation: Optional[str] = AnnotationField
    tags: TagCollection
    update_time: datetime = UpdateTimeField
    preferred_object_store_id: Optional[str] = PreferredObjectStoreIdField


class HistoryActiveContentCounts(Model):
    """Contains the number of active, deleted or hidden items in a History."""

    active: int = Field(
        ...,
        title="Active",
        description="Number of active datasets.",
    )
    hidden: int = Field(
        ...,
        title="Hidden",
        description="Number of hidden datasets.",
    )
    deleted: int = Field(
        ...,
        title="Deleted",
        description="Number of deleted datasets.",
    )


# TODO: https://github.com/galaxyproject/galaxy/issues/17785
HistoryStateCounts = Dict[DatasetState, int]
HistoryStateIds = Dict[DatasetState, List[DecodedDatabaseIdField]]

HistoryContentStates = Union[DatasetState, DatasetCollectionPopulatedState]
HistoryContentStateCounts = Dict[HistoryContentStates, int]


class HistoryDetailed(HistorySummary):  # Equivalent to 'dev-detailed' view, which seems the default
    """History detailed information."""

    contents_url: ContentsUrlField
    size: int = Field(
        ...,
        title="Size",
        description="The total size of the contents of this history in bytes.",
    )
    user_id: Optional[EncodedDatabaseIdField] = Field(
        None,
        title="User ID",
        description="The encoded ID of the user that owns this History.",
    )
    create_time: datetime = CreateTimeField
    importable: bool = Field(
        ...,
        title="Importable",
        description="Whether this History can be imported by other users with a shared link.",
    )
    slug: Optional[str] = Field(
        None,
        title="Slug",
        description="Part of the URL to uniquely identify this History by link in a readable way.",
    )
    username: Optional[str] = Field(
        None,
        title="Username",
        description="Owner of the history",
    )
    username_and_slug: Optional[str] = Field(
        None,
        title="Username and slug",
        description="The relative URL in the form of /u/{username}/h/{slug}",
    )
    genome_build: Optional[str] = GenomeBuildField
    state: DatasetState = Field(
        ...,
        title="State",
        description="The current state of the History based on the states of the datasets it contains.",
    )
    state_ids: HistoryStateIds = Field(
        ...,
        title="State IDs",
        description=(
            "A dictionary keyed to possible dataset states and valued with lists "
            "containing the ids of each HDA in that state."
        ),
    )
    state_details: HistoryStateCounts = Field(
        ...,
        title="State Counts",
        description=(
            "A dictionary keyed to possible dataset states and valued with the number "
            "of datasets in this history that have those states."
        ),
    )


@partial_model()
class CustomHistoryView(HistoryDetailed):
    """History Response with all optional fields.

    It is used for serializing only specific attributes using the "keys"
    query parameter. Unfortunately, we cannot know the exact fields that
    will be requested, so we have to allow all fields to be optional.
    """

    # Define a few more useful fields to be optional that are not part of HistoryDetailed
    contents_active: Optional[HistoryActiveContentCounts] = Field(
        default=None,
        title="Contents Active",
        description=("Contains the number of active, deleted or hidden items in a History."),
    )
    contents_states: Optional[HistoryContentStateCounts] = Field(
        default=None,
        title="Contents States",
        description="A dictionary keyed to possible dataset states and valued with the number of datasets in this history that have those states.",
    )
    nice_size: Optional[str] = Field(
        default=None,
        title="Nice Size",
        description="The total size of the contents of this history in a human-readable format.",
    )


AnyHistoryView = Annotated[
    Union[
        CustomHistoryView,
        HistoryDetailed,
        HistorySummary,
    ],
    Field(union_mode="left_to_right"),
]


class UpdateHistoryPayload(Model):
    name: Optional[str] = None
    annotation: Optional[str] = None
    tags: Optional[TagCollection] = None
    published: Optional[bool] = None
    importable: Optional[bool] = None
    deleted: Optional[bool] = None
    purged: Optional[bool] = None
    genome_build: Optional[str] = None
    preferred_object_store_id: Optional[str] = None


class ExportHistoryArchivePayload(Model):
    gzip: Optional[bool] = Field(
        default=True,
        title="GZip",
        description="Whether to export as gzip archive.",
    )
    include_hidden: Optional[bool] = Field(
        default=False,
        title="Include Hidden",
        description="Whether to include hidden datasets in the exported archive.",
    )
    include_deleted: Optional[bool] = Field(
        default=False,
        title="Include Deleted",
        description="Whether to include deleted datasets in the exported archive.",
    )
    file_name: Optional[str] = Field(
        default=None,
        title="File Name",
        description="The name of the file containing the exported history.",
    )
    directory_uri: Optional[str] = Field(
        default=None,
        title="Directory URI",
        description=(
            "A writable directory destination where the history will be exported "
            "using the `galaxy.files` URI infrastructure."
        ),
    )
    force: Optional[bool] = Field(  # Hack to force rebuild everytime during dev
        default=None,
        title="Force Rebuild",
        description="Whether to force a rebuild of the history archive.",
    )


WorkflowSortByEnum = Literal["create_time", "update_time", "name"]


class WorkflowIndexQueryPayload(Model):
    show_deleted: bool = False
    show_hidden: bool = False
    show_published: Optional[bool] = None
    show_shared: Optional[bool] = None
    sort_by: Optional[WorkflowSortByEnum] = Field(None, title="Sort By", description="Sort workflows by this attribute")
    sort_desc: Optional[bool] = Field(
        None, title="Sort descending", description="Explicitly sort by descending if sort_by is specified."
    )
    limit: Optional[int] = Field(
        default=None,
        lt=1000,
    )
    offset: Optional[int] = Field(default=0, description="Number of workflows to skip")
    search: Optional[str] = Field(default=None, title="Filter text", description="Freetext to search.")
    skip_step_counts: bool = False


class JobIndexSortByEnum(str, Enum):
    create_time = "create_time"
    update_time = "update_time"


class JobIndexQueryPayload(Model):
    states: Optional[List[str]] = None
    user_details: bool = False
    user_id: Optional[DecodedDatabaseIdField] = None
    tool_ids: Optional[List[str]] = None
    tool_ids_like: Optional[List[str]] = None
    date_range_min: Optional[Union[OffsetNaiveDatetime, date]] = None
    date_range_max: Optional[Union[OffsetNaiveDatetime, date]] = None
    history_id: Optional[DecodedDatabaseIdField] = None
    workflow_id: Optional[DecodedDatabaseIdField] = None
    invocation_id: Optional[DecodedDatabaseIdField] = None
    implicit_collection_jobs_id: Optional[DecodedDatabaseIdField] = None
    order_by: JobIndexSortByEnum = JobIndexSortByEnum.update_time
    search: Optional[str] = None
    limit: int = 500
    offset: int = 0


class InvocationSortByEnum(str, Enum):
    create_time = "create_time"
    update_time = "update_time"
    none = None


class InvocationIndexQueryPayload(Model):
    workflow_id: Optional[int] = Field(
        None, title="Workflow ID", description="Return only invocations for this Workflow ID"
    )
    history_id: Optional[int] = Field(
        None, title="History ID", description="Return only invocations for this History ID"
    )
    job_id: Optional[int] = Field(None, title="Job ID", description="Return only invocations for this Job ID")
    user_id: Optional[int] = Field(None, title="User ID", description="Return invocations for this User ID")
    sort_by: Optional[InvocationSortByEnum] = Field(
        None, title="Sort By", description="Sort Workflow Invocations by this attribute"
    )
    sort_desc: bool = Field(default=False, description="Sort in descending order?")
    include_terminal: bool = Field(default=True, description="Set to false to only include terminal Invocations.")
    limit: Optional[int] = Field(
        default=100,
        lt=1000,
    )
    offset: Optional[int] = Field(default=0, description="Number of invocations to skip")
    include_nested_invocations: bool = True


PageSortByEnum = Literal["create_time", "title", "update_time", "username"]


class PageIndexQueryPayload(Model):
    deleted: bool = False
    limit: Optional[int] = Field(default=100, lt=1000, title="Limit", description="Maximum number of pages to return.")
    offset: Optional[int] = Field(default=0, title="Offset", description="Number of pages to skip.")
    show_own: Optional[bool] = None
    show_published: Optional[bool] = None
    show_shared: Optional[bool] = None
    search: Optional[str] = Field(default=None, title="Filter text", description="Freetext to search.")
    sort_by: PageSortByEnum = Field("update_time", title="Sort By", description="Sort pages by this attribute.")
    sort_desc: Optional[bool] = Field(default=False, title="Sort descending", description="Sort in descending order.")
    user_id: Optional[DecodedDatabaseIdField] = None


class CreateHistoryPayload(Model):
    name: Optional[str] = Field(
        default=None,
        title="Name",
        description="The new history name.",
    )
    history_id: Optional[DecodedDatabaseIdField] = Field(
        default=None,
        title="History ID",
        description=(
            "The encoded ID of the history to copy. Provide this value only if you want to copy an existing history."
        ),
    )
    all_datasets: Optional[bool] = Field(
        default=True,
        title="All Datasets",
        description=(
            "Whether to copy also deleted HDAs/HDCAs. Only applies when providing a `history_id` to copy from."
        ),
    )
    archive_source: Optional[str] = Field(
        default=None,
        title="Archive Source",
        description=("The URL that will generate the archive to import when `archive_type='url'`. "),
    )
    archive_type: Optional[HistoryImportArchiveSourceType] = Field(
        default=HistoryImportArchiveSourceType.url,
        title="Archive Type",
        description="The type of source from where the new history will be imported.",
    )
    archive_file: Optional[Any] = Field(
        default=None,
        title="Archive File",
        description="Uploaded file information when importing the history from a file.",
    )


class CollectionElementIdentifier(Model):
    name: Optional[str] = Field(
        None,
        title="Name",
        description="The name of the element.",
    )
    src: ColletionSourceType = Field(
        ...,
        title="Source",
        description="The source of the element.",
    )
    id: Optional[DecodedDatabaseIdField] = Field(
        default=None,
        title="ID",
        description="The encoded ID of the element.",
    )
    collection_type: Optional[CollectionType] = OptionalCollectionTypeField
    element_identifiers: Optional[List["CollectionElementIdentifier"]] = Field(
        default=None,
        title="Element Identifiers",
        description="List of elements that should be in the new sub-collection.",
    )
    tags: Optional[List[str]] = Field(
        default=None,
        title="Tags",
        description="The list of tags associated with the element.",
    )


class CreateNewCollectionPayload(Model):
    collection_type: Optional[CollectionType] = OptionalCollectionTypeField
    element_identifiers: Optional[List[CollectionElementIdentifier]] = Field(
        default=None,
        title="Element Identifiers",
        description="List of elements that should be in the new collection.",
    )
    name: Optional[str] = Field(
        default=None,
        title="Name",
        description="The name of the new collection.",
    )
    hide_source_items: Optional[bool] = Field(
        default=False,
        title="Hide Source Items",
        description="Whether to mark the original HDAs as hidden.",
    )
    copy_elements: Optional[bool] = Field(
        default=True,
        title="Copy Elements",
        description="Whether to create a copy of the source HDAs for the new collection.",
    )
    instance_type: Optional[DatasetCollectionInstanceType] = Field(
        default="history",
        title="Instance Type",
        description="The type of the instance, either `history` (default) or `library`.",
    )
    history_id: Optional[DecodedDatabaseIdField] = Field(
        default=None,
        description="The ID of the history that will contain the collection. Required if `instance_type=history`.",
    )
    folder_id: Optional[LibraryFolderDatabaseIdField] = Field(
        default=None,
        description="The ID of the library folder that will contain the collection. Required if `instance_type=library`.",
    )


class ModelStoreFormat(str, Enum):
    """Available types of model stores for export."""

    TGZ = "tgz"
    TAR = "tar"
    TAR_DOT_GZ = "tar.gz"
    BAG_DOT_ZIP = "bag.zip"
    BAG_DOT_TAR = "bag.tar"
    BAG_DOT_TGZ = "bag.tgz"
    ROCRATE_ZIP = "rocrate.zip"
    BCO_JSON = "bco.json"

    @classmethod
    def is_compressed(cls, value: "ModelStoreFormat"):
        return value in [cls.TAR_DOT_GZ, cls.TGZ, cls.TAR, cls.ROCRATE_ZIP]

    @classmethod
    def is_bag(cls, value: "ModelStoreFormat"):
        return value in [cls.BAG_DOT_TAR, cls.BAG_DOT_TGZ, cls.BAG_DOT_ZIP]
    
    @classmethod
    def available_formats(cls):
        return [item.value for item in cls]

class StoreContentSource(Model):
    store_content_uri: Optional[str] = None
    store_dict: Optional[Dict[str, Any]] = None
    model_store_format: Optional["ModelStoreFormat"] = None


class CreateHistoryFromStore(StoreContentSource):
    pass


class StoreExportPayload(Model):
    model_store_format: ModelStoreFormat = Field(
        default=ModelStoreFormat.TAR_DOT_GZ,
        description="format of model store to export",
    )
    include_files: bool = Field(
        default=True,
        description="include materialized files in export when available",
    )
    include_deleted: bool = Field(
        default=False,
        title="Include deleted",
        description="Include file contents for deleted datasets (if include_files is True).",
    )
    include_hidden: bool = Field(
        default=False,
        title="Include hidden",
        description="Include file contents for hidden datasets (if include_files is True).",
    )


class ShortTermStoreExportPayload(StoreExportPayload):
    short_term_storage_request_id: UUID
    duration: OptionalNumberT = None


class BcoGenerationParametersMixin(BaseModel):
    bco_merge_history_metadata: bool = Field(
        default=False, description="When reading tags/annotations to generate BCO object include history metadata."
    )
    bco_override_environment_variables: Optional[Dict[str, str]] = Field(
        default=None,
        description="Override environment variables for 'execution_domain' when generating BioCompute object.",
    )
    bco_override_empirical_error: Optional[Dict[str, str]] = Field(
        default=None,
        description="Override empirical error for 'error domain' when generating BioCompute object.",
    )
    bco_override_algorithmic_error: Optional[Dict[str, str]] = Field(
        default=None,
        description="Override algorithmic error for 'error domain' when generating BioCompute object.",
    )
    bco_override_xref: Optional[List[XrefItem]] = Field(
        default=None,
        description="Override xref for 'description domain' when generating BioCompute object.",
    )


class WriteStoreToPayload(StoreExportPayload):
    target_uri: str = Field(
        ...,
        title="Target URI",
        description="Galaxy Files URI to write mode store content to.",
    )


class ObjectExportResponseBase(Model):
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="The encoded database ID of the export request.",
    )
    ready: bool = Field(
        ...,
        title="Ready",
        description="Whether the export has completed successfully and the archive is ready",
    )
    preparing: bool = Field(
        ...,
        title="Preparing",
        description="Whether the archive is currently being built or in preparation.",
    )
    up_to_date: bool = Field(
        ...,
        title="Up to Date",
        description="False, if a new export archive should be generated.",
    )


class JobExportHistoryArchiveModel(ObjectExportResponseBase):
    job_id: EncodedDatabaseIdField = Field(
        ...,
        title="Job ID",
        description="The encoded database ID of the job that generated this history export archive.",
    )
    download_url: RelativeUrl = Field(
        ...,
        title="Download URL",
        description="Relative API URL to download the exported history archive.",
    )
    external_download_latest_url: AnyUrl = Field(
        ...,
        title="External Download Latest URL",
        description="Fully qualified URL to download the latests version of the exported history archive.",
    )
    external_download_permanent_url: AnyUrl = Field(
        ...,
        title="External Download Permanent URL",
        description="Fully qualified URL to download this particular version of the exported history archive.",
    )


class ExportObjectType(str, Enum):
    """Types of objects that can be exported."""

    HISTORY = "history"
    INVOCATION = "invocation"


class ExportObjectRequestMetadata(Model):
    object_id: EncodedDatabaseIdField
    object_type: ExportObjectType
    user_id: Optional[EncodedDatabaseIdField] = None
    payload: Union[WriteStoreToPayload, ShortTermStoreExportPayload]


class ExportObjectResultMetadata(Model):
    success: bool
    uri: Optional[str] = None
    error: Optional[str] = None

    @model_validator(mode="after")
    @classmethod
    def validate_success(cls, model):
        """
        Ensure successful exports do not have error text.
        """
        if model.success and model.error is not None:
            raise ValueError("successful exports cannot have error text")

        return model

    @model_validator(mode="after")
    @classmethod
    def validate_uri(cls, model):
        """
        Ensure unsuccessful exports do not have a URI.
        """

        if not model.success and model.uri:
            raise ValueError("unsuccessful exports cannot have a URI")

        return model


class ExportObjectMetadata(Model):
    request_data: ExportObjectRequestMetadata
    result_data: Optional[ExportObjectResultMetadata] = None

    def is_short_term(self):
        """Whether the export is a short term export."""
        return isinstance(self.request_data.payload, ShortTermStoreExportPayload)

    def is_ready(self):
        """Whether the export has finished and it's ready to be used."""
        return self.result_data is not None and self.result_data.success


class ObjectExportTaskResponse(ObjectExportResponseBase):
    task_uuid: UUID4 = Field(
        ...,
        title="Task ID",
        description="The identifier of the task processing the export.",
    )
    create_time: datetime = CreateTimeField
    export_metadata: Optional[ExportObjectMetadata] = None


class JobExportHistoryArchiveListResponse(RootModel):
    root: List[JobExportHistoryArchiveModel]


class ExportTaskListResponse(RootModel):
    root: List[ObjectExportTaskResponse]
    __accept_type__ = "application/vnd.galaxy.task.export+json"


class ArchiveHistoryRequestPayload(Model):
    archive_export_id: Optional[DecodedDatabaseIdField] = Field(
        default=None,
        title="Export Record ID",
        description=(
            "The encoded ID of the export record to associate with this history archival."
            "This is used to be able to recover the history from the export record."
        ),
    )
    purge_history: bool = Field(
        default=False,
        title="Purge History",
        description="Whether to purge the history after archiving it. It requires an `archive_export_id` to be set.",
    )


class ExportRecordData(WriteStoreToPayload):
    """Data of an export record associated with a history that was archived."""

    # Initially this is just a WriteStoreToPayload, but we may want to add more data to
    # this in the future to support more complex export scenarios or target destinations.
    pass


class ExportAssociationData(Model):
    export_record_data: Optional[ExportRecordData] = Field(
        default=None,
        title="Export Record Data",
        description="The export record data associated with this archived history. Used to recover the history.",
    )


class ArchivedHistorySummary(HistorySummary, ExportAssociationData):
    pass


class ArchivedHistoryDetailed(HistoryDetailed, ExportAssociationData):
    pass


@partial_model()
class CustomArchivedHistoryView(CustomHistoryView, ExportAssociationData):
    """Archived History Response with all optional fields.

    It is used for serializing only specific attributes using the "keys"
    query parameter.
    """

    pass


AnyArchivedHistoryView = Annotated[
    Union[
        CustomArchivedHistoryView,
        ArchivedHistoryDetailed,
        ArchivedHistorySummary,
    ],
    Field(union_mode="left_to_right"),
]


class LabelValuePair(Model):
    """Generic Label/Value pair model."""

    label: str = Field(
        ...,
        title="Label",
        description="The label of the item.",
    )
    value: str = Field(
        ...,
        title="Value",
        description="The value of the item.",
    )


class CustomBuildsMetadataResponse(Model):
    installed_builds: List[LabelValuePair] = Field(
        ...,
        title="Installed Builds",
        description="TODO",
    )
    fasta_hdas: List[LabelValuePair] = Field(
        ...,
        title="Fasta HDAs",
        description=(
            "A list of label/value pairs with all the datasets of type `FASTA` contained in the History.\n"
            " - `label` is item position followed by the name of the dataset.\n"
            " - `value` is the encoded database ID of the dataset.\n"
        ),
    )


class JobIdResponse(Model):
    """Contains the ID of the job associated with a particular request."""

    job_id: JobId


class JobBaseModel(Model, WithModelClass):
    id: JobId
    history_id: Optional[EncodedDatabaseIdField] = Field(
        None,
        title="History ID",
        description="The encoded ID of the history associated with this item.",
    )
    model_class: JOB_MODEL_CLASS = ModelClassField(JOB_MODEL_CLASS)
    tool_id: str = Field(
        ...,
        title="Tool ID",
        description="Identifier of the tool that generated this job.",
    )
    state: JobState = Field(
        ...,
        title="State",
        description="Current state of the job.",
    )
    exit_code: Optional[int] = Field(
        None,
        title="Exit Code",
        description="The exit code returned by the tool. Can be unset if the job is not completed yet.",
    )
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    galaxy_version: Optional[str] = Field(
        default=None,
        title="Galaxy Version",
        description="The (major) version of Galaxy used to create this job.",
        examples=["21.05"],
    )


class JobImportHistoryResponse(JobBaseModel):
    message: str = Field(
        ...,
        title="Message",
        description="Text message containing information about the history import.",
    )


class ItemStateSummary(Model):
    id: EncodedDatabaseIdField
    populated_state: DatasetCollectionPopulatedState = PopulatedStateField
    states: Dict[JobState, int] = Field(
        {}, title="States", description=("A dictionary of job states and the number of jobs in that state.")
    )


class JobStateSummary(ItemStateSummary):
    model: Literal["Job"] = ModelClassField(Literal["Job"])


class ImplicitCollectionJobsStateSummary(ItemStateSummary):
    model: Literal["ImplicitCollectionJobs"] = ModelClassField(Literal["ImplicitCollectionJobs"])


class WorkflowInvocationStateSummary(ItemStateSummary):
    model: Literal["WorkflowInvocation"] = ModelClassField(Literal["WorkflowInvocation"])


class JobSummary(JobBaseModel):
    """Basic information about a job."""

    external_id: Optional[str] = Field(
        None,
        title="External ID",
        description="The job id used by the external job runner (Condor, Pulsar, etc.). Only administrator can see this value.",
    )
    handler: Optional[str] = Field(
        None,
        title="Job Handler",
        description="The job handler process assigned to handle this job. Only administrator can see this value.",
    )
    job_runner_name: Optional[str] = Field(
        None,
        title="Job Runner Name",
        description="Name of the job runner plugin that handles this job. Only administrator can see this value.",
    )
    command_line: Optional[str] = Field(
        None,
        title="Command Line",
        description=(
            "The command line produced by the job. "
            "Users can see this value if allowed in the configuration, administrator can always see this value."
        ),
    )
    user_email: Optional[str] = Field(
        None,
        title="User Email",
        description=(
            "The email of the user that owns this job. "
            "Only the owner of the job and administrators can see this value."
        ),
    )


class DatasetSourceIdBase(Model):
    src: DatasetSourceType = Field(
        ...,
        title="Source",
        description="The source of this dataset, either `hda` or `ldda` depending of its origin.",
    )


class DatasetSourceId(DatasetSourceIdBase):
    id: DecodedDatabaseIdField


class EncodedDatasetSourceId(DatasetSourceIdBase):
    id: EncodedDatabaseIdField


class EncodedDataItemSourceId(Model):
    id: EncodedDatabaseIdField
    src: DataItemSourceType = Field(
        ...,
        title="Source",
        description="The source of this dataset, either `hda`, `ldda`, `hdca`, `dce` or `dc` depending of its origin.",
    )


class EncodedJobParameterHistoryItem(EncodedDataItemSourceId):
    hid: Optional[int] = None
    name: str


class DatasetJobInfo(DatasetSourceId):
    uuid: UuidField


class JobDetails(JobSummary):
    command_version: str = Field(
        ...,
        title="Command Version",
        description="Tool version indicated during job execution.",
    )
    params: Any = Field(
        None,
        title="Parameters",
        description=(
            "Object containing all the parameters of the tool associated with this job. "
            "The specific parameters depend on the tool itself."
        ),
    )
    inputs: Dict[str, DatasetJobInfo] = Field(
        {},
        title="Inputs",
        description="Dictionary mapping all the tool inputs (by name) with the corresponding dataset information.",
    )
    outputs: Dict[str, DatasetJobInfo] = Field(
        {},
        title="Outputs",
        description="Dictionary mapping all the tool outputs (by name) with the corresponding dataset information.",
    )


class JobMetric(Model):
    title: str = Field(
        ...,
        title="Title",
        description="A descriptive title for this metric.",
    )
    value: str = Field(
        ...,
        title="Value",
        description="The textual representation of the metric value.",
    )
    plugin: str = Field(
        ...,
        title="Plugin",
        description="The instrumenter plugin that generated this metric.",
    )
    name: str = Field(
        ...,
        title="Name",
        description="The name of the metric variable.",
    )
    raw_value: str = Field(
        ...,
        title="Raw Value",
        description="The raw value of the metric as a string.",
    )
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Job Start Time",
                "value": "2021-02-25 14:55:40",
                "plugin": "core",
                "name": "start_epoch",
                "raw_value": "1614261340.0000000",
            }
        }
    )


class WorkflowJobMetric(JobMetric):
    tool_id: str
    job_id: str
    step_index: int
    step_label: Optional[str]


class JobMetricCollection(RootModel):
    """Represents a collection of metrics associated with a Job."""

    root: List[JobMetric] = Field(
        [],
        title="Job Metrics",
        description="Collections of metrics provided by `JobInstrumenter` plugins on a particular job.",
    )


class JobFullDetails(JobDetails):
    tool_stdout: str = Field(
        ...,
        title="Tool Standard Output",
        description="The captured standard output of the tool executed by the job.",
    )
    tool_stderr: str = Field(
        ...,
        title="Tool Standard Error",
        description="The captured standard error of the tool executed by the job.",
    )
    job_stdout: str = Field(
        ...,
        title="Job Standard Output",
        description="The captured standard output of the job execution.",
    )
    job_stderr: str = Field(
        ...,
        title="Job Standard Error",
        description="The captured standard error of the job execution.",
    )
    stdout: str = Field(  # Redundant? it seems to be (tool_stdout + "\n" + job_stdout)
        ...,
        title="Standard Output",
        description="Combined tool and job standard output streams.",
    )
    stderr: str = Field(  # Redundant? it seems to be (tool_stderr + "\n" + job_stderr)
        ...,
        title="Standard Error",
        description="Combined tool and job standard error streams.",
    )
    job_messages: List[str] = Field(
        ...,
        title="Job Messages",
        description="List with additional information and possible reasons for a failed job.",
    )
    job_metrics: Optional[JobMetricCollection] = Field(
        None,
        title="Job Metrics",
        description=(
            "Collections of metrics provided by `JobInstrumenter` plugins on a particular job. "
            "Only administrators can see these metrics."
        ),
    )


class StoredWorkflowSummary(Model, WithModelClass):
    id: EncodedDatabaseIdField
    model_class: STORED_WORKFLOW_MODEL_CLASS = ModelClassField(STORED_WORKFLOW_MODEL_CLASS)
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    name: str = Field(
        ...,
        title="Name",
        description="The name of the history.",
    )
    url: RelativeUrlField
    published: bool = Field(
        ...,
        title="Published",
        description="Whether this workflow is currently publicly available to all users.",
    )
    annotations: Optional[List[str]] = (
        Field(  # Inconsistency? Why workflows summaries use a list instead of an optional string?
            None,
            title="Annotations",
            description="An list of annotations to provide details or to help understand the purpose and usage of this workflow.",
        )
    )
    tags: TagCollection
    deleted: bool = Field(
        ...,
        title="Deleted",
        description="Whether this item is marked as deleted.",
    )
    hidden: bool = Field(
        ...,
        title="Hidden",
        description="TODO",
    )
    owner: str = Field(
        ...,
        title="Owner",
        description="The name of the user who owns this workflow.",
    )
    latest_workflow_uuid: Optional[UUID4] = Field(
        None,
        title="Latest workflow UUID",
        description="TODO",
    )
    number_of_steps: Optional[int] = Field(
        None,
        title="Number of Steps",
        description="The number of steps that make up this workflow.",
    )
    show_in_tool_panel: Optional[bool] = Field(
        None,
        title="Show in Tool Panel",
        description="Whether to display this workflow in the Tools Panel.",
    )


class WorkflowInput(Model):
    label: Optional[str] = Field(
        ...,
        title="Label",
        description="Label of the input.",
    )
    value: Optional[Any] = Field(
        ...,
        title="Value",
        description="TODO",
    )
    uuid: Optional[UUID4] = Field(
        ...,
        title="UUID",
        description="Universal unique identifier of the input.",
    )


class WorkflowOutput(Model):
    label: Optional[str] = Field(
        None,
        title="Label",
        description="Label of the output.",
    )
    output_name: str = Field(
        ...,
        title="Output Name",
        description="The name assigned to the output.",
    )
    uuid: Optional[UUID4] = Field(
        None,
        title="UUID",
        description="Universal unique identifier of the output.",
    )


class InputStep(Model):
    source_step: int = Field(
        ...,
        title="Source Step",
        description="The identifier of the workflow step connected to this particular input.",
    )
    step_output: str = Field(
        ...,
        title="Step Output",
        description="The name of the output generated by the source step.",
    )


class WorkflowStepBase(Model):
    id: int = Field(
        ...,
        title="ID",
        description="The identifier of the step. It matches the index order of the step inside the workflow.",
    )
    annotation: Optional[str] = AnnotationField
    input_steps: Dict[str, InputStep] = Field(
        ...,
        title="Input Steps",
        description="A dictionary containing information about the inputs connected to this workflow step.",
    )
    when: Optional[str]
    # TODO: these should move to ToolStep, however we might be breaking scripts that iterate over steps and
    # assume tool_id is a valid key for every step.
    tool_id: Optional[str] = Field(
        None, title="Tool ID", description="The unique name of the tool associated with this step."
    )
    tool_version: Optional[str] = Field(
        None, title="Tool Version", description="The version of the tool associated with this step."
    )
    tool_inputs: Any = Field(None, title="Tool Inputs", description="TODO")


class InputDataStep(WorkflowStepBase):
    type: Literal["data_input"]


class InputDataCollectionStep(WorkflowStepBase):
    type: Literal["data_collection_input"]


class InputParameterStep(WorkflowStepBase):
    type: Literal["parameter_input"]


class PauseStep(WorkflowStepBase):
    type: Literal["pause"]


class ToolStep(WorkflowStepBase):
    type: Literal["tool"]


class SubworkflowStep(WorkflowStepBase):
    type: Literal["subworkflow"]
    workflow_id: EncodedDatabaseIdField = Field(
        ..., title="Workflow ID", description="The encoded ID of the workflow that will be run on this step."
    )


class Creator(Model):
    class_: str = Field(..., alias="class", title="Class", description="The class representing this creator.")
    name: Optional[str] = Field(None, title="Name", description="The name of the creator.")
    address: Optional[str] = Field(
        None,
        title="Address",
    )
    alternate_name: Optional[str] = Field(
        None,
        alias="alternateName",
        title="Alternate Name",
    )
    email: Optional[str] = Field(
        None,
        title="Email",
    )
    fax_number: Optional[str] = Field(
        None,
        alias="faxNumber",
        title="Fax Number",
    )
    identifier: Optional[str] = Field(None, title="Identifier", description="Identifier (typically an orcid.org ID)")
    image: Optional[AnyHttpUrl] = Field(
        None,
        title="Image URL",
    )
    telephone: Optional[str] = Field(
        None,
        title="Telephone",
    )
    url: Optional[AnyHttpUrl] = Field(
        None,
        title="URL",
    )


class Organization(Creator):
    class_: str = Field(
        "Organization",
        alias="class",
    )


class Person(Creator):
    class_: str = Field(
        "Person",
        alias="class",
    )
    family_name: Optional[str] = Field(
        None,
        alias="familyName",
        title="Family Name",
    )
    givenName: Optional[str] = Field(
        None,
        alias="givenName",
        title="Given Name",
    )
    honorific_prefix: Optional[str] = Field(
        None,
        alias="honorificPrefix",
        title="Honorific Prefix",
        description="Honorific Prefix (e.g. Dr/Mrs/Mr)",
    )
    honorific_suffix: Optional[str] = Field(
        None, alias="honorificSuffix", title="Honorific Suffix", description="Honorific Suffix (e.g. M.D.)"
    )
    job_title: Optional[str] = Field(
        None,
        alias="jobTitle",
        title="Job Title",
    )


class Input(Model):
    name: str = Field(..., title="Name", description="The name of the input.")
    description: str = Field(..., title="Description", description="The annotation or description of the input.")


class Output(Model):
    name: str = Field(..., title="Name", description="The name of the output.")
    type: str = Field(..., title="Type", description="The extension or type of output.")


class InputConnection(Model):
    id: int = Field(..., title="ID", description="The identifier of the input.")
    output_name: str = Field(
        ...,
        title="Output Name",
        description="The name assigned to the output.",
    )
    input_subworkflow_step_id: Optional[int] = Field(
        None,
        title="Input Subworkflow Step ID",
        description="TODO",
    )


class WorkflowStepLayoutPosition(Model):
    """Position and dimensions of the workflow step represented by a box on the graph."""

    bottom: int = Field(..., title="Bottom", description="Position in pixels of the bottom of the box.")
    top: int = Field(..., title="Top", description="Position in pixels of the top of the box.")
    left: int = Field(..., title="Left", description="Left margin or left-most position of the box.")
    right: int = Field(..., title="Right", description="Right margin or right-most position of the box.")
    x: int = Field(..., title="X", description="Horizontal pixel coordinate of the top right corner of the box.")
    y: int = Field(..., title="Y", description="Vertical pixel coordinate of the top right corner of the box.")
    height: int = Field(..., title="Height", description="Height of the box in pixels.")
    width: int = Field(..., title="Width", description="Width of the box in pixels.")


InvocationsStateCounts = RootModel[Dict[str, int]]


class WorkflowStepToExportBase(Model):
    id: int = Field(
        ...,
        title="ID",
        description="The identifier of the step. It matches the index order of the step inside the workflow.",
    )
    type: str = Field(..., title="Type", description="The type of workflow module.")
    name: str = Field(..., title="Name", description="The descriptive name of the module or step.")
    annotation: Optional[str] = AnnotationField
    tool_id: Optional[str] = Field(  # Duplicate of `content_id` or viceversa?
        None, title="Tool ID", description="The unique name of the tool associated with this step."
    )
    uuid: UUID4 = Field(
        ...,
        title="UUID",
        description="Universal unique identifier of the workflow.",
    )
    label: Optional[str] = Field(
        None,
        title="Label",
    )
    inputs: List[Input] = Field(
        ...,
        title="Inputs",
        description="TODO",
    )
    outputs: List[Output] = Field(
        ...,
        title="Outputs",
        description="TODO",
    )
    input_connections: Dict[str, InputConnection] = Field(
        {},
        title="Input Connections",
        description="TODO",
    )
    position: WorkflowStepLayoutPosition = Field(
        ...,
        title="Position",
        description="Layout position of this step in the graph",
    )
    workflow_outputs: List[WorkflowOutput] = Field(
        [], title="Workflow Outputs", description="Workflow outputs associated with this step."
    )


class WorkflowStepToExport(WorkflowStepToExportBase):
    content_id: Optional[str] = Field(  # Duplicate of `tool_id` or viceversa?
        None, title="Content ID", description="TODO"
    )
    tool_version: Optional[str] = Field(
        None, title="Tool Version", description="The version of the tool associated with this step."
    )
    tool_state: Json = Field(
        ...,
        title="Tool State",
        description="JSON string containing the serialized representation of the persistable state of the step.",
    )
    errors: Optional[str] = Field(
        None,
        title="Errors",
        description="An message indicating possible errors in the step.",
    )


class ToolShedRepositorySummary(Model):
    name: str = Field(
        ...,
        title="Name",
        description="The name of the repository.",
    )
    owner: str = Field(
        ...,
        title="Owner",
        description="The owner of the repository.",
    )
    changeset_revision: str = Field(
        ...,
        title="Changeset Revision",
        description="TODO",
    )
    tool_shed: str = Field(
        ...,
        title="Tool Shed",
        description="The Tool Shed base URL.",
    )


class PostJobAction(Model):
    action_type: str = Field(
        ...,
        title="Action Type",
        description="The type of action to run.",
    )
    output_name: str = Field(
        ...,
        title="Output Name",
        description="The name of the output that will be affected by the action.",
    )
    action_arguments: Dict[str, Any] = Field(
        ...,
        title="Action Arguments",
        description="Any additional arguments needed by the action.",
    )


class WorkflowToolStepToExport(WorkflowStepToExportBase):
    tool_shed_repository: ToolShedRepositorySummary = Field(
        ..., title="Tool Shed Repository", description="Information about the origin repository of this tool."
    )
    post_job_actions: Dict[str, PostJobAction] = Field(
        ..., title="Post-job Actions", description="Set of actions that will be run when the job finish."
    )


class SubworkflowStepToExport(WorkflowStepToExportBase):
    subworkflow: "WorkflowToExport" = Field(
        ..., title="Subworkflow", description="Full information about the subworkflow associated with this step."
    )


class WorkflowToExport(Model):
    a_galaxy_workflow: str = Field(  # Is this meant to be a bool instead?
        "true", title="Galaxy Workflow", description="Whether this workflow is a Galaxy Workflow."
    )
    format_version: str = Field(
        "0.1",
        alias="format-version",  # why this field uses `-` instead of `_`?
        title="Galaxy Workflow",
        description="Whether this workflow is a Galaxy Workflow.",
    )
    name: str = Field(..., title="Name", description="The name of the workflow.")
    annotation: Optional[str] = AnnotationField
    tags: TagCollection
    uuid: Optional[UUID4] = Field(
        None,
        title="UUID",
        description="Universal unique identifier of the workflow.",
    )
    creator: Optional[List[Union[Person, Organization]]] = Field(
        None,
        title="Creator",
        description=("Additional information about the creator (or multiple creators) of this workflow."),
    )
    license: Optional[str] = Field(
        None, title="License", description="SPDX Identifier of the license associated with this workflow."
    )
    version: int = Field(
        ..., title="Version", description="The version of the workflow represented by an incremental number."
    )
    steps: Dict[int, Union[SubworkflowStepToExport, WorkflowToolStepToExport, WorkflowStepToExport]] = Field(
        {}, title="Steps", description="A dictionary with information about all the steps of the workflow."
    )


# Roles -----------------------------------------------------------------

RoleIdField = Annotated[EncodedDatabaseIdField, Field(title="ID", description="Encoded ID of the role")]
RoleNameField = Annotated[str, Field(title="Name", description="Name of the role")]
RoleDescriptionField = Annotated[str, Field(title="Description", description="Description of the role")]


class BasicRoleModel(Model):
    id: RoleIdField
    name: RoleNameField
    type: str = Field(title="Type", description="Type or category of the role")


class RoleModelResponse(BasicRoleModel, WithModelClass):
    description: Optional[RoleDescriptionField]
    url: RelativeUrlField
    model_class: Literal["Role"] = ModelClassField(Literal["Role"])


class RoleDefinitionModel(Model):
    name: RoleNameField
    description: RoleDescriptionField
    user_ids: Optional[List[DecodedDatabaseIdField]] = Field(title="User IDs", default=[])
    group_ids: Optional[List[DecodedDatabaseIdField]] = Field(title="Group IDs", default=[])


class RoleListResponse(RootModel):
    root: List[RoleModelResponse]


# The tuple should probably be another proper model instead?
# Keeping it as a Tuple for now for backward compatibility
# TODO: Use Tuple again when `make update-client-api-schema` supports them
RoleNameIdTuple = List[str]  # Tuple[str, DecodedDatabaseIdField]

# Group_Roles -----------------------------------------------------------------


class GroupRoleResponse(Model):
    id: RoleIdField
    name: RoleNameField
    url: RelativeUrlField


class GroupRoleListResponse(RootModel):
    root: List[GroupRoleResponse]


# Users -----------------------------------------------------------------------
# Group_Users -----------------------------------------------------------------


class GroupUserResponse(Model):
    id: EncodedDatabaseIdField
    email: str = UserEmailField
    url: RelativeUrlField


class GroupUserListResponse(RootModel):
    root: List[GroupUserResponse]


class ImportToolDataBundleUriSource(Model):
    src: Literal["uri"] = Field(title="src", description="Indicates that the tool data should be resolved by a URI.")
    uri: str = Field(
        title="uri",
        description="URI to fetch tool data bundle from (file:// URIs are fine because this is an admin-only operation)",
    )


class ImportToolDataBundleDatasetSource(Model):
    src: Literal["hda", "ldda"] = Field(
        title="src", description="Indicates that the tool data should be resolved from a dataset."
    )
    id: DecodedDatabaseIdField


ImportToolDataBundleSource = Union[ImportToolDataBundleDatasetSource, ImportToolDataBundleUriSource]


class ToolShedRepository(Model):
    tool_shed_url: str = Field(
        title="Tool Shed URL", default="https://toolshed.g2.bx.psu.edu/", description="Tool Shed target"
    )
    name: str = Field(title="Name", description="Name of repository")
    owner: str = Field(title="Owner", description="Owner of repository")


class ToolShedRepositoryChangeset(ToolShedRepository):
    changeset_revision: str


class InstalledRepositoryToolShedStatus(Model):
    # See https://github.com/galaxyproject/galaxy/issues/10453 , bad booleans
    # See https://github.com/galaxyproject/galaxy/issues/16135 , optional fields
    latest_installable_revision: Optional[str] = Field(
        title="Latest installed revision", description="Most recent version available on the tool shed"
    )
    revision_update: str
    revision_upgrade: Optional[str] = None
    repository_deprecated: Optional[str] = Field(
        title="Repository deprecated", description="Repository has been depreciated on the tool shed"
    )


class InstalledToolShedRepository(Model, WithModelClass):
    model_class: Literal["ToolShedRepository"] = ModelClassField(Literal["ToolShedRepository"])
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="Encoded ID of the install tool shed repository.",
    )
    status: str
    name: str = Field(title="Name", description="Name of repository")
    owner: str = Field(title="Owner", description="Owner of repository")
    deleted: bool
    # This should be an int... but it would break backward compatiblity. Probably switch it at some point anyway?
    ctx_rev: Optional[str] = Field(
        title="Changeset revision number",
        description="The linearized 0-based index of the changeset on the tool shed (0, 1, 2,...)",
    )
    error_message: str = Field("Installation error message, the empty string means no error was recorded")
    installed_changeset_revision: str = Field(
        title="Installed changeset revision",
        description="Initially installed changeset revision. Used to construct path to repository within Galaxies filesystem. Does not change if a repository is updated.",
    )
    tool_shed: str = Field(title="Tool shed", description="Hostname of the tool shed this was installed from")
    dist_to_shed: bool
    uninstalled: bool
    changeset_revision: str = Field(
        title="Changeset revision", description="Changeset revision of the repository - a mercurial commit hash"
    )
    tool_shed_status: Optional[InstalledRepositoryToolShedStatus] = Field(
        title="Latest updated status from the tool shed"
    )


class InstalledToolShedRepositories(RootModel):
    root: List[InstalledToolShedRepository]


CheckForUpdatesResponseStatusT = Literal["ok", "error"]


class CheckForUpdatesResponse(Model):
    status: CheckForUpdatesResponseStatusT = Field(title="Status", description="'ok' or 'error'")
    message: str = Field(
        title="Message", description="Unstructured description of tool shed updates discovered or failure"
    )


# Libraries -----------------------------------------------------------------


class LibraryPermissionScope(str, Enum):
    current = "current"
    available = "available"


class LibraryLegacySummary(Model, WithModelClass):
    model_class: Literal["Library"] = ModelClassField(Literal["Library"])
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="Encoded ID of the Library.",
    )
    name: str = Field(
        ...,
        title="Name",
        description="The name of the Library.",
    )
    description: Optional[str] = Field(
        "",
        title="Description",
        description="A detailed description of the Library.",
    )
    synopsis: Optional[str] = Field(
        None,
        title="Description",
        description="A short text describing the contents of the Library.",
    )
    root_folder_id: EncodedLibraryFolderDatabaseIdField = Field(
        ...,
        title="Root Folder ID",
        description="Encoded ID of the Library's base folder.",
    )
    create_time: datetime = Field(
        ...,
        title="Create Time",
        description="The time and date this item was created.",
    )
    deleted: bool = Field(
        ...,
        title="Deleted",
        description="Whether this Library has been deleted.",
    )


class LibrarySummary(LibraryLegacySummary):
    create_time_pretty: str = Field(  # This is somewhat redundant, maybe the client can do this with `create_time`?
        ...,
        title="Create Time Pretty",
        description="Nice time representation of the creation date.",
        examples=["2 months ago"],
    )
    public: bool = Field(
        ...,
        title="Public",
        description="Whether this Library has been deleted.",
    )
    can_user_add: bool = Field(
        ...,
        title="Can User Add",
        description="Whether the current user can add contents to this Library.",
    )
    can_user_modify: bool = Field(
        ...,
        title="Can User Modify",
        description="Whether the current user can modify this Library.",
    )
    can_user_manage: bool = Field(
        ...,
        title="Can User Manage",
        description="Whether the current user can manage the Library and its contents.",
    )


class LibrarySummaryList(RootModel):
    root: List[LibrarySummary] = Field(
        default=[],
        title="List with summary information of Libraries.",
    )


class CreateLibraryPayload(Model):
    name: str = Field(
        ...,
        title="Name",
        description="The name of the Library.",
    )
    description: Optional[str] = Field(
        "",
        title="Description",
        description="A detailed description of the Library.",
    )
    synopsis: Optional[str] = Field(
        "",
        title="Synopsis",
        description="A short text describing the contents of the Library.",
    )


class CreateLibrariesFromStore(StoreContentSource):
    pass


class UpdateLibraryPayload(Model):
    name: Optional[str] = Field(
        None,
        title="Name",
        description="The new name of the Library. Leave unset to keep the existing.",
    )
    description: Optional[str] = Field(
        None,
        title="Description",
        description="A detailed description of the Library. Leave unset to keep the existing.",
    )
    synopsis: Optional[str] = Field(
        None,
        title="Synopsis",
        description="A short text describing the contents of the Library. Leave unset to keep the existing.",
    )


class DeleteLibraryPayload(Model):
    undelete: bool = Field(
        ...,
        title="Undelete",
        description="Whether to restore this previously deleted library.",
    )


class LibraryCurrentPermissions(Model):
    access_library_role_list: List[RoleNameIdTuple] = Field(
        ...,
        title="Access Role List",
        description="A list containing pairs of role names and corresponding encoded IDs which have access to the Library.",
    )
    modify_library_role_list: List[RoleNameIdTuple] = Field(
        ...,
        title="Modify Role List",
        description="A list containing pairs of role names and corresponding encoded IDs which can modify the Library.",
    )
    manage_library_role_list: List[RoleNameIdTuple] = Field(
        ...,
        title="Manage Role List",
        description="A list containing pairs of role names and corresponding encoded IDs which can manage the Library.",
    )
    add_library_item_role_list: List[RoleNameIdTuple] = Field(
        ...,
        title="Add Role List",
        description="A list containing pairs of role names and corresponding encoded IDs which can add items to the Library.",
    )


RoleIdList = Union[
    List[DecodedDatabaseIdField], DecodedDatabaseIdField
]  # Should we support just List[DecodedDatabaseIdField] in the future?


class LegacyLibraryPermissionsPayload(RequireOneSetOption):
    LIBRARY_ACCESS_in: Optional[RoleIdList] = Field(
        [],
        title="Access IDs",
        description="A list of role encoded IDs defining roles that should have access permission on the library.",
    )
    LIBRARY_MODIFY_in: Optional[RoleIdList] = Field(
        [],
        title="Add IDs",
        description="A list of role encoded IDs defining roles that should be able to add items to the library.",
    )
    LIBRARY_ADD_in: Optional[RoleIdList] = Field(
        [],
        title="Manage IDs",
        description="A list of role encoded IDs defining roles that should have manage permission on the library.",
    )
    LIBRARY_MANAGE_in: Optional[RoleIdList] = Field(
        [],
        title="Modify IDs",
        description="A list of role encoded IDs defining roles that should have modify permission on the library.",
    )


class LibraryPermissionAction(str, Enum):
    set_permissions = "set_permissions"
    remove_restrictions = "remove_restrictions"  # name inconsistency? should be `make_public`?


class DatasetPermissionAction(str, Enum):
    set_permissions = "set_permissions"
    make_private = "make_private"
    remove_restrictions = "remove_restrictions"


class LibraryPermissionsPayloadBase(RequireOneSetOption):
    add_ids: Optional[RoleIdList] = Field(
        [],
        alias="add_ids[]",
        title="Add IDs",
        description="A list of role encoded IDs defining roles that should be able to add items to the library.",
    )
    manage_ids: Optional[RoleIdList] = Field(
        [],
        alias="manage_ids[]",
        title="Manage IDs",
        description="A list of role encoded IDs defining roles that should have manage permission on the library.",
    )
    modify_ids: Optional[RoleIdList] = Field(
        [],
        alias="modify_ids[]",
        title="Modify IDs",
        description="A list of role encoded IDs defining roles that should have modify permission on the library.",
    )


class LibraryPermissionsPayload(LibraryPermissionsPayloadBase):
    action: Optional[LibraryPermissionAction] = Field(
        None,
        title="Action",
        description="Indicates what action should be performed on the Library.",
    )
    access_ids: Optional[RoleIdList] = Field(
        [],
        alias="access_ids[]",  # Added for backward compatibility but it looks really ugly...
        title="Access IDs",
        description="A list of role encoded IDs defining roles that should have access permission on the library.",
    )


# Library Folders -----------------------------------------------------------------


class LibraryFolderPermissionAction(str, Enum):
    set_permissions = "set_permissions"


FolderNameField: str = Field(
    ...,
    title="Name",
    description="The name of the library folder.",
)
FolderDescriptionField: Optional[str] = Field(
    "",
    title="Description",
    description="A detailed description of the library folder.",
)


class LibraryFolderPermissionsPayload(LibraryPermissionsPayloadBase):
    action: Optional[LibraryFolderPermissionAction] = Field(
        None,
        title="Action",
        description="Indicates what action should be performed on the library folder.",
    )


class LibraryFolderDetails(Model, WithModelClass):
    model_class: Literal["LibraryFolder"] = ModelClassField(Literal["LibraryFolder"])
    id: EncodedLibraryFolderDatabaseIdField = Field(
        ...,
        title="ID",
        description="Encoded ID of the library folder.",
    )
    name: str = FolderNameField
    description: Optional[str] = FolderDescriptionField
    item_count: int = Field(
        ...,
        title="Item Count",
        description="A detailed description of the library folder.",
    )
    parent_library_id: EncodedDatabaseIdField = Field(
        ...,
        title="Parent Library ID",
        description="Encoded ID of the Library this folder belongs to.",
    )
    parent_id: Optional[EncodedLibraryFolderDatabaseIdField] = Field(
        None,
        title="Parent Folder ID",
        description="Encoded ID of the parent folder. Empty if it's the root folder.",
    )
    genome_build: Optional[str] = GenomeBuildField
    update_time: datetime = UpdateTimeField
    deleted: bool = Field(
        ...,
        title="Deleted",
        description="Whether this folder is marked as deleted.",
    )
    library_path: List[str] = Field(
        [],
        title="Path",
        description="The list of folder names composing the path to this folder.",
    )


class CreateLibraryFolderPayload(Model):
    name: str = FolderNameField
    description: Optional[str] = FolderDescriptionField


class UpdateLibraryFolderPayload(Model):
    name: Optional[str] = Field(
        default=None,
        title="Name",
        description="The new name of the library folder.",
    )
    description: Optional[str] = Field(
        default=None,
        title="Description",
        description="The new description of the library folder.",
    )


class LibraryAvailablePermissions(Model):
    roles: List[BasicRoleModel] = Field(
        ...,
        title="Roles",
        description="A list containing available roles that can be assigned to a particular permission.",
    )
    page: int = Field(
        ...,
        title="Page",
        description="Current page.",
    )
    page_limit: int = Field(
        ...,
        title="Page Limit",
        description="Maximum number of items per page.",
    )
    total: int = Field(
        ...,
        title="Total",
        description="Total number of items",
    )


class LibraryFolderCurrentPermissions(Model):
    modify_folder_role_list: List[RoleNameIdTuple] = Field(
        ...,
        title="Modify Role List",
        description="A list containing pairs of role names and corresponding encoded IDs which can modify the Library folder.",
    )
    manage_folder_role_list: List[RoleNameIdTuple] = Field(
        ...,
        title="Manage Role List",
        description="A list containing pairs of role names and corresponding encoded IDs which can manage the Library folder.",
    )
    add_library_item_role_list: List[RoleNameIdTuple] = Field(
        ...,
        title="Add Role List",
        description="A list containing pairs of role names and corresponding encoded IDs which can add items to the Library folder.",
    )


LibraryFolderContentsIndexSortByEnum = Literal["name", "description", "type", "size", "update_time"]


class LibraryFolderContentsIndexQueryPayload(Model):
    limit: int = 10
    offset: int = 0
    search_text: Optional[str] = None
    include_deleted: Optional[bool] = None
    order_by: LibraryFolderContentsIndexSortByEnum = "name"
    sort_desc: Optional[bool] = False


class LibraryFolderItemBase(Model):
    name: str
    type: str
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    can_manage: bool
    deleted: bool


class FolderLibraryFolderItem(LibraryFolderItemBase):
    id: EncodedLibraryFolderDatabaseIdField
    type: Literal["folder"]
    can_modify: bool
    description: Optional[str] = FolderDescriptionField


class FileLibraryFolderItem(LibraryFolderItemBase):
    id: EncodedDatabaseIdField
    type: Literal["file"]
    file_ext: str
    date_uploaded: datetime
    is_unrestricted: bool
    is_private: bool
    state: DatasetStateField
    file_size: str
    raw_size: int
    ldda_id: EncodedDatabaseIdField
    tags: TagCollection
    message: Optional[str] = None


AnyLibraryFolderItem = Annotated[Union[FileLibraryFolderItem, FolderLibraryFolderItem], Field(discriminator="type")]


class LibraryFolderMetadata(Model):
    parent_library_id: EncodedDatabaseIdField
    folder_name: str
    folder_description: str
    total_rows: int
    can_modify_folder: bool
    can_add_library_item: bool
    full_path: List[Tuple[EncodedLibraryFolderDatabaseIdField, str]]


class LibraryFolderContentsIndexResult(Model):
    metadata: LibraryFolderMetadata
    folder_contents: List[AnyLibraryFolderItem]


class CreateLibraryFilePayload(Model):
    from_hda_id: Optional[DecodedDatabaseIdField] = Field(
        default=None,
        title="From HDA ID",
        description="The ID of an accessible HDA to copy into the library.",
    )
    from_hdca_id: Optional[DecodedDatabaseIdField] = Field(
        default=None,
        title="From HDCA ID",
        description=(
            "The ID of an accessible HDCA to copy into the library. "
            "Nested collections are not allowed, you must flatten the collection first."
        ),
    )
    ldda_message: Optional[str] = Field(
        default="",
        title="LDDA Message",
        description="The new message attribute of the LDDA created.",
    )


class DatasetAssociationRoles(Model):
    access_dataset_roles: List[RoleNameIdTuple] = Field(
        default=[],
        title="Access Roles",
        description=(
            "A list of roles that can access the dataset. "
            "The user has to **have all these roles** in order to access this dataset. "
            "Users without access permission **cannot** have other permissions on this dataset. "
            "If there are no access roles set on the dataset it is considered **unrestricted**."
        ),
    )
    manage_dataset_roles: List[RoleNameIdTuple] = Field(
        default=[],
        title="Manage Roles",
        description=(
            "A list of roles that can manage permissions on the dataset. "
            "Users with **any** of these roles can manage permissions of this dataset. "
            "If you remove yourself you will lose the ability to manage this dataset unless you are an admin."
        ),
    )
    modify_item_roles: List[RoleNameIdTuple] = Field(
        default=[],
        title="Modify Roles",
        description=(
            "A list of roles that can modify the library item. This is a library related permission. "
            "User with **any** of these roles can modify name, metadata, and other information about this library item."
        ),
    )


class UpdateDatasetPermissionsPayloadBase(Model):
    action: Optional[DatasetPermissionAction] = Field(
        DatasetPermissionAction.set_permissions,
        title="Action",
        description="Indicates what action should be performed on the dataset.",
    )


AccessIdsField = Annotated[
    Optional[RoleIdList],
    Field(
        default=None,
        title="Access IDs",
        description="A list of role encoded IDs defining roles that should have access permission on the dataset.",
    ),
]

ManageIdsField = Annotated[
    Optional[RoleIdList],
    Field(
        default=None,
        title="Manage IDs",
        description="A list of role encoded IDs defining roles that should have manage permission on the dataset.",
    ),
]

ModifyIdsField = Annotated[
    Optional[RoleIdList],
    Field(
        default=None,
        title="Modify IDs",
        description="A list of role encoded IDs defining roles that should have modify permission on the dataset.",
    ),
]


class UpdateDatasetPermissionsPayload(UpdateDatasetPermissionsPayloadBase):
    access_ids: Annotated[Optional[RoleIdList], Field(default=None, alias="access_ids[]")] = None
    manage_ids: Annotated[Optional[RoleIdList], Field(default=None, alias="manage_ids[]")] = None
    modify_ids: Annotated[Optional[RoleIdList], Field(default=None, alias="modify_ids[]")] = None


class UpdateDatasetPermissionsPayloadAliasB(UpdateDatasetPermissionsPayloadBase):
    access: AccessIdsField = None
    manage: ManageIdsField = None
    modify: ModifyIdsField = None


class UpdateDatasetPermissionsPayloadAliasC(UpdateDatasetPermissionsPayloadBase):
    access_ids: AccessIdsField = None
    manage_ids: ManageIdsField = None
    modify_ids: ModifyIdsField = None


UpdateDatasetPermissionsPayloadAliases = Union[
    UpdateDatasetPermissionsPayload,
    UpdateDatasetPermissionsPayloadAliasB,
    UpdateDatasetPermissionsPayloadAliasC,
]


@partial_model()
class HDACustom(HDADetailed):
    """Can contain any serializable property of an HDA.

    Allows arbitrary custom keys to be specified in the serialization
    parameters without a particular view (predefined set of keys).
    """

    # TODO: Fix this workaround for partial_model not supporting UUID fields for some reason.
    # The error otherwise is: `PydanticUserError: 'UuidVersion' cannot annotate 'nullable'.`
    # Also ignoring mypy complaints about the type redefinition.
    uuid: Optional[UUID4]  # type: ignore[assignment]

    # Add fields that are not part of any view here
    visualizations: Annotated[
        Optional[List[Visualization]],
        Field(
            None,
            title="Visualizations",
            description="The collection of visualizations that can be applied to this dataset.",
        ),
    ]

    # We need to allow extra fields so we can have the metadata_* fields serialized.
    # TODO: try to find a better way to handle this.
    model_config = ConfigDict(extra="allow")


@partial_model()
class HDCACustom(HDCADetailed):
    """Can contain any serializable property of an HDCA.

    Allows arbitrary custom keys to be specified in the serialization
    parameters without a particular view (predefined set of keys).
    """


AnyHDA = Union[HDACustom, HDADetailed, HDASummary, HDAInaccessible]
AnyHDCA = Union[HDCACustom, HDCADetailed, HDCASummary]
AnyHistoryContentItem = Annotated[
    Union[
        AnyHDA,
        AnyHDCA,
    ],
    Field(union_mode="left_to_right"),
]


AnyJobStateSummary = Annotated[
    Union[
        JobStateSummary,
        ImplicitCollectionJobsStateSummary,
        WorkflowInvocationStateSummary,
    ],
    Field(..., discriminator="model"),
]


HistoryArchiveExportResult = Union[JobExportHistoryArchiveModel, JobIdResponse]


class DeleteHistoryContentPayload(Model):
    purge: bool = Field(
        default=False,
        title="Purge",
        description="Whether to remove the dataset from storage. Datasets will only be removed from storage once all HDAs or LDDAs that refer to this datasets are deleted.",
    )
    recursive: bool = Field(
        default=False,
        title="Recursive",
        description="When deleting a dataset collection, whether to also delete containing datasets.",
    )
    stop_job: bool = Field(
        default=False,
        title="Stop Job",
        description="Whether to stop the creating job if all the job's outputs are deleted.",
    )


class DeleteHistoryContentResult(Model):
    """Contains minimum information about the deletion state of a history item.

    Can also contain any other properties of the item."""

    id: DecodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="The encoded ID of the history item.",
    )
    deleted: bool = Field(
        ...,
        title="Deleted",
        description="True if the item was successfully deleted.",
    )
    purged: Optional[bool] = Field(
        default=None,
        title="Purged",
        description="True if the item was successfully removed from disk.",
    )


class HistoryContentsArchiveDryRunResult(RootModel):
    """
    Contains a collection of filepath/filename entries that represent
    the contents that would have been included in the archive.
    This is returned when the `dry_run` flag is active when
    creating an archive with the contents of the history.

    This is used for debugging purposes.
    """

    root: List[Tuple[str, str]]


class HistoryContentStats(Model):
    total_matches: int = Field(
        ...,
        title="Total Matches",
        description=("The total number of items that match the search query without any pagination"),
    )


class HistoryContentsResult(RootModel):
    """List of history content items.
    Can contain different views and kinds of items.
    """

    root: List[AnyHistoryContentItem]


class HistoryContentsWithStatsResult(Model):
    """Includes stats with items counting"""

    stats: HistoryContentStats = Field(
        ...,
        title="Stats",
        description=("Contains counting stats for the query."),
    )
    contents: List[AnyHistoryContentItem] = Field(
        ...,
        title="Contents",
        description=(
            "The items matching the search query. Only the items fitting in the current page limit will be returned."
        ),
    )

    # This field is ignored and contains the content type associated with this model
    __accept_type__ = "application/vnd.galaxy.history.contents.stats+json"


# Sharing -----------------------------------------------------------------
class SharingOptions(str, Enum):
    """Options for sharing resources that may have restricted access to all or part of their contents."""

    make_public = "make_public"
    make_accessible_to_shared = "make_accessible_to_shared"
    no_changes = "no_changes"


class ShareWithExtra(Model):
    can_share: bool = Field(
        False,
        title="Can Share",
        description="Indicates whether the resource can be directly shared or requires further actions.",
    )


UserIdentifier = Union[DecodedDatabaseIdField, str]


class ShareWithPayload(Model):
    user_ids: List[UserIdentifier] = Field(
        ...,
        title="User Identifiers",
        description=(
            "A collection of encoded IDs (or email addresses) of users that this resource will be shared with."
        ),
    )
    share_option: Optional[SharingOptions] = Field(
        None,
        title="Share Option",
        description=(
            "User choice for sharing resources which its contents may be restricted:\n"
            " - None: The user did not choose anything yet or no option is needed.\n"
            f" - {SharingOptions.make_public.value}: The contents of the resource will be made publicly accessible.\n"
            f" - {SharingOptions.make_accessible_to_shared.value}: This will automatically create a new `sharing role` allowing protected contents to be accessed only by the desired users.\n"
            f" - {SharingOptions.no_changes.value}: This won't change the current permissions for the contents. The user which this resource will be shared may not be able to access all its contents.\n"
        ),
    )


class SetSlugPayload(Model):
    new_slug: str = Field(
        ...,
        title="New Slug",
        description="The slug that will be used to access this shared item.",
    )


class UserEmail(Model):
    id: EncodedDatabaseIdField = Field(
        ...,
        title="User ID",
        description="The encoded ID of the user.",
    )
    email: str = Field(
        ...,
        title="Email",
        description="The email of the user.",
    )


class UserBeaconSetting(Model):
    enabled: bool = Field(
        ...,
        title="Enabled",
        description="True if beacon sharing is enabled",
    )


class SharingStatus(Model):
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="The encoded ID of the resource to be shared.",
    )
    title: str = Field(
        ...,
        title="Title",
        description="The title or name of the resource.",
    )
    importable: bool = Field(
        ...,
        title="Importable",
        description="Whether this resource can be published using a link.",
    )
    published: bool = Field(
        ...,
        title="Published",
        description="Whether this resource is currently published.",
    )
    users_shared_with: List[UserEmail] = Field(
        [],
        title="Users shared with",
        description="The list of encoded ids for users the resource has been shared.",
    )
    email_hash: Optional[str] = Field(
        None,
        title="Encoded Email",
        description="Encoded owner email.",
    )
    username: Optional[str] = Field(
        None,
        title="Username",
        description="The owner's username.",
    )
    username_and_slug: Optional[str] = Field(
        None,
        title="Username and slug",
        description="The relative URL in the form of /u/{username}/{resource_single_char}/{slug}",
    )


class HDABasicInfo(Model):
    id: EncodedDatabaseIdField
    name: str


class ShareHistoryExtra(ShareWithExtra):
    can_change: List[HDABasicInfo] = Field(
        [],
        title="Can Change",
        description=(
            "A collection of datasets that are not accessible by one or more of the target users "
            "and that can be made accessible for others by the user sharing the history."
        ),
    )
    cannot_change: List[HDABasicInfo] = Field(
        [],
        title="Cannot Change",
        description=(
            "A collection of datasets that are not accessible by one or more of the target users "
            "and that cannot be made accessible for others by the user sharing the history."
        ),
    )
    accessible_count: int = Field(
        0,
        title="Accessible Count",
        description=("The number of datasets in the history that are public or accessible by all the target users."),
    )


class ShareWithStatus(SharingStatus):
    errors: List[str] = Field(
        [],
        title="Errors",
        description="Collection of messages indicating that the resource was not shared with some (or all users) due to an error.",
    )
    extra: Optional[ShareWithExtra] = Field(
        None,
        title="Extra",
        description=(
            "Optional extra information about this shareable resource that may be of interest. "
            "The contents of this field depend on the particular resource."
        ),
    )


class ShareHistoryWithStatus(ShareWithStatus):
    extra: ShareHistoryExtra = Field(
        ...,
        title="Extra",
        description=(
            "Optional extra information about this shareable resource that may be of interest. "
            "The contents of this field depend on the particular resource."
        ),
    )


# Pages -------------------------------------------------------


class PageContentFormat(str, Enum):
    markdown = "markdown"
    html = "html"


ContentFormatField: PageContentFormat = Field(
    default=PageContentFormat.html,
    title="Content format",
    description="Either `markdown` or `html`.",
)

ContentField: Optional[str] = Field(
    default="",
    title="Content",
    description="Raw text contents of the last page revision (type dependent on content_format).",
)


class PageSummaryBase(Model):
    title: str = Field(
        ...,  # Required
        title="Title",
        description="The name of the page.",
    )
    slug: str = Field(
        ...,  # Required
        title="Identifier",
        description="The title slug for the page URL, must be unique.",
        pattern=r"^[^/:?#]+$",
    )


class MaterializeDatasetInstanceAPIRequest(Model):
    source: DatasetSourceType = Field(
        title="Source",
        description="The source of the content. Can be other history element to be copied or library elements.",
    )
    content: DecodedDatabaseIdField = Field(
        title="Content",
        description=(
            "Depending on the `source` it can be:\n"
            "- The encoded id of the source library dataset\n"
            "- The encoded id of the HDA\n"
        ),
    )


class MaterializeDatasetInstanceRequest(MaterializeDatasetInstanceAPIRequest):
    history_id: DecodedDatabaseIdField


class ChatPayload(Model):
    query: str = Field(
        ...,
        title="Query",
        description="The query to be sent to the chatbot.",
    )
    context: Optional[str] = Field(
        default="",
        title="Context",
        description="The context for the chatbot.",
    )


class CreatePagePayload(PageSummaryBase):
    content_format: PageContentFormat = ContentFormatField
    content: Optional[str] = ContentField
    annotation: Optional[str] = Field(
        default=None,
        title="Annotation",
        description="Annotation that will be attached to the page.",
    )
    invocation_id: Optional[DecodedDatabaseIdField] = Field(
        None,
        title="Workflow invocation ID",
        description="Encoded ID used by workflow generated reports.",
    )
    model_config = ConfigDict(use_enum_values=True, extra="allow")


class AsyncTaskResultSummary(Model):
    id: str = Field(
        ...,
        title="ID",
        description="Celery AsyncResult ID for this task",
    )
    ignored: bool = Field(
        ...,
        title="Ignored",
        description="Indicated whether the Celery AsyncResult will be available for retrieval",
    )
    name: Optional[str] = Field(
        None,
        title="Name of task being done derived from Celery AsyncResult",
    )
    queue: Optional[str] = Field(
        None,
        title="Queue of task being done derived from Celery AsyncResult",
    )


ToolRequestIdField = Field(title="ID", description="Encoded ID of the role")


class ToolRequestState(str, Enum):
    NEW = "new"
    SUBMITTED = "submitted"
    FAILED = "failed"


class ToolRequestModel(Model):
    id: EncodedDatabaseIdField = ToolRequestIdField
    request: Dict[str, Any]
    state: ToolRequestState
    state_message: Optional[str]


class AsyncFile(Model):
    storage_request_id: UUID
    task: AsyncTaskResultSummary


class PageSummary(PageSummaryBase, WithModelClass):
    id: EncodedDatabaseIdField = Field(
        ...,  # Required
        title="ID",
        description="Encoded ID of the Page.",
    )
    model_class: PAGE_MODEL_CLASS = ModelClassField(PAGE_MODEL_CLASS)
    username: str = Field(
        ...,  # Required
        title="Username",
        description="The name of the user owning this Page.",
    )
    email_hash: str = Field(
        ...,  # Required
        title="Encoded email",
        description="The encoded email of the user.",
    )
    author_deleted: bool = Field(
        ...,  # Required
        title="Author deleted",
        description="Whether the author of this Page has been deleted.",
    )
    published: bool = Field(
        ...,  # Required
        title="Published",
        description="Whether this Page has been published.",
    )
    importable: bool = Field(
        ...,  # Required
        title="Importable",
        description="Whether this Page can be imported.",
    )
    deleted: bool = Field(
        ...,  # Required
        title="Deleted",
        description="Whether this Page has been deleted.",
    )
    latest_revision_id: EncodedDatabaseIdField = Field(
        ...,  # Required
        title="Latest revision ID",
        description="The encoded ID of the last revision of this Page.",
    )
    revision_ids: List[EncodedDatabaseIdField] = Field(
        ...,  # Required
        title="List of revisions",
        description="The history with the encoded ID of each revision of the Page.",
    )
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    tags: TagCollection


GenerateVersionField = Field(
    None,
    title="Galaxy Version",
    description="The version of Galaxy this object was generated with.",
)
GenerateTimeField = Field(
    None,
    title="Galaxy Version",
    description="The version of Galaxy this object was generated with.",
)


class OAuth2State(BaseModel):
    route: str
    nonce: str

    def encode(self) -> str:
        return base64.b64encode(self.model_dump_json().encode("utf-8")).decode("utf-8")

    @staticmethod
    def decode(base64_param: str) -> "OAuth2State":
        return OAuth2State.model_validate_json(base64.b64decode(base64_param.encode("utf-8")))


class PageDetails(PageSummary):
    content_format: PageContentFormat = ContentFormatField
    content: Optional[str] = ContentField
    generate_version: Optional[str] = GenerateVersionField
    generate_time: Optional[str] = GenerateTimeField
    model_config = ConfigDict(extra="allow")


class PageSummaryList(RootModel):
    root: List[PageSummary] = Field(
        default=[],
        title="List with summary information of Pages.",
    )


class LandingRequestState(str, Enum):
    UNCLAIMED = "unclaimed"
    CLAIMED = "claimed"


ToolLandingRequestIdField = Field(title="ID", description="Encoded ID of the tool landing request")
WorkflowLandingRequestIdField = Field(title="ID", description="Encoded ID of the workflow landing request")


class CreateToolLandingRequestPayload(Model):
    tool_id: str
    tool_version: Optional[str] = None
    request_state: Optional[Dict[str, Any]] = None
    client_secret: Optional[str] = None
    public: bool = False


class CreateWorkflowLandingRequestPayload(Model):
    workflow_id: str
    workflow_target_type: Literal["stored_workflow", "workflow", "trs_url"]
    request_state: Optional[Dict[str, Any]] = None
    client_secret: Optional[str] = None
    public: bool = Field(
        False,
        description="If workflow landing request is public anyone with the uuid can use the landing request. If not public the request must be claimed before use and additional verification might occur.",
    )


class ClaimLandingPayload(Model):
    client_secret: Optional[str] = None


class ToolLandingRequest(Model):
    uuid: UuidField
    tool_id: str
    tool_version: Optional[str] = None
    request_state: Optional[Dict[str, Any]] = None
    state: LandingRequestState


class WorkflowLandingRequest(Model):
    uuid: UuidField
    workflow_id: str
    workflow_target_type: Literal["stored_workflow", "workflow", "trs_url"]
    request_state: Dict[str, Any]
    state: LandingRequestState


class MessageExceptionModel(BaseModel):
    err_msg: str
    err_code: int


class SanitizedString(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if isinstance(value, str):
            return cls(sanitize_html(value))
        raise TypeError("string required")

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )
