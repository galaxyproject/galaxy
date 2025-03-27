"""
API for updating Galaxy Pages
"""

import io
import logging
from typing import Optional

from fastapi import (
    Body,
    Query,
    Response,
    status,
)
from starlette.responses import StreamingResponse

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    AsyncFile,
    CreatePagePayload,
    PageDetails,
    PageIndexQueryPayload,
    PageSortByEnum,
    PageSummary,
    PageSummaryList,
    SetSlugPayload,
    ShareWithPayload,
    ShareWithStatus,
    SharingStatus,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    IndexQueryTag,
    Router,
    search_query_param,
)
from galaxy.webapps.galaxy.api.common import PageIdPathParam
from galaxy.webapps.galaxy.services.pages import PagesService

log = logging.getLogger(__name__)

router = Router(tags=["pages"])

DeletedQueryParam: bool = Query(
    default=False, title="Display deleted", description="Whether to include deleted pages in the result."
)

UserIdQueryParam: Optional[DecodedDatabaseIdField] = Query(
    default=None,
    title="Encoded user ID to restrict query to, must be own id if not an admin user",
)

ShowOwnQueryParam: bool = Query(default=True, title="Show pages owned by user.", description="")

ShowPublishedQueryParam: bool = Query(default=True, title="Include published pages.", description="")

ShowSharedQueryParam: bool = Query(default=False, title="Include pages shared with authenticated user.", description="")


SortByQueryParam: PageSortByEnum = Query(
    default="update_time",
    title="Sort attribute",
    description="Sort page index by this specified attribute on the page model",
)


SortDescQueryParam: bool = Query(
    default=False,
    title="Sort Descending",
    description="Sort in descending order?",
)

LimitQueryParam: int = Query(default=100, ge=1, lt=1000, title="Limit number of queries.")

OffsetQueryParam: int = Query(
    default=0,
    ge=0,
    title="Number of pages to skip in sorted query (to enable pagination).",
)

query_tags = [
    IndexQueryTag("title", "The page's title."),
    IndexQueryTag("slug", "The page's slug.", "s"),
    IndexQueryTag("tag", "The page's tags.", "t"),
    IndexQueryTag("user", "The page's owner's username.", "u"),
]

SearchQueryParam: Optional[str] = search_query_param(
    model_name="Page",
    tags=query_tags,
    free_text_fields=["title", "slug", "tag", "user"],
)


