"""This module contains general pydantic models and common schema field annotations for them."""

from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Dict,
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
    Job,
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
HISTORY_MODEL_CLASS_NAME = "History"
JOB_MODEL_CLASS_NAME = "Job"
STORED_WORKFLOW_MODEL_CLASS_NAME = "StoredWorkflow"


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

HistoryIdField: EncodedDatabaseIdField = Field(
    ...,
    title="History ID",
    description="The encoded ID of the history associated with this item.",
)

UuidField: UUID4 = Field(
    ...,
    title="UUID",
    description="Universal unique identifier for this dataset.",
)

GenomeBuildField: str = Field(
    "?",
    title="Genome Build",
    description="TODO",
)


class Model(BaseModel):
    """Base model definition with common configuration used by all derived models."""
    class Config:
        use_enum_values = True  # when using .dict()


class UserModel(Model):
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


class DatasetSourceType(str, Enum):
    hda = "hda"
    ldda = "ldda"


class TagCollection(Model):
    """Represents the collection of tags associated with an item."""
    __root__: List[str] = Field(
        [],
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
    download_url: AnyUrl = DownloadUrlField


class DatasetPermissions(Model):
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


class Hyperlink(Model):
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
    id: EncodedDatabaseIdField = EncodedEntityIdField
    name: str = Field(
        ...,
        title="Name",
        description="The name of the item.",
    )
    history_id: EncodedDatabaseIdField = HistoryIdField
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
    hda_ldda: DatasetSourceType = Field(
        DatasetSourceType.hda,
        const=True,
        title="HDA or LDDA",
        description="Whether this dataset belongs to a history (HDA) or a library (LDDA).",
        deprecated=False  # TODO Should this field be deprecated in favor of model_class?
    )
    accessible: bool = AccessibleField
    genome_build: str = GenomeBuildField
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
    uuid: UUID4 = UuidField
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


class DCSummary(Model):
    """Dataset Collection summary information."""
    model_class: str = ModelClassField(DC_MODEL_CLASS_NAME)
    id: EncodedDatabaseIdField = EncodedEntityIdField
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    collection_type: str = CollectionTypeField
    populated_state: DatasetCollection.populated_states = PopulatedStateField
    populated_state_message: Optional[str] = PopulatedStateMessageField
    element_count: Optional[int] = ElementCountField


class DCESummary(Model):
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


class HistorySummary(Model):
    """History summary information."""
    model_class: str = ModelClassField(HISTORY_MODEL_CLASS_NAME)
    id: EncodedDatabaseIdField = EncodedEntityIdField
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
    url: AnyUrl = UrlField
    published: bool = Field(
        ...,
        title="Published",
        description="Whether this resource is currently publicly available to all users.",
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


class HistoryDetailed(HistorySummary):  # Equivalent to 'dev-detailed' view, which seems the default
    """History detailed information."""
    contents_url: AnyUrl = Field(
        ...,
        title="Contents URL",
        description="The relative URL to access the contents of this History.",
    )
    size: int = Field(
        ...,
        title="Size",
        description="The total size of the contents of this history in bytes.",
    )
    user_id: EncodedDatabaseIdField = Field(
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
    genome_build: str = GenomeBuildField
    contents_active: HistoryActiveContentCounts = Field(
        ...,
        title="Active Contents",
        description="Contains the number of active, deleted or hidden items in the History.",
    )
    hid_counter: int = Field(
        ...,
        title="HID Counter",
        description="TODO",
    )


class HistoryBeta(HistoryDetailed):
    """History detailed information used in the new Beta History."""
    annotation: Optional[str] = AnnotationField
    empty: bool = Field(
        ...,
        title="Empty",
        description="Whether this History has any content.",
    )
    nice_size: str = Field(
        ...,
        title="Nice Size",
        description="Human-readable size of the contents of this history.",
        example="95.4 MB"
    )
    purged: bool = Field(
        ...,
        title="Purged",
        description="Whether this History has been permanently removed.",
    )
    state: Dataset.states = Field(
        ...,
        title="State",
        description="The current state of the History based on the states of the datasets it contains.",
    )
    tags: TagCollection
    url: AnyUrl = UrlField


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


class JobSummary(Model):
    """Basic information about a job."""
    id: EncodedDatabaseIdField = EncodedEntityIdField
    model_class: str = ModelClassField(JOB_MODEL_CLASS_NAME)
    tool_id: str = Field(
        ...,
        title="Tool ID",
        description="Identifier of the tool that generated this job.",
    )
    history_id: EncodedDatabaseIdField = HistoryIdField
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
        example="21.05"
    )
    external_id: Optional[str] = Field(
        None,
        title="External ID",
        description=(
            "The job id used by the external job runner (Condor, Pulsar, etc.)"
            "Only administrator can see this value."
        )
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


class DatasetJobInfo(Model):
    id: EncodedDatabaseIdField = EncodedEntityIdField
    src: DatasetSourceType = Field(
        ...,
        title="Source",
        description="The source of this dataset, either `hda` or `ldda` depending of its origin.",
    )
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
                "raw_value": "1614261340.0000000"
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
    id: EncodedDatabaseIdField = EncodedEntityIdField
    model_class: str = ModelClassField(STORED_WORKFLOW_MODEL_CLASS_NAME)
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    name: str = Field(
        ...,
        title="Name",
        description="The name of the history.",
    )
    url: AnyUrl = UrlField
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


class WorkflowInput(BaseModel):
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


class InputStep(BaseModel):
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


class WorkflowStepBase(BaseModel):
    id: int = Field(
        ...,
        title="ID",
        description="The identifier of the step. It matches the index order of the step inside the workflow."
    )
    type: str = Field(
        ...,
        title="Type",
        description="The type of workflow module."
    )
    annotation: Optional[str] = AnnotationField
    input_steps: Dict[str, InputStep] = Field(
        ...,
        title="Input Steps",
        description="A dictionary containing information about the inputs connected to this workflow step."
    )


class WorkflowStep(WorkflowStepBase):
    tool_id: Optional[str] = Field(
        None,
        title="Tool ID",
        description="The unique name of the tool associated with this step."
    )
    tool_version: Optional[str] = Field(
        None,
        title="Tool Version",
        description="The version of the tool associated with this step."
    )
    tool_inputs: Any = Field(
        ...,
        title="Tool Inputs",
        description="TODO"
    )


class InputDataStep(WorkflowStep):
    type: str = Field(
        "data_input", const=True,
        title="Type",
        description="The type of workflow module."
    )


class InputDataCollectionStep(WorkflowStep):
    type: str = Field(
        "data_collection_input", const=True,
        title="Type",
        description="The type of workflow module."
    )


class InputParameterStep(WorkflowStep):
    type: str = Field(
        "parameter_input", const=True,
        title="Type",
        description="The type of workflow module."
    )


class PauseStep(WorkflowStep):
    type: str = Field(
        "pause", const=True,
        title="Type",
        description="The type of workflow module."
    )


class ToolStep(WorkflowStep):
    type: str = Field(
        "tool", const=True,
        title="Type",
        description="The type of workflow module."
    )


class SubworkflowStep(WorkflowStepBase):
    type: str = Field(
        "subworkflow", const=True,
        title="Type",
        description="The type of workflow module."
    )
    workflow_id: EncodedDatabaseIdField = Field(
        ...,
        title="Workflow ID",
        description="The encoded ID of the workflow that will be run on this step."
    )


class StoredWorkflowDetailed(StoredWorkflowSummary):
    annotation: Optional[str] = AnnotationField  # Inconsistency? See comment on StoredWorkflowSummary.annotations
    license: Optional[str] = Field(
        None,
        title="License",
        description="SPDX Identifier of the license associated with this workflow."
    )
    version: int = Field(
        ...,
        title="Version",
        description="The version of this workflow represented by an incremental number."
    )
    inputs: Dict[int, WorkflowInput] = Field(
        {},
        title="Inputs",
        description="A dictionary containing information about all the inputs of the workflow."
    )
    creator: Optional[Any] = Field(
        None,
        title="Creator",
        description=(
            "Additional information about the creator of this workflow. "
            "This information is heterogeneous."
        )
    )
    steps: Dict[int,
        Union[
            InputDataStep,
            InputDataCollectionStep,
            InputParameterStep,
            PauseStep,
            ToolStep,
            SubworkflowStep,
        ]
    ] = Field(
        {},
        title="Steps",
        description="A dictionary with information about all the steps of the workflow."
    )
