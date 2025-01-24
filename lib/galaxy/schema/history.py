from datetime import datetime
from typing import (
    List,
    Optional,
)

from pydantic import (
    ConfigDict,
    Field,
    RootModel,
)
from typing_extensions import Literal

from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import (
    CreateTimeField,
    Model,
    TagCollection,
    UpdateTimeField,
)

HistorySortByEnum = Literal["create_time", "name", "update_time", "username"]


class HistoryIndexQueryPayload(Model):
    show_own: Optional[bool] = None
    show_published: Optional[bool] = None
    show_shared: Optional[bool] = None
    show_archived: Optional[bool] = None
    sort_by: HistorySortByEnum = Field("update_time", title="Sort By", description="Sort by this attribute.")
    sort_desc: Optional[bool] = Field(default=True, title="Sort descending", description="Sort in descending order.")
    search: Optional[str] = Field(default=None, title="Filter text", description="Freetext to search.")
    limit: Optional[int] = Field(
        default=100, lt=1000, title="Limit", description="Maximum number of entries to return."
    )
    offset: Optional[int] = Field(default=0, title="Offset", description="Number of entries to skip.")


class HistoryQueryResult(Model):
    model_config = ConfigDict(extra="allow")

    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="Encoded ID of the History.",
    )
    annotation: Optional[str] = Field(
        default=None,
        title="Annotation",
        description="The annotation of this History.",
    )
    deleted: bool = Field(
        ...,  # Required
        title="Deleted",
        description="Whether this History has been deleted.",
    )
    importable: bool = Field(
        ...,  # Required
        title="Importable",
        description="Whether this History can be imported.",
    )
    published: bool = Field(
        ...,  # Required
        title="Published",
        description="Whether this History has been published.",
    )
    tags: Optional[TagCollection] = Field(
        ...,
        title="Tags",
        description="A list of tags to add to this item.",
    )
    name: str = Field(
        title="Name",
        description="The name of the History.",
    )
    create_time: Optional[datetime] = CreateTimeField
    update_time: Optional[datetime] = UpdateTimeField


class HistoryQueryResultList(RootModel):
    root: List[HistoryQueryResult] = Field(
        default=[],
        title="List with detailed information of Histories.",
    )
