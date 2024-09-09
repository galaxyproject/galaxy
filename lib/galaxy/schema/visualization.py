from datetime import datetime
from typing import (
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
from typing_extensions import Literal

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
    ModelClassField,
)
from galaxy.schema.schema import (
    CreateTimeField,
    Model,
    SanitizedString,
    TagCollection,
    UpdateTimeField,
    WithModelClass,
)

VisualizationSortByEnum = Literal["create_time", "title", "update_time", "username"]

VISUALIZATION_MODEL_CLASS = Literal["Visualization"]
VISUALIZATION_REVISION_MODEL_CLASS = Literal["VisualizationRevision"]


class VisualizationIndexQueryPayload(Model):
    deleted: bool = False
    show_own: Optional[bool] = None
    show_published: Optional[bool] = None
    show_shared: Optional[bool] = None
    user_id: Optional[DecodedDatabaseIdField] = None
    sort_by: VisualizationSortByEnum = Field(
        "update_time", title="Sort By", description="Sort pages by this attribute."
    )
    sort_desc: Optional[bool] = Field(default=True, title="Sort descending", description="Sort in descending order.")
    search: Optional[str] = Field(default=None, title="Filter text", description="Freetext to search.")
    limit: Optional[int] = Field(default=100, lt=1000, title="Limit", description="Maximum number of pages to return.")
    offset: Optional[int] = Field(default=0, title="Offset", description="Number of pages to skip.")


class VisualizationSummary(Model):
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="Encoded ID of the Visualization.",
    )
    annotation: Optional[str] = Field(
        default=None,
        title="Annotation",
        description="The annotation of this Visualization.",
    )
    dbkey: Optional[str] = Field(
        default=None,
        title="DbKey",
        description="The database key of the visualization.",
    )
    deleted: bool = Field(
        ...,  # Required
        title="Deleted",
        description="Whether this Visualization has been deleted.",
    )
    importable: bool = Field(
        ...,  # Required
        title="Importable",
        description="Whether this Visualization can be imported.",
    )
    published: bool = Field(
        ...,  # Required
        title="Published",
        description="Whether this Visualization has been published.",
    )
    tags: Optional[TagCollection] = Field(
        ...,
        title="Tags",
        description="A list of tags to add to this item.",
    )
    title: str = Field(
        title="Title",
        description="The name of the visualization.",
    )
    type: str = Field(
        ...,
        title="Type",
        description="The type of the visualization.",
    )
    username: str = Field(
        ...,  # Required
        title="Username",
        description="The name of the user owning this Visualization.",
    )
    create_time: Optional[datetime] = CreateTimeField
    update_time: Optional[datetime] = UpdateTimeField
    model_config = ConfigDict(extra="allow")


class VisualizationSummaryList(RootModel):
    root: List[VisualizationSummary] = Field(
        default=[],
        title="List with detailed information of Visualizations.",
    )


class VisualizationRevisionResponse(Model, WithModelClass):
    model_class: VISUALIZATION_REVISION_MODEL_CLASS = ModelClassField(VISUALIZATION_REVISION_MODEL_CLASS)
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="Encoded ID of the Visualization Revision.",
    )
    visualization_id: EncodedDatabaseIdField = Field(
        ...,
        title="Visualization ID",
        description="Encoded ID of the Visualization.",
    )
    title: str = Field(
        ...,
        title="Title",
        description="The name of the visualization revision.",
    )
    dbkey: Optional[str] = Field(
        None,
        title="DbKey",
        description="The database key of the visualization.",
    )
    config: Dict = Field(
        ...,
        title="Config",
        description="The config of the visualization revision.",
    )


class VisualizationPluginResponse(Model):
    name: str = Field(
        ...,
        title="Name",
        description="The name of the plugin.",
    )
    html: str = Field(
        ...,
        title="HTML",
        description="The HTML of the plugin.",
    )
    description: str = Field(
        ...,
        title="Description",
        description="The description of the plugin.",
    )
    logo: Optional[str] = Field(
        None,
        title="Logo",
        description="The logo of the plugin.",
    )
    title: Optional[str] = Field(
        None,
        title="Title",
        description="The title of the plugin.",
    )
    target: str = Field(
        ...,
        title="Target",
        description="The target of the plugin.",
    )
    embeddable: bool = Field(
        ...,
        title="Embeddable",
        description="Whether the plugin is embeddable.",
    )
    entry_point: Dict = Field(
        ...,
        title="Entry Point",
        description="The entry point of the plugin.",
    )
    settings: List[Dict] = Field(
        ...,
        title="Settings",
        description="The settings of the plugin.",
    )
    groups: Optional[List[Dict]] = Field(
        None,
        title="Groups",
        description="The groups of the plugin.",
    )
    specs: Optional[Dict] = Field(
        None,
        title="Specs",
        description="The specs of the plugin.",
    )
    href: str = Field(
        ...,
        title="Href",
        description="The href of the plugin.",
    )


