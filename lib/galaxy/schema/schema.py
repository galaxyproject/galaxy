from datetime import datetime
from enum import Enum
from typing import (
    Any,
    List,
    Optional,
    Union,
)

from pydantic import (
    AnyUrl,
    BaseModel,
    Extra,
    Field,
    FilePath,
    UUID4,
)

from galaxy.model import (
    Dataset,
    DatasetCollection,
    DatasetInstance,
)
from galaxy.schema.fields import (
    EncodedDatabaseIdField,
    ModelClassField,
)

USER_MODEL_CLASS_NAME = "User"
HDA_MODEL_CLASS_NAME = "HistoryDatasetAssociation"
DC_MODEL_CLASS_NAME = "DatasetCollection"
DCE_MODEL_CLASS_NAME = "DatasetCollectionElement"
HDCA_MODEL_CLASS_NAME = "HistoryDatasetCollectionAssociation"


# Generic and common Field annotations that can be reused across models

UrlField: AnyUrl = Field(
    ...,
    title="URL",
    description="The relative URL to access this item.",
    deprecated=False  # TODO Should this field be deprecated in FastAPI?
)

DownloadUrlField: AnyUrl = Field(
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

EncodedEntityIdField: EncodedDatabaseIdField = Field(
    ...,
    title="ID",
    description="The encoded ID of this entity.",
)

DatasetStateField: Dataset.states = Field(
    ...,
    title="State",
    description="The current state of this dataset.",
)

CreateTimeField: datetime = Field(
    ...,
    title="Create Time",
    description="The time and date this item was created.",
)

UpdateTimeField: datetime = Field(
    ...,
    title="Update Time",
    description="The last time and date this item was updated.",
)

CollectionTypeField: str = Field(
    ...,
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
    ...,
    title="Populated",
    description="Whether the dataset collection elements (and any subcollections elements) were successfully populated.",
)

ElementsField: List['DCESummary'] = Field(
    [],
    title="Elements",
    description="The summary information of each of the elements inside the dataset collection.",
)


class UserModel(BaseModel):
    """User in a transaction context."""
    id: EncodedDatabaseIdField = Field(title='ID', description='User ID')
    username: str = Field(title='Username', description='User username')
    email: str = Field(title='Email', description='User email')
    active: bool = Field(title='Active', description='User is active')
    deleted: bool = Field(title='Deleted', description='User is deleted')
    last_password_change: datetime = Field(title='Last password change', description='')
    model_class: str = ModelClassField(USER_MODEL_CLASS_NAME)


class JobSourceType(str, Enum):
    """Available types of job sources (model classes) that produce dataset collections."""
    Job = "Job"
    ImplicitCollectionJobs = "ImplicitCollectionJobs"
    WorkflowInvocation = "WorkflowInvocation"


class HistoryContentType(str, Enum):
    """Available types of History contents."""
    dataset = "dataset"
    dataset_collection = "dataset_collection"


class DCEType(str, Enum):  # TODO: suspiciously similar to HistoryContentType
    """Available types of dataset collection elements."""
    hda = "hda"
    dataset_collection = "dataset_collection"


class TagCollection(BaseModel):
    """Represents the collection of tags associated with an item."""
    __root__: List[str] = Field(
        [],
        title="Tags",
        description="The collection of tags associated with an item.",
    )


class MetadataFile(BaseModel):
    """Metadata file associated with a dataset."""
    file_type: str = Field(
        ...,
        title="File Type",
        description="TODO",
    )
    download_url: AnyUrl = DownloadUrlField


class DatasetPermissions(BaseModel):
    """Role-based permissions for accessing and managing a dataset."""
    manage: List[EncodedDatabaseIdField] = Field(
        [],
        title="Management",
        description="The set of roles (encoded IDs) that can manage this dataset.",
    )
    access: List[EncodedDatabaseIdField] = Field(
        [],
        title="Access",
        description="The set of roles (encoded IDs) that can access this dataset.",
    )


class Hyperlink(BaseModel):
    """Represents some text with an Hyperlink."""
    target: str = Field(
        ...,
        title="Target",
        description="Specifies where to open the linked document.",
        example="_blank"
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


class DisplayApp(BaseModel):
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


class Visualization(BaseModel):  # TODO annotate this model
    class Config:
        extra = Extra.allow  # Allow any fields temporarily until the model is annotated


class HistoryItemBase(BaseModel):
    """Basic information provided by items contained in a History."""
    id: EncodedDatabaseIdField = EncodedEntityIdField
    name: str = Field(
        ...,
        title="Name",
        description="The name of the item.",
    )
    history_id: EncodedDatabaseIdField = Field(
        ...,
        title="History ID",
        description="The encoded ID of the history containing this item.",
    )
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
    type_id: str = Field(
        ...,
        title="Type - ID",
        description="The type and the encoded ID of this item. Used for caching.",
        example="dataset-616e371b2cc6c62e",
    )
    type: str = Field(
        ...,
        title="Type",
        description="The type of this item.",
    )
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    url: AnyUrl = UrlField
    tags: TagCollection


class HDASummary(HistoryItemCommon):
    """History Dataset Association summary information."""
    dataset_id: EncodedDatabaseIdField = Field(
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


class HDADetailed(HDASummary):
    """History Dataset Association detailed information."""
    model_class: str = ModelClassField(HDA_MODEL_CLASS_NAME)
    hda_ldda: str = Field(
        "hda",
        const=True,
        title="HDA or LDDA",
        description="Whether this dataset belongs to a history (HDA) or a library (LDDA).",
        deprecated=False  # TODO Should this field be deprecated in favor of model_class?
    )
    accessible: bool = AccessibleField
    genome_build: str = Field(
        "?",
        title="Genome Build",
        description="TODO",
    )
    misc_info: str = Field(
        ...,
        title="Miscellaneous Information",
        description="TODO",
    )
    misc_blurb: str = Field(
        ...,
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
    metadata: Any = Field(  # TODO: create pydantic model for metadata?
        ...,
        title="Metadata",
        description="The metadata associated with this dataset.",
    )
    meta_files: List[MetadataFile] = Field(
        [],
        title="Metadata Files",
        description="Collection of metadata files associated with this dataset.",
    )
    data_type: str = Field(
        ...,
        title="Data Type",
        description="The fully qualified name of the class implementing the data type of this dataset.",
        example="galaxy.datatypes.data.Text"
    )
    peek: str = Field(
        ...,
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
    uuid: UUID4 = Field(
        ...,
        title="UUID",
        description="Universal unique identifier for this dataset.",
    )
    permissions: DatasetPermissions = Field(
        ...,
        title="Permissions",
        description="Role-based access and manage control permissions for the dataset.",
    )
    file_name: FilePath = Field(
        ...,
        title="File Name",
        description="The full path to the dataset file.",
    )
    display_apps: List[DisplayApp] = Field(
        [],
        title="Display Applications",
        description="Contains new-style display app urls.",
    )
    display_types: List[DisplayApp] = Field(
        [],
        title="Legacy Display Applications",
        description="Contains old-style display app urls.",
        deprecated=False,  # TODO: Should this field be deprecated in favor of display_apps?
    )
    visualizations: List[Visualization] = Field(
        [],
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
    download_url: AnyUrl = DownloadUrlField
    type: str = Field(
        "file",
        const=True,
        title="Type",
        description="This is always `file` for datasets.",
    )
    api_type: str = Field(
        "file",
        const=True,
        title="API Type",
        description="TODO",
        deprecated=False,  # TODO: Should this field be deprecated as announced in release 16.04?
    )
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
    parent_id: Optional[EncodedDatabaseIdField] = Field(
        None,
        title="Parent ID",
        description="TODO",
    )
    designation: Optional[str] = Field(
        None,
        title="Designation",
        description="TODO",
    )


class HDABeta(HDADetailed):  # TODO: change HDABeta name to a more appropriate one.
    """History Dataset Association information used in the new Beta History."""
    # Equivalent to `betawebclient` serialization view for HDAs
    pass


class DCSummary(BaseModel):
    """Dataset Collection summary information."""
    model_class: str = ModelClassField(DC_MODEL_CLASS_NAME)
    id: EncodedDatabaseIdField = EncodedEntityIdField
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    collection_type: str = CollectionTypeField
    populated_state: DatasetCollection.populated_states = PopulatedStateField
    populated_state_message: Optional[str] = PopulatedStateMessageField
    element_count: Optional[int] = ElementCountField


class DCESummary(BaseModel):
    """Dataset Collection Element summary information."""
    id: EncodedDatabaseIdField = EncodedEntityIdField
    model_class: str = ModelClassField(DCE_MODEL_CLASS_NAME)
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
    object: Union[HDASummary, DCSummary] = Field(
        ...,
        title="Object",
        description="The element's specific data depending on the value of `element_type`.",
    )


class DCDetailed(DCSummary):
    """Dataset Collection detailed information."""
    populated: bool = PopulatedField
    elements: List[DCESummary] = ElementsField


class HDCASummary(HistoryItemCommon):
    """History Dataset Collection Association summary information."""
    model_class: str = ModelClassField(HDCA_MODEL_CLASS_NAME)  # TODO: inconsistency? HDASummary does not have model_class only the detailed view has it...
    type: str = Field(
        "collection",
        const=True,
        title="Type",
        description="This is always `collection` for dataset collections.",
    )
    collection_type: str = CollectionTypeField
    populated_state: DatasetCollection.populated_states = PopulatedStateField
    populated_state_message: Optional[str] = PopulatedStateMessageField
    element_count: Optional[int] = ElementCountField
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
    contents_url: AnyUrl = Field(
        ...,
        title="Contents URL",
        description="The relative URL to access the contents of this dataset collection.",
    )


class HDCADetailed(HDCASummary):
    """History Dataset Collection Association detailed information."""
    populated: bool = PopulatedField
    elements: List[DCESummary] = ElementsField


class HDCJobStateSummary(BaseModel):
    """Overview of the job states working inside a dataset collection."""
    all_jobs: int = Field(
        0,
        title="All jobs",
        description="Total number of jobs in the associated with a dataset collection.",
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


class HDCABeta(HDCADetailed):  # TODO: change HDCABeta name to a more appropriate one.
    """History Dataset Collection Association information used in the new Beta History."""
    # Equivalent to `betawebclient` serialization view for HDCAs
    collection_id: EncodedDatabaseIdField = Field(
        # TODO: inconsistency? the equivalent counterpart for HDAs, `dataset_id`, is declared in `HDASummary` scope
        # while in HDCAs it is only serialized in the new `betawebclient` view?
        ...,
        title="Collection ID",
        description="The encoded ID of the dataset collection associated with this HDCA.",
    )
    job_state_summary: Optional[HDCJobStateSummary] = Field(
        None,
        title="Job State Summary",
        description="Overview of the job states working inside the dataset collection.",
    )
