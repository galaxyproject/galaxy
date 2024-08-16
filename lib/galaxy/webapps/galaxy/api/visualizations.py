"""
Visualizations resource control over the API.

NOTE!: this is a work in progress and functionality and data structures
may change often.
"""

import logging
from typing import Optional

from fastapi import (
    Body,
    Path,
    Query,
    Response,
    status,
)
from typing_extensions import Annotated

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    SetSlugPayload,
    ShareWithPayload,
    ShareWithStatus,
    SharingStatus,
)
from galaxy.schema.visualization import (
    VisualizationIndexQueryPayload,
    VisualizationShow,
    VisualizationSortByEnum,
    VisualizationSummaryList,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    IndexQueryTag,
    Router,
    search_query_param,
)
from galaxy.webapps.galaxy.api.common import (
    LimitQueryParam,
    OffsetQueryParam,
)
from galaxy.webapps.galaxy.services.visualizations import VisualizationsService

log = logging.getLogger(__name__)

router = Router(tags=["visualizations"])

DeletedQueryParam: bool = Query(
    default=False, title="Display deleted", description="Whether to include deleted visualizations in the result."
)

UserIdQueryParam: Optional[DecodedDatabaseIdField] = Query(
    default=None,
    title="Encoded user ID to restrict query to, must be own id if not an admin user",
)

query_tags = [
    IndexQueryTag("title", "The visualization's title."),
    IndexQueryTag("slug", "The visualization's slug.", "s"),
    IndexQueryTag("tag", "The visualization's tags.", "t"),
    IndexQueryTag("user", "The visualization's owner's username.", "u"),
]

SearchQueryParam: Optional[str] = search_query_param(
    model_name="Visualization",
    tags=query_tags,
    free_text_fields=["title", "slug", "tag", "type"],
)

SharingQueryParam: bool = Query(
    default=False, title="Provide sharing status", description="Whether to provide sharing details in the result."
)

ShowOwnQueryParam: bool = Query(default=True, title="Show visualizations owned by user.", description="")

ShowPublishedQueryParam: bool = Query(default=True, title="Include published visualizations.", description="")

ShowSharedQueryParam: bool = Query(
    default=False, title="Include visualizations shared with authenticated user.", description=""
)

SortByQueryParam: VisualizationSortByEnum = Query(
    default="update_time",
    title="Sort attribute",
    description="Sort visualization index by this specified attribute on the visualization model",
)

SortDescQueryParam: bool = Query(
    default=True,
    title="Sort Descending",
    description="Sort in descending order?",
)

VisualizationIdPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="Visualization ID", description="The encoded database identifier of the Visualization."),
]


@router.cbv
class FastAPIVisualizations:
    service: VisualizationsService = depends(VisualizationsService)

    @router.get(
        "/api/visualizations",
        summary="Returns visualizations for the current user.",
    )
    async def index(
        self,
        response: Response,
        trans: ProvidesUserContext = DependsOnTrans,
        deleted: bool = DeletedQueryParam,
        limit: Optional[int] = LimitQueryParam,
        offset: Optional[int] = OffsetQueryParam,
        user_id: Optional[DecodedDatabaseIdField] = UserIdQueryParam,
        show_own: bool = ShowOwnQueryParam,
        show_published: bool = ShowPublishedQueryParam,
        show_shared: bool = ShowSharedQueryParam,
        sort_by: VisualizationSortByEnum = SortByQueryParam,
        sort_desc: bool = SortDescQueryParam,
        search: Optional[str] = SearchQueryParam,
    ) -> VisualizationSummaryList:
        payload = VisualizationIndexQueryPayload.model_construct(
            deleted=deleted,
            user_id=user_id,
            show_published=show_published,
            show_own=show_own,
            show_shared=show_shared,
            sort_by=sort_by,
            sort_desc=sort_desc,
            limit=limit,
            offset=offset,
            search=search,
        )
        entries, total_matches = self.service.index(trans, payload, include_total_count=True)
        response.headers["total_matches"] = str(total_matches)
        return entries

    @router.get(
        "/api/visualizations/{id}/sharing",
        summary="Get the current sharing status of the given Visualization.",
    )
    def sharing(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Return the sharing status of the item."""
        return self.service.shareable_service.sharing(trans, id)

    @router.put(
        "/api/visualizations/{id}/enable_link_access",
        summary="Makes this item accessible by a URL link.",
    )
    def enable_link_access(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item accessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.enable_link_access(trans, id)

    @router.put(
        "/api/visualizations/{id}/disable_link_access",
        summary="Makes this item inaccessible by a URL link.",
    )
    def disable_link_access(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item inaccessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.disable_link_access(trans, id)

    @router.put(
        "/api/visualizations/{id}/publish",
        summary="Makes this item public and accessible by a URL link.",
    )
    def publish(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item publicly available by a URL link and return the current sharing status."""
        return self.service.shareable_service.publish(trans, id)

    @router.put(
        "/api/visualizations/{id}/unpublish",
        summary="Removes this item from the published list.",
    )
    def unpublish(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Removes this item from the published list and return the current sharing status."""
        return self.service.shareable_service.unpublish(trans, id)

    @router.put(
        "/api/visualizations/{id}/share_with_users",
        summary="Share this item with specific users.",
    )
    def share_with_users(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: ShareWithPayload = Body(...),
    ) -> ShareWithStatus:
        """Shares this item with specific users and return the current sharing status."""
        return self.service.shareable_service.share_with_users(trans, id, payload)

    @router.put(
        "/api/visualizations/{id}/slug",
        summary="Set a new slug for this shared item.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def set_slug(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: SetSlugPayload = Body(...),
    ):
        """Sets a new slug to access this item by URL. The new slug must be unique."""
        self.service.shareable_service.set_slug(trans, id, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get(
        "/api/visualizations/{id}",
        summary="Get a visualization by ID.",
    )
    def show(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> VisualizationShow:
        """Return the visualization."""
        return self.service.show(trans, id)

    @router.post(
        "/api/visualizations",
        summary="Create a new visualization.",
    )
    def create(
        self,
        import_id: Optional[VisualizationIdPathParam] = Body(None),
        type: str = Body(...),
        title: str = Body(...),
        dbkey: Optional[str] = Body(None),
        slug: Optional[str] = Body(None),
        annotation: Optional[str] = Body(None),
        config: Optional[dict] = Body(None),
        save: bool = Body(True),
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> VisualizationShow:
        payload = {
            "import_id": import_id,
            "type": type,
            "title": title,
            "dbkey": dbkey,
            "slug": slug,
            "annotation": annotation,
            "config": config,
            "save": save,
        }
        return self.service.create(trans, payload)

    @router.put(
        "/api/visualizations/{id}",
        summary="Update a visualization.",
    )
    def update(
        self,
        id: VisualizationIdPathParam,
        title: Optional[str] = Body(None),
        dbkey: Optional[str] = Body(None),
        deleted: Optional[bool] = Body(None),
        config: Optional[dict] = Body(None),
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> VisualizationShow:
        payload = {
            "title": title,
            "dbkey": dbkey,
            "deleted": deleted,
            "config": config,
        }
        return self.service.update(trans, id, payload)