@router.cbv
class FastAPIPages:
    service: PagesService = depends(PagesService)

    @router.get(
        "/api/pages",
        summary="Lists all Pages viewable by the user.",
        response_description="A list with summary page information.",
    )
    def index(
        self,
        response: Response,
        trans: ProvidesUserContext = DependsOnTrans,
        deleted: bool = DeletedQueryParam,
        limit: int = LimitQueryParam,
        offset: int = OffsetQueryParam,
        search: Optional[str] = SearchQueryParam,
        show_own: bool = ShowOwnQueryParam,
        show_published: bool = ShowPublishedQueryParam,
        show_shared: bool = ShowSharedQueryParam,
        sort_by: PageSortByEnum = SortByQueryParam,
        sort_desc: bool = SortDescQueryParam,
        user_id: Optional[DecodedDatabaseIdField] = UserIdQueryParam,
    ) -> PageSummaryList:
        """Get a list with summary information of all Pages available to the user."""
        payload = PageIndexQueryPayload.model_construct(
            deleted=deleted,
            limit=limit,
            offset=offset,
            search=search,
            show_own=show_own,
            show_published=show_published,
            show_shared=show_shared,
            sort_by=sort_by,
            sort_desc=sort_desc,
            user_id=user_id,
        )
        pages, total_matches = self.service.index(trans, payload, include_total_count=True)
        response.headers["total_matches"] = str(total_matches)
        return pages

    @router.post(
        "/api/pages",
        summary="Create a page and return summary information.",
        response_description="The page summary information.",
    )
    def create(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: CreatePagePayload = Body(...),
    ) -> PageSummary:
        """Creates a new Page."""
        return self.service.create(trans, payload)

    @router.delete(
        "/api/pages/{id}",
        summary="Marks the specific Page as deleted.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete(
        self,
        id: PageIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Marks the Page with the given ID as deleted."""
        self.service.delete(trans, id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.put(
        "/api/pages/{id}/undelete",
        summary="Undelete the specific Page.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def undelete(
        self,
        id: PageIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Marks the Page with the given ID as undeleted."""
        self.service.undelete(trans, id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get(
        "/api/pages/{id}.pdf",
        summary="Return a PDF document of the last revision of the Page.",
        response_class=StreamingResponse,
        responses={
            200: {
                "description": "PDF document with the last revision of the page.",
                "content": {"application/pdf": {}},
            },
            501: {"description": "PDF conversion service not available."},
        },
    )
    def show_pdf(
        self,
        id: PageIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Return a PDF document of the last revision of the Page.

        This feature may not be available in this Galaxy.
        """
        pdf_bytes = self.service.show_pdf(trans, id)
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf")

    @router.post(
        "/api/pages/{id}/prepare_download",
        summary="Return a PDF document of the last revision of the Page.",
        responses={
            200: {
                "description": "Short term storage reference for async monitoring of this download.",
            },
            501: {"description": "PDF conversion service not available."},
        },
    )
    def prepare_pdf(
        self,
        id: PageIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> AsyncFile:
        """Return a STS download link for this page to be downloaded as a PDF.

        This feature may not be available in this Galaxy.
        """
        return self.service.prepare_pdf(trans, id)

    @router.get(
        "/api/pages/{id}",
        summary="Return a page summary and the content of the last revision.",
        response_description="The page summary information.",
    )
    def show(
        self,
        id: PageIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> PageDetails:
        """Return summary information about a specific Page and the content of the last revision."""
        return self.service.show(trans, id)

    @router.get(
        "/api/pages/{id}/sharing",
        summary="Get the current sharing status of the given Page.",
    )
    def sharing(
        self,
        id: PageIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Return the sharing status of the item."""
        return self.service.shareable_service.sharing(trans, id)

    @router.put(
        "/api/pages/{id}/enable_link_access",
        summary="Makes this item accessible by a URL link.",
    )
    def enable_link_access(
        self,
        id: PageIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item accessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.enable_link_access(trans, id)

    @router.put(
        "/api/pages/{id}/disable_link_access",
        summary="Makes this item inaccessible by a URL link.",
    )
    def disable_link_access(
        self,
        id: PageIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item inaccessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.disable_link_access(trans, id)

    @router.put(
        "/api/pages/{id}/publish",
        summary="Makes this item public and accessible by a URL link.",
    )
    def publish(
        self,
        id: PageIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item publicly available by a URL link and return the current sharing status."""
        return self.service.shareable_service.publish(trans, id)

    @router.put(
        "/api/pages/{id}/unpublish",
        summary="Removes this item from the published list.",
    )
    def unpublish(
        self,
        id: PageIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Removes this item from the published list and return the current sharing status."""
        return self.service.shareable_service.unpublish(trans, id)

    @router.put(
        "/api/pages/{id}/share_with_users",
        summary="Share this item with specific users.",
    )
    def share_with_users(
        self,
        id: PageIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: ShareWithPayload = Body(...),
    ) -> ShareWithStatus:
        """Shares this item with specific users and return the current sharing status."""
        return self.service.shareable_service.share_with_users(trans, id, payload)

    @router.put(
        "/api/pages/{id}/slug",
        summary="Set a new slug for this shared item.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def set_slug(
        self,
        id: PageIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: SetSlugPayload = Body(...),
    ):
        """Sets a new slug to access this item by URL. The new slug must be unique."""
        self.service.shareable_service.set_slug(trans, id, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
