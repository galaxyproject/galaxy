"""This module contains general pydantic models and common schema field annotations for them."""

import re
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
    Union,
)
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    AnyUrl,
    BaseModel,
    ConstrainedStr,
    Extra,
    Field,
    Json,
    UUID4,
)
from typing_extensions import (
    Annotated,
    Literal,
)

from galaxy.model import (
    Dataset,
    DatasetCollection,
    DatasetInstance,
    Job,
)
from galaxy.schema.bco import XrefItem
from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
    LibraryFolderDatabaseIdField,
    ModelClassField,
)
from galaxy.schema.types import (
    OffsetNaiveDatetime,
    RelativeUrl,
)

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

OptionalNumberT = Optional[Union[int, float]]

# Generic and common Field annotations that can be reused across models

RelativeUrlField: RelativeUrl = Field(
    ...,
    title="URL",
    description="The relative URL to access this item.",
    deprecated=True,
)

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

EntityIdField = Field(
    ...,
    title="ID",
    description="The encoded ID of this entity.",
)

DatasetStateField: Dataset.states = Field(
    ...,
    title="State",
    description="The current state of this dataset.",
)

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
    default=None,
    title="Collection Type",
    description=(
        "The type of the collection, can be `list`, `paired`, or define subcollections using `:` "
        "as separator like `list:paired` or `list:list`."
    ),
)