class VisualizationShowResponse(Model, WithModelClass):
    model_class: VISUALIZATION_MODEL_CLASS = ModelClassField(VISUALIZATION_MODEL_CLASS)
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="Encoded ID of the Visualization.",
    )
    title: str = Field(
        ...,
        title="Title",
        description="The name of the visualization.",
    )
    type: str = Field(
        ...,
        title="Type",
        description="The type of the visualization.",
    )
    user_id: EncodedDatabaseIdField = Field(
        ...,
        title="User ID",
        description="The ID of the user owning this Visualization.",
    )
    dbkey: Optional[str] = Field(
        None,
        title="DbKey",
        description="The database key of the visualization.",
    )
    slug: Optional[str] = Field(
        None,
        title="Slug",
        description="The slug of the visualization.",
    )
    latest_revision: VisualizationRevisionResponse = Field(
        ...,
        title="Latest Revision",
        description="The latest revision of this Visualization.",
    )
    revisions: List[EncodedDatabaseIdField] = Field(
        ...,
        title="Revisions",
        description="A list of encoded IDs of the revisions of this Visualization.",
    )
    url: str = Field(
        ...,
        title="URL",
        description="The URL of the visualization.",
    )
    username: str = Field(
        ...,
        title="Username",
        description="The name of the user owning this Visualization.",
    )
    email_hash: str = Field(
        ...,
        title="Email Hash",
        description="The hash of the email of the user owning this Visualization.",
    )
    tags: Optional[TagCollection] = Field(
        None,
        title="Tags",
        description="A list of tags to add to this item.",
    )
    annotation: Optional[str] = Field(
        None,
        title="Annotation",
        description="The annotation of this Visualization.",
    )
    plugin: Optional[VisualizationPluginResponse] = Field(
        None,
        title="Plugin",
        description="The plugin of this Visualization.",
    )


class VisualizationCreateResponse(Model):
    id: Optional[EncodedDatabaseIdField] = Field(
        None,
        title="ID",
        description="Encoded ID of the Visualization.",
    )


class VisualizationUpdateResponse(Model):
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="Encoded ID of the Visualization.",
    )
    revision: EncodedDatabaseIdField = Field(
        ...,
        title="Revision",
        description="Encoded ID of the Visualization Revision.",
    )


class VisualizationCreatePayload(Model):
    type: SanitizedString = Field(
        ...,
        title="Type",
        description="The type of the visualization.",
    )
    title: SanitizedString = Field(
        SanitizedString("Untitled Visualization"),
        title="Title",
        description="The name of the visualization.",
    )
    dbkey: Optional[SanitizedString] = Field(
        None,
        title="DbKey",
        description="The database key of the visualization.",
    )
    slug: Optional[SanitizedString] = Field(
        None,
        title="Slug",
        description="The slug of the visualization.",
    )
    annotation: Optional[SanitizedString] = Field(
        None,
        title="Annotation",
        description="The annotation of the visualization.",
    )
    config: Optional[dict] = Field(
        {},
        title="Config",
        description="The config of the visualization.",
    )
    save: Optional[bool] = Field(
        True,
        title="Save",
        description="Whether to save the visualization.",
    )


class VisualizationUpdatePayload(Model):
    title: Optional[SanitizedString] = Field(
        None,
        title="Title",
        description="The name of the visualization.",
    )
    dbkey: Optional[SanitizedString] = Field(
        None,
        title="DbKey",
        description="The database key of the visualization.",
    )
    deleted: Optional[bool] = Field(
        False,
        title="Deleted",
        description="Whether this Visualization has been deleted.",
    )
    config: Optional[Union[dict, bytes]] = Field(
        {},
        title="Config",
        description="The config of the visualization.",
    )
