from datetime import datetime
from enum import Enum
from typing import (
    Any,
    List,
    Optional,
)

from pydantic import (
    AnyUrl,
    BaseModel,
    Extra,
    Field,
    FilePath,
    UUID4,
)

from galaxy.model import Dataset, DatasetInstance
from galaxy.schema.fields import (
    AccessibleField,
    AnnotationField,
    DownloadUrlField,
    EncodedDatabaseIdField,
    ModelClassField,
    UrlField,
)

USER_MODEL_CLASS_NAME = "User"
HDA_MODEL_CLASS_NAME = "HistoryDatasetAssociation"

DatasetStateField: Dataset.states = Field(
    ...,
    title="State",
    description="The current state of this dataset.",
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


class HistoryContentType(str, Enum):
    dataset = "dataset"
    dataset_collection = "dataset_collection"


class TagCollection(BaseModel):
    __root__: List[str] = Field(
        [],
        title="Tags",
        description="The collection of tags associated with an item.",
    )


class MetadataFile(BaseModel):
    file_type: str = Field(
        ...,
        title="File Type",
        description="TODO",
    )
    download_url: AnyUrl = DownloadUrlField


class DatasetPermissions(BaseModel):
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
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="The encoded ID of the item.",
    )
    name: str = Field(
        ...,
        title="Name",
        description="The name of the dataset.",
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


class HistoryItemSummary(HistoryItemBase):
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
    create_time: datetime = Field(
        ...,
        title="Create Time",
        description="The time and date this item was created.",
    )
    update_time: datetime = Field(
        ...,
        title="Update Time",
        description="The last time and date this item was updated.",
    )
    url: AnyUrl = UrlField
    tags: TagCollection


class HDASummary(HistoryItemSummary):
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
    accessible: bool = AccessibleField
    state: Dataset.states = DatasetStateField


class HDADetailed(HDASummary):
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