PopulatedStateField: DatasetCollection.populated_states = Field(
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

ElementCountField: Optional[int] = Field(
    None,
    title="Element Count",
    description=(
        "The number of elements contained in the dataset collection. "
        "It may be None or undefined if the collection could not be populated."
    ),
)

PopulatedField: bool = Field(
    title="Populated",
    description="Whether the dataset collection elements (and any subcollections elements) were successfully populated.",
)

ElementsField = Field(
    [],
    title="Elements",
    description="The summary information of each of the elements inside the dataset collection.",
)

HistoryIdField: DecodedDatabaseIdField = Field(
    ...,
    title="History ID",
    description="The encoded ID of the history associated with this item.",
)

UuidField: UUID4 = Field(
    ...,
    title="UUID",
    description="Universal unique identifier for this dataset.",
)

GenomeBuildField: Optional[str] = Field(
    "?",
    title="Genome Build",
    description="TODO",
)

ContentsUrlField = Field(
    title="Contents URL",
    description="The relative URL to access the contents of this History.",
)


class Model(BaseModel):
    """Base model definition with common configuration used by all derived models."""

    class Config:
        use_enum_values = True  # when using .dict()
        allow_population_by_field_name = True
        json_encoders = {
            # This will ensure all IDs are encoded when serialized to JSON
            DecodedDatabaseIdField: lambda v: DecodedDatabaseIdField.encode(v),
            LibraryFolderDatabaseIdField: lambda v: LibraryFolderDatabaseIdField.encode(v),
        }

        @staticmethod
        def schema_extra(schema: Dict[str, Any], model) -> None:
            # pydantic doesn't currently allow creating a constant that isn't optional,
            # which makes sense for validation, but an openapi schema that describes
            # a response should be able to declare that a field is always present,
            # even if it is generated from a default value.
            # Pass `mark_required_in_schema=True` when constructing a pydantic Field instance
            # to indicate that the field is always present.
            remove_prop_keys = set()  # hidden items shouldn't be added to schema
            properties = schema.get("properties", {})
            for prop_key, prop in properties.items():
                required_in_schema = prop.pop("mark_required_in_schema", None)
                hidden = prop.get("hidden")
                if hidden:
                    remove_prop_keys.add(prop_key)
                if required_in_schema:
                    # const is not valid in response?
                    prop.pop("const", None)
                    if "required" in schema:
                        schema["required"].append(prop_key)
                    else:
                        schema["required"] = [prop_key]
            for prop_key_to_remove in remove_prop_keys:
                del properties[prop_key_to_remove]


class UserModel(Model):
    """User in a transaction context."""

    id: DecodedDatabaseIdField = Field(title="ID", description="User ID")
    username: str = Field(title="Username", description="User username")
    email: str = Field(title="Email", description="User email")
    active: bool = Field(title="Active", description="User is active")
    deleted: bool = Field(title="Deleted", description="User is deleted")
    last_password_change: Optional[datetime] = Field(title="Last password change", description="")
    model_class: USER_MODEL_CLASS = ModelClassField(USER_MODEL_CLASS)


class GroupModel(Model):
    """User group model"""

    model_class: GROUP_MODEL_CLASS = ModelClassField(GROUP_MODEL_CLASS)
    id: DecodedDatabaseIdField = Field(
        ...,  # Required
        title="ID",
        description="Encoded group ID",
    )
    name: str = Field(
        ...,  # Required
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


class TagItem(ConstrainedStr):
    regex = re.compile(r"^([^\s.:])+(.[^\s.:]+)*(:[^\s.:]+)?$")


class TagCollection(Model):
    """Represents the collection of tags associated with an item."""

    __root__: List[TagItem] = Field(
        default=...,
        title="Tags",
        description="The collection of tags associated with an item.",
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
        ..., title="Target", description="Specifies where to open the linked document.", example="_blank"
    )
    href: AnyUrl = Field(
        ...,
        title="HRef",
        description="Specifies the linked document, resource, or location.",
    )
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
    class Config:
        extra = Extra.allow  # Allow any fields temporarily until the model is annotated


class HistoryItemBase(Model):
    """Basic information provided by items contained in a History."""

    id: DecodedDatabaseIdField = EntityIdField
    name: Optional[str] = Field(
        title="Name",
        description="The name of the item.",
    )
    history_id: DecodedDatabaseIdField = HistoryIdField
    hid: int = Field(
        ...,
        title="HID",
        description="The index position of this item in the History.",
    )
    history_content_type: HistoryContentType = Field(
        ...,
        title="Content Type",
        description="The type of this item.",
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

    class Config:
        extra = Extra.allow

    type_id: Optional[str] = Field(
        default=None,
        title="Type - ID",
        description="The type and the encoded ID of this item. Used for caching.",
        example="dataset-616e371b2cc6c62e",
    )
    type: str = Field(
        ...,
        title="Type",
        description="The type of this item.",
    )
    create_time: Optional[datetime] = CreateTimeField
    update_time: Optional[datetime] = UpdateTimeField
    url: RelativeUrl = RelativeUrlField
    tags: TagCollection


class HDASummary(HistoryItemCommon):
    """History Dataset Association summary information."""

    dataset_id: DecodedDatabaseIdField = Field(
        ...,
        title="Dataset ID",
        description="The encoded ID of the dataset associated with this item.",
    )
    state: Dataset.states = DatasetStateField
    extension: str = Field(
        ...,
        title="Extension",
        description="The extension of the dataset.",
        example="txt",
    )
    purged: bool = Field(
        ...,
        title="Purged",
        description="Whether this dataset has been removed from disk.",
    )


class HDAInaccessible(HistoryItemBase):
    """History Dataset Association information when the user can not access it."""

    accessible: bool = AccessibleField
    state: Dataset.states = DatasetStateField


HdaLddaField = Field(
    DatasetSourceType.hda,
    const=True,
    title="HDA or LDDA",
    description="Whether this dataset belongs to a history (HDA) or a library (LDDA).",
    deprecated=False,  # TODO Should this field be deprecated in favor of model_class?
)


class HDADetailed(HDASummary):
    """History Dataset Association detailed information."""

    model_class: Annotated[HDA_MODEL_CLASS, ModelClassField()]
    hda_ldda: DatasetSourceType = HdaLddaField
    accessible: bool = AccessibleField
    genome_build: Optional[str] = GenomeBuildField
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
    metadata_dbkey: Optional[str] = Field(
        "?",
        title="Metadata DBKey",
        description="TODO",
    )
    metadata_data_lines: int = Field(
        0,
        title="Metadata Data Lines",
        description="TODO",
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
        example="galaxy.datatypes.data.Text",
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
    uuid: UUID4 = UuidField
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
        deprecated=False,  # TODO: Should this field be deprecated in favor of display_apps?
    )
    visualizations: List[Visualization] = Field(
        ...,
        title="Visualizations",
        description="The collection of visualizations that can be applied to this dataset.",
    )
    validated_state: DatasetInstance.validated_states = Field(
        ...,
        title="Validated State",
        description="The state of the datatype validation for this dataset.",
    )
    validated_state_message: Optional[str] = Field(
        ...,
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
            deprecated=False,  # TODO: Should this field be deprecated as announced in release 16.04?
        ),
    ] = "file"
    created_from_basename: Optional[str] = Field(
        None,
        title="Created from basename",
        description="The basename of the output that produced this dataset.",  # TODO: is that correct?
    )


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


class DCSummary(Model):
    """Dataset Collection summary information."""

    model_class: DC_MODEL_CLASS = ModelClassField(DC_MODEL_CLASS)
    id: DecodedDatabaseIdField = EntityIdField
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    collection_type: CollectionType = CollectionTypeField
    populated_state: DatasetCollection.populated_states = PopulatedStateField
    populated_state_message: Optional[str] = PopulatedStateMessageField
    element_count: Optional[int] = ElementCountField


class HDAObject(Model):
    """History Dataset Association Object"""

    id: DecodedDatabaseIdField = EntityIdField
    model_class: HDA_MODEL_CLASS = ModelClassField(HDA_MODEL_CLASS)
    state: Dataset.states = DatasetStateField
    hda_ldda: DatasetSourceType = HdaLddaField
    history_id: DecodedDatabaseIdField = HistoryIdField

    class Config:
        extra = Extra.allow  # Can contain more fields like metadata_*


class DCObject(Model):
    """Dataset Collection Object"""

    id: DecodedDatabaseIdField = EntityIdField
    model_class: DC_MODEL_CLASS = ModelClassField(DC_MODEL_CLASS)
    collection_type: CollectionType = CollectionTypeField
    populated: Optional[bool] = PopulatedField
    element_count: Optional[int] = ElementCountField
    contents_url: Optional[RelativeUrl] = ContentsUrlField
    elements: List["DCESummary"] = ElementsField


class DCESummary(Model):
    """Dataset Collection Element summary information."""

    id: DecodedDatabaseIdField = EntityIdField
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
    element_type: DCEType = Field(
        ...,
        title="Element Type",
        description="The type of the element. Used to interpret the `object` field.",
    )
    object: Union[HDAObject, HDADetailed, DCObject] = Field(
        ...,
        title="Object",
        description="The element's specific data depending on the value of `element_type`.",
    )


DCObject.update_forward_refs()


class DCDetailed(DCSummary):
    """Dataset Collection detailed information."""

    populated: bool = PopulatedField
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


class HDCASummary(HistoryItemCommon):
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
    populated_state: DatasetCollection.populated_states = PopulatedStateField
    populated_state_message: Optional[str] = PopulatedStateMessageField
    element_count: Optional[int] = ElementCountField
    job_source_id: Optional[DecodedDatabaseIdField] = Field(
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
    contents_url: RelativeUrl = ContentsUrlField
    collection_id: DecodedDatabaseIdField = Field(
        ...,
        title="Collection ID",
        description="The encoded ID of the dataset collection associated with this HDCA.",
    )


class HDCADetailed(HDCASummary):
    """History Dataset Collection Association detailed information."""

    populated: bool = PopulatedField
    elements: List[DCESummary] = ElementsField
    elements_datatypes: Set[str] = Field(
        ..., description="A set containing all the different element datatypes in the collection."
    )


class HistoryBase(Model):
    """Provides basic configuration for all the History models."""

    class Config:
        extra = Extra.allow  # Allow any other extra fields


class HistoryContentItem(Model):
    """Identifies a dataset or collection contained in a History."""

    history_content_type: HistoryContentType = Field(
        ...,
        title="Content Type",
        description="The type of this item.",
    )
    id: DecodedDatabaseIdField = EntityIdField


class UpdateContentItem(HistoryContentItem):
    """Used for updating a particular history item. All fields are optional."""

    class Config:
        use_enum_values = True  # When using .dict()
        extra = Extra.allow  # Allow any other extra fields


class UpdateHistoryContentsBatchPayload(HistoryBase):
    """Contains property values that will be updated for all the history `items` provided."""

    items: List[UpdateContentItem] = Field(
        ...,
        title="Items",
        description="A list of content items to update with the changes.",
    )

    class Config:
        schema_extra = {
            "example": {
                "items": [{"history_content_type": "dataset", "id": "string"}],
                "visible": False,
            }
        }


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
    items: Optional[List[HistoryContentItem]]
    params: Optional[AnyBulkOperationParams]


class BulkOperationItemError(Model):
    item: HistoryContentItem
    error: str


class HistoryContentBulkOperationResult(Model):
    success_count: int
    errors: List[BulkOperationItemError]


class UpdateHistoryContentsPayload(HistoryBase):
    """Contains arbitrary property values that will be updated for a particular history item."""

    class Config:
        schema_extra = {
            "example": {
                "visible": False,
                "annotation": "Test",
            }
        }


class HistorySummary(HistoryBase):
    """History summary information."""

    model_class: HISTORY_MODEL_CLASS = ModelClassField(HISTORY_MODEL_CLASS)
    id: DecodedDatabaseIdField = EntityIdField
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
    url: RelativeUrl = RelativeUrlField
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


HistoryStateCounts = Dict[Dataset.states, int]
HistoryStateIds = Dict[Dataset.states, List[DecodedDatabaseIdField]]


class HistoryDetailed(HistorySummary):  # Equivalent to 'dev-detailed' view, which seems the default
    """History detailed information."""

    contents_url: RelativeUrl = ContentsUrlField
    size: int = Field(
        ...,
        title="Size",
        description="The total size of the contents of this history in bytes.",
    )
    user_id: DecodedDatabaseIdField = Field(
        ...,
        title="User ID",
        description="The encoded ID of the user that owns this History.",
    )
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
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
    username_and_slug: Optional[str] = Field(
        None,
        title="Username and slug",
        description="The relative URL in the form of /u/{username}/h/{slug}",
    )
    genome_build: Optional[str] = GenomeBuildField
    state: Dataset.states = Field(
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


AnyHistoryView = Union[
    HistorySummary,
    HistoryDetailed,
    # Any will cover those cases in which only specific `keys` are requested
    # otherwise the validation will fail because the required fields are not returned
    Any,
]


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
        hidden=True,  # Avoids displaying this field in the documentation
    )


WorkflowSortByEnum = Literal["create_time", "update_time", "name"]


class WorkflowIndexQueryPayload(Model):
    show_deleted: bool = False
    show_hidden: bool = False
    show_published: Optional[bool] = None
    show_shared: Optional[bool] = None
    sort_by: Optional[WorkflowSortByEnum] = Field(title="Sort By", description="Sort workflows by this attribute")
    sort_desc: Optional[bool] = Field(
        title="Sort descending", description="Explicitly sort by descending if sort_by is specified."
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
    order_by: JobIndexSortByEnum = JobIndexSortByEnum.update_time
    search: Optional[str] = None
    limit: int = 500
    offset: int = 0


class InvocationSortByEnum(str, Enum):
    create_time = "create_time"
    update_time = "update_time"
    none = None


class InvocationIndexQueryPayload(Model):
    workflow_id: Optional[DecodedDatabaseIdField] = Field(
        title="Workflow ID", description="Return only invocations for this Workflow ID"
    )
    history_id: Optional[DecodedDatabaseIdField] = Field(
        title="History ID", description="Return only invocations for this History ID"
    )
    job_id: Optional[DecodedDatabaseIdField] = Field(
        title="Job ID", description="Return only invocations for this Job ID"
    )
    user_id: Optional[DecodedDatabaseIdField] = Field(
        title="User ID", description="Return invocations for this User ID"
    )
    sort_by: Optional[InvocationSortByEnum] = Field(
        title="Sort By", description="Sort Workflow Invocations by this attribute"
    )
    sort_desc: bool = Field(default=False, descritpion="Sort in descending order?")
    include_terminal: bool = Field(default=True, description="Set to false to only include terminal Invocations.")
    limit: Optional[int] = Field(
        default=100,
        lt=1000,
    )
    offset: Optional[int] = Field(default=0, description="Number of invocations to skip")


class PageSortByEnum(str, Enum):
    create_time = "create_time"
    update_time = "update_time"


class PageIndexQueryPayload(Model):
    deleted: bool = False
    user_id: Optional[DecodedDatabaseIdField] = None
    sort_by: PageSortByEnum = PageSortByEnum.update_time
    sort_desc: bool = Field(default=True, descritpion="Sort in descending order?")
    show_published: bool = True
    show_shared: bool = False
    limit: int = 500
    offset: int = 0


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
            "The encoded ID of the history to copy. " "Provide this value only if you want to copy an existing history."
        ),
    )
    all_datasets: Optional[bool] = Field(
        default=True,
        title="All Datasets",
        description=(
            "Whether to copy also deleted HDAs/HDCAs. Only applies when " "providing a `history_id` to copy from."
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
    collection_type: Optional[CollectionType] = CollectionTypeField
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


# Required for self-referencing models
# See https://pydantic-docs.helpmanual.io/usage/postponed_annotations/#self-referencing-models
CollectionElementIdentifier.update_forward_refs()


class CreateNewCollectionPayload(Model):
    collection_type: Optional[CollectionType] = CollectionTypeField
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
        default=False,
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


class StoreContentSource(Model):
    store_content_uri: Optional[str]
    store_dict: Optional[Dict[str, Any]]
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
    duration: OptionalNumberT


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
    user_id: Optional[EncodedDatabaseIdField]
    payload: Union[WriteStoreToPayload, ShortTermStoreExportPayload]


class ExportObjectResultMetadata(Model):
    success: bool
    error: Optional[str]


class ExportObjectMetadata(Model):
    request_data: ExportObjectRequestMetadata
    result_data: Optional[ExportObjectResultMetadata]


class ObjectExportTaskResponse(ObjectExportResponseBase):
    task_uuid: UUID4 = Field(
        ...,
        title="Task ID",
        description="The identifier of the task processing the export.",
    )
    create_time: datetime = CreateTimeField
    export_metadata: Optional[ExportObjectMetadata]


class JobExportHistoryArchiveListResponse(Model):
    __root__: List[JobExportHistoryArchiveModel]


class ExportTaskListResponse(Model):
    __root__: List[ObjectExportTaskResponse]
    __accept_type__ = "application/vnd.galaxy.task.export+json"


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

    job_id: EncodedDatabaseIdField = Field(
        ...,
        title="Job ID",
        description="The encoded database ID of the job that is currently processing a particular request.",
    )


class JobBaseModel(Model):
    id: DecodedDatabaseIdField = EntityIdField
    model_class: JOB_MODEL_CLASS = ModelClassField(JOB_MODEL_CLASS)
    tool_id: str = Field(
        ...,
        title="Tool ID",
        description="Identifier of the tool that generated this job.",
    )
    history_id: Optional[DecodedDatabaseIdField] = Field(
        None,
        title="History ID",
        description="The encoded ID of the history associated with this item.",
    )
    state: Job.states = Field(
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
    galaxy_version: str = Field(
        ...,
        title="Galaxy Version",
        description="The (major) version of Galaxy used to create this job.",
        example="21.05",
    )


class JobImportHistoryResponse(JobBaseModel):
    message: str = Field(
        ...,
        title="Message",
        description="Text message containing information about the history import.",
    )


class ItemStateSummary(Model):
    id: DecodedDatabaseIdField = EntityIdField
    populated_state: DatasetCollection.populated_states = PopulatedStateField
    states: Dict[Job.states, int] = Field(
        {}, title="States", description=("A dictionary of job states and the number of jobs in that state.")
    )


class JobStateSummary(ItemStateSummary):
    model: Literal["Job"] = ModelClassField("Job")


class ImplicitCollectionJobsStateSummary(ItemStateSummary):
    model: Literal["ImplicitCollectionJobs"] = ModelClassField("ImplicitCollectionJobs")


class WorkflowInvocationStateSummary(ItemStateSummary):
    model: Literal["WorkflowInvocation"] = ModelClassField("WorkflowInvocation")


class JobSummary(JobBaseModel):
    """Basic information about a job."""

    external_id: Optional[str] = Field(
        None,
        title="External ID",
        description=(
            "The job id used by the external job runner (Condor, Pulsar, etc.)" "Only administrator can see this value."
        ),
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


class DatasetSourceId(Model):
    id: DecodedDatabaseIdField = EntityIdField
    src: DatasetSourceType = Field(
        ...,
        title="Source",
        description="The source of this dataset, either `hda` or `ldda` depending of its origin.",
    )


class DatasetJobInfo(DatasetSourceId):
    uuid: UUID4 = UuidField


class JobDetails(JobSummary):
    command_version: str = Field(
        ...,
        title="Command Version",
        description="Tool version indicated during job execution.",
    )
    params: Any = Field(
        ...,
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

    class Config:
        schema_extra = {
            "example": {
                "title": "Job Start Time",
                "value": "2021-02-25 14:55:40",
                "plugin": "core",
                "name": "start_epoch",
                "raw_value": "1614261340.0000000",
            }
        }


class JobMetricCollection(Model):
    """Represents a collection of metrics associated with a Job."""

    __root__: List[JobMetric] = Field(
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


class StoredWorkflowSummary(Model):
    id: DecodedDatabaseIdField = EntityIdField
    model_class: STORED_WORKFLOW_MODEL_CLASS = ModelClassField(STORED_WORKFLOW_MODEL_CLASS)
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    name: str = Field(
        ...,
        title="Name",
        description="The name of the history.",
    )
    url: RelativeUrl = RelativeUrlField
    published: bool = Field(
        ...,
        title="Published",
        description="Whether this workflow is currently publicly available to all users.",
    )
    annotations: List[str] = Field(  # Inconsistency? Why workflows summaries use a list instead of an optional string?
        ...,
        title="Annotations",
        description="An list of annotations to provide details or to help understand the purpose and usage of this workflow.",
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
    latest_workflow_uuid: UUID4 = Field(  # Is this really used?
        ...,
        title="Latest workflow UUID",
        description="TODO",
    )
    number_of_steps: int = Field(
        ...,
        title="Number of Steps",
        description="The number of steps that make up this workflow.",
    )
    show_in_tool_panel: bool = Field(
        ...,
        title="Show in Tool Panel",
        description="Whether to display this workflow in the Tools Panel.",
    )


class WorkflowInput(Model):
    label: str = Field(
        ...,
        title="Label",
        description="Label of the input.",
    )
    value: str = Field(
        ...,
        title="Value",
        description="TODO",
    )
    uuid: UUID4 = Field(
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
        ...,
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


class WorkflowModuleType(str, Enum):
    """Available types of modules that represent a step in a Workflow."""

    data_input = "data_input"
    data_collection_input = "data_collection_input"
    parameter_input = "parameter_input"
    subworkflow = "subworkflow"
    tool = "tool"
    pause = "pause"  # Experimental


class WorkflowStepBase(Model):
    id: int = Field(
        ...,
        title="ID",
        description="The identifier of the step. It matches the index order of the step inside the workflow.",
    )
    type: WorkflowModuleType = Field(..., title="Type", description="The type of workflow module.")
    annotation: Optional[str] = AnnotationField
    input_steps: Dict[str, InputStep] = Field(
        ...,
        title="Input Steps",
        description="A dictionary containing information about the inputs connected to this workflow step.",
    )


class ToolBasedWorkflowStep(WorkflowStepBase):
    tool_id: Optional[str] = Field(
        None, title="Tool ID", description="The unique name of the tool associated with this step."
    )
    tool_version: Optional[str] = Field(
        None, title="Tool Version", description="The version of the tool associated with this step."
    )
    tool_inputs: Any = Field(..., title="Tool Inputs", description="TODO")


class InputDataStep(ToolBasedWorkflowStep):
    type: WorkflowModuleType = Field(
        WorkflowModuleType.data_input, const=True, title="Type", description="The type of workflow module."
    )


class InputDataCollectionStep(ToolBasedWorkflowStep):
    type: WorkflowModuleType = Field(
        WorkflowModuleType.data_collection_input, const=True, title="Type", description="The type of workflow module."
    )


class InputParameterStep(ToolBasedWorkflowStep):
    type: WorkflowModuleType = Field(
        WorkflowModuleType.parameter_input, const=True, title="Type", description="The type of workflow module."
    )


class PauseStep(WorkflowStepBase):
    type: WorkflowModuleType = Field(
        WorkflowModuleType.pause, const=True, title="Type", description="The type of workflow module."
    )


class ToolStep(ToolBasedWorkflowStep):
    type: WorkflowModuleType = Field(
        WorkflowModuleType.tool, const=True, title="Type", description="The type of workflow module."
    )


class SubworkflowStep(WorkflowStepBase):
    type: WorkflowModuleType = Field(
        WorkflowModuleType.subworkflow, const=True, title="Type", description="The type of workflow module."
    )
    workflow_id: DecodedDatabaseIdField = Field(
        ..., title="Workflow ID", description="The encoded ID of the workflow that will be run on this step."
    )


class Creator(Model):
    class_: str = Field(..., alias="class", title="Class", description="The class representing this creator.")
    name: str = Field(..., title="Name", description="The name of the creator.")
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
        const=True,
        alias="class",
    )


class Person(Creator):
    class_: str = Field(
        "Person",
        const=True,
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


class StoredWorkflowDetailed(StoredWorkflowSummary):
    annotation: Optional[str] = AnnotationField  # Inconsistency? See comment on StoredWorkflowSummary.annotations
    license: Optional[str] = Field(
        None, title="License", description="SPDX Identifier of the license associated with this workflow."
    )
    version: int = Field(
        ..., title="Version", description="The version of the workflow represented by an incremental number."
    )
    inputs: Dict[int, WorkflowInput] = Field(
        {}, title="Inputs", description="A dictionary containing information about all the inputs of the workflow."
    )
    creator: Optional[List[Union[Person, Organization]]] = Field(
        None,
        title="Creator",
        description=("Additional information about the creator (or multiple creators) of this workflow."),
    )
    steps: Dict[
        int,
        Union[
            InputDataStep,
            InputDataCollectionStep,
            InputParameterStep,
            PauseStep,
            ToolStep,
            SubworkflowStep,
        ],
    ] = Field({}, title="Steps", description="A dictionary with information about all the steps of the workflow.")


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
        [], title="Workflow Outputs", description="The version of the tool associated with this step."
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

RoleIdField = Field(title="ID", description="Encoded ID of the role")
RoleNameField = Field(title="Name", description="Name of the role")
RoleDescriptionField = Field(title="Description", description="Description of the role")


class BasicRoleModel(Model):
    id: DecodedDatabaseIdField = RoleIdField
    name: str = RoleNameField
    type: str = Field(title="Type", description="Type or category of the role")


class RoleModel(BasicRoleModel):
    description: Optional[str] = RoleDescriptionField
    url: RelativeUrl = RelativeUrlField
    model_class: Literal["Role"] = ModelClassField("Role")


class RoleDefinitionModel(Model):
    name: str = RoleNameField
    description: str = RoleDescriptionField
    user_ids: Optional[List[DecodedDatabaseIdField]] = Field(title="User IDs", default=[])
    group_ids: Optional[List[DecodedDatabaseIdField]] = Field(title="Group IDs", default=[])


class RoleListModel(Model):
    __root__: List[RoleModel]


# The tuple should probably be another proper model instead?
# Keeping it as a Tuple for now for backward compatibility
# TODO: Use Tuple again when https://github.com/tiangolo/fastapi/issues/3665 is fixed upstream
RoleNameIdTuple = List[str]  # Tuple[str, DecodedDatabaseIdField]

# Group_Roles -----------------------------------------------------------------


class GroupRoleModel(Model):
    id: DecodedDatabaseIdField = RoleIdField
    name: str = RoleNameField
    url: RelativeUrl = RelativeUrlField


class GroupRoleListModel(Model):
    __root__: List[GroupRoleModel]


# Users -----------------------------------------------------------------

UserIdField = Field(title="ID", description="Encoded ID of the user")
UserEmailField = Field(title="Email", description="Email of the user")
UserDescriptionField = Field(title="Description", description="Description of the user")

# Group_Users -----------------------------------------------------------------


class GroupUserModel(Model):
    id: DecodedDatabaseIdField = UserIdField
    email: str = UserEmailField
    url: RelativeUrl = RelativeUrlField


class GroupUserListModel(Model):
    __root__: List[GroupUserModel]


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
    id: DecodedDatabaseIdField = EntityIdField


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
    # See https://github.com/galaxyproject/galaxy/issues/10453
    latest_installable_revision: str = Field(
        title="Latest installed revision", description="Most recent version available on the tool shed"
    )
    revision_update: str
    revision_upgrade: Optional[str]
    repository_deprecated: str = Field(
        title="Repository deprecated", description="Repository has been depreciated on the tool shed"
    )


class InstalledToolShedRepository(Model):
    model_class: Literal["ToolShedRepository"] = ModelClassField("ToolShedRepository")
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
    ctx_rev: str = Field(
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


class InstalledToolShedRepositories(Model):
    __root__: List[InstalledToolShedRepository]


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


class LibraryLegacySummary(Model):
    model_class: Literal["Library"] = ModelClassField("Library")
    id: DecodedDatabaseIdField = Field(
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
    root_folder_id: LibraryFolderDatabaseIdField = Field(
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
        example="2 months ago",
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


class LibrarySummaryList(Model):
    __root__: List[LibrarySummary] = Field(
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


class LegacyLibraryPermissionsPayload(Model):
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


class LibraryPermissionsPayloadBase(Model):
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
        ...,
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


class LibraryFolderDetails(Model):
    model_class: Literal["LibraryFolder"] = ModelClassField("LibraryFolder")
    id: LibraryFolderDatabaseIdField = Field(
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
    parent_library_id: DecodedDatabaseIdField = Field(
        ...,
        title="Parent Library ID",
        description="Encoded ID of the Library this folder belongs to.",
    )
    parent_id: Optional[LibraryFolderDatabaseIdField] = Field(
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
        description="A list available roles that can be assigned to a particular permission.",
    )
    page: int = Field(
        ...,
        title="Page",
        description="Current page .",
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
    id: DecodedDatabaseIdField
    name: str
    type: str
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    can_manage: bool
    deleted: bool


class FolderLibraryFolderItem(LibraryFolderItemBase):
    type: Literal["folder"]
    can_modify: bool
    description: Optional[str] = FolderDescriptionField


class FileLibraryFolderItem(LibraryFolderItemBase):
    type: Literal["file"]
    file_ext: str
    date_uploaded: datetime
    is_unrestricted: bool
    is_private: bool
    state: Dataset.states = DatasetStateField
    file_size: str
    raw_size: int
    ldda_id: DecodedDatabaseIdField
    tags: str
    message: Optional[str]


AnyLibraryFolderItem = Annotated[Union[FileLibraryFolderItem, FolderLibraryFolderItem], Field(discriminator="type")]


class LibraryFolderMetadata(Model):
    parent_library_id: DecodedDatabaseIdField
    folder_name: str
    folder_description: str
    total_rows: int
    can_modify_folder: bool
    can_add_library_item: bool
    full_path: List[List[str]]


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


class UpdateDatasetPermissionsPayload(Model):
    action: Optional[DatasetPermissionAction] = Field(
        DatasetPermissionAction.set_permissions,
        title="Action",
        description="Indicates what action should be performed on the dataset.",
    )
    access_ids: Optional[RoleIdList] = Field(
        [],
        alias="access_ids[]",  # Added for backward compatibility but it looks really ugly...
        title="Access IDs",
        description="A list of role encoded IDs defining roles that should have access permission on the dataset.",
    )
    manage_ids: Optional[RoleIdList] = Field(
        [],
        alias="manage_ids[]",
        title="Manage IDs",
        description="A list of role encoded IDs defining roles that should have manage permission on the dataset.",
    )
    modify_ids: Optional[RoleIdList] = Field(
        [],
        alias="modify_ids[]",
        title="Modify IDs",
        description="A list of role encoded IDs defining roles that should have modify permission on the dataset.",
    )


class CustomHistoryItem(Model):
    """Can contain any serializable property of the item.

    Allows arbitrary custom keys to be specified in the serialization
    parameters without a particular view (predefined set of keys).
    """

    class Config:
        extra = Extra.allow


AnyHDA = Union[HDADetailed, HDASummary]
AnyHDCA = Union[HDCADetailed, HDCASummary]
AnyHistoryContentItem = Union[
    AnyHDA,
    AnyHDCA,
    CustomHistoryItem,
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


class DeleteHistoryContentResult(CustomHistoryItem):
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


class HistoryContentsArchiveDryRunResult(Model):
    """
    Contains a collection of filepath/filename entries that represent
    the contents that would have been included in the archive.
    This is returned when the `dry_run` flag is active when
    creating an archive with the contents of the history.

    This is used for debugging purposes.
    """

    # TODO: Use Tuple again when https://github.com/tiangolo/fastapi/issues/3665 is fixed upstream
    __root__: List[List[str]]  # List[Tuple[str, str]]


class HistoryContentStats(Model):
    total_matches: int = Field(
        ...,
        title="Total Matches",
        description=("The total number of items that match the search query without any pagination"),
    )


class HistoryContentsResult(Model):
    """List of history content items.
    Can contain different views and kinds of items.
    """

    __root__: List[AnyHistoryContentItem]


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

    class Config:
        extra = Extra.allow


UserIdentifier = Union[DecodedDatabaseIdField, str]


class ShareWithPayload(Model):
    user_ids: List[UserIdentifier] = Field(
        ...,
        title="User Identifiers",
        description=(
            "A collection of encoded IDs (or email addresses) of users " "that this resource will be shared with."
        ),
    )
    share_option: Optional[SharingOptions] = Field(
        None,
        title="Share Option",
        description=(
            "User choice for sharing resources which its contents may be restricted:\n"
            " - None: The user did not choose anything yet or no option is needed.\n"
            f" - {SharingOptions.make_public}: The contents of the resource will be made publicly accessible.\n"
            f" - {SharingOptions.make_accessible_to_shared}: This will automatically create a new `sharing role` allowing protected contents to be accessed only by the desired users.\n"
            f" - {SharingOptions.no_changes}: This won't change the current permissions for the contents. The user which this resource will be shared may not be able to access all its contents.\n"
        ),
    )


class SetSlugPayload(Model):
    new_slug: str = Field(
        ...,
        title="New Slug",
        description="The slug that will be used to access this shared item.",
    )


class UserEmail(Model):
    id: DecodedDatabaseIdField = Field(
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
    id: DecodedDatabaseIdField = Field(
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


class HDABasicInfo(Model):
    id: DecodedDatabaseIdField
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
    description="Raw text contents of the first page revision (type dependent on content_format).",
)


class PageSummaryBase(Model):
    title: str = Field(
        ...,  # Required
        title="Title",
        description="The name of the page",
    )
    slug: str = Field(
        ...,  # Required
        title="Identifier",
        description="The title slug for the page URL, must be unique.",
        regex=r"^[a-z0-9\-]+$",
    )


class MaterializeDatasetInstanceAPIRequest(Model):
    source: DatasetSourceType = Field(
        None,
        title="Source",
        description="The source of the content. Can be other history element to be copied or library elements.",
    )
    content: DecodedDatabaseIdField = Field(
        None,
        title="Content",
        description=(
            "Depending on the `source` it can be:\n"
            "- The encoded id of the source library dataset\n"
            "- The encoded id of the the HDA\n"
        ),
    )


class MaterializeDatasetInstanceRequest(MaterializeDatasetInstanceAPIRequest):
    history_id: DecodedDatabaseIdField


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

    class Config:
        use_enum_values = True  # When using .dict()
        extra = Extra.allow  # Allow any other extra fields


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


class AsyncFile(Model):
    storage_request_id: UUID
    task: AsyncTaskResultSummary


class PageSummary(PageSummaryBase):
    id: DecodedDatabaseIdField = Field(
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
        description="The encoded email of the user",
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
    latest_revision_id: DecodedDatabaseIdField = Field(
        ...,  # Required
        title="Latest revision ID",
        description="The encoded ID of the last revision of this Page.",
    )
    revision_ids: List[DecodedDatabaseIdField] = Field(
        ...,  # Required
        title="List of revisions",
        description="The history with the encoded ID of each revision of the Page.",
    )


class PageDetails(PageSummary):
    content_format: PageContentFormat = ContentFormatField
    content: Optional[str] = ContentField
    generate_version: Optional[str] = Field(
        None,
        title="Galaxy Version",
        description="The version of Galaxy this page was generated with.",
    )
    generate_time: Optional[str] = Field(
        None,
        title="Generate Date",
        description="The date this page was generated.",
    )

    class Config:
        extra = Extra.allow  # Allow any other extra fields


class PageSummaryList(Model):
    __root__: List[PageSummary] = Field(
        default=[],
        title="List with summary information of Pages.",
    )
