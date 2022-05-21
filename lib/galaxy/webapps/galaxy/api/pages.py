"""
API for updating Galaxy Pages
"""
import io
import logging
from typing import Optional

from fastapi import (
    Body,
    Path,
    Query,
    Response,
    status,
)
from starlette.responses import StreamingResponse

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.fields import EncodedDatabaseIdField
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
from galaxy.webapps.galaxy.services.pages import PagesService
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["pages"])

DeletedQueryParam: bool = Query(
    default=False, title="Display deleted", description="Whether to include deleted pages in the result."
)

UserIdQueryParam: Optional[EncodedDatabaseIdField] = Query(
    default=None,
    title="Encoded user ID to restrict query to, must be own id if not an admin user",
)

PageIdPathParam: EncodedDatabaseIdField = Path(
    ..., title="Page ID", description="The encoded database identifier of the Page."  # Required
)

ShowPublishedQueryParam: bool = Query(default=True, title="Include published pages.", description="")

ShowSharedQueryParam: bool = Query(default=False, title="Include pages shared with authenticated user.", description="")


SortByQueryParam: PageSortByEnum = Query(
    default=PageSortByEnum.update_time,
    title="Sort attribute",
    description="Sort page index by this specified attribute on the page model",
)


SortDescQueryParam: bool = Query(
    default=True,
    title="Sort Descending",
    description="Sort in descending order?",
)

LimitQueryParam: int = Query(default=100, lt=1000, title="Limit number of queries.")

OffsetQueryParam: int = Query(
    default=0,
    title="Number of pages to skip in sorted query (to enable pagination).",
)


@router.cbv
class FastAPIPages:
    service: PagesService = depends(PagesService)

    @router.get(
        "/api/pages",
        summary="Lists all Pages viewable by the user.",
        response_description="A list with summary page information.",
    )
    async def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        deleted: bool = DeletedQueryParam,
        user_id: Optional[EncodedDatabaseIdField] = UserIdQueryParam,
        show_published: bool = ShowPublishedQueryParam,
        show_shared: bool = ShowSharedQueryParam,
        sort_by: PageSortByEnum = SortByQueryParam,
        sort_desc: bool = SortDescQueryParam,
        limit: int = LimitQueryParam,
        offset: int = OffsetQueryParam,
    ) -> PageSummaryList:
        """Get a list with summary information of all Pages available to the user."""
        payload = PageIndexQueryPayload(
            deleted=deleted,
            user_id=user_id,
            show_published=show_published,
            show_shared=show_shared,
            sort_by=sort_by,
            sort_desc=sort_desc,
            limit=limit,
            offset=offset,
        )
        return self.service.index(trans, payload)

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
        """Get a list with details of all Pages available to the user."""
        return self.service.create(trans, payload)

    @router.delete(
        "/api/pages/{id}",
        summary="Marks the specific Page as deleted.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = PageIdPathParam,
    ):
        """Marks the Page with the given ID as deleted."""
        self.service.delete(trans, id)
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
    async def show_pdf(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = PageIdPathParam,
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
    async def prepare_pdf(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = PageIdPathParam,
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
    async def show(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = PageIdPathParam,
    ) -> PageDetails:
        """Return summary information about a specific Page and the content of the last revision."""
        return self.service.show(trans, id)

    @router.get(
        "/api/pages/{id}/sharing",
        summary="Get the current sharing status of the given Page.",
    )
    def sharing(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = PageIdPathParam,
    ) -> SharingStatus:
        """Return the sharing status of the item."""
        return self.service.shareable_service.sharing(trans, id)

    @router.put(
        "/api/pages/{id}/enable_link_access",
        summary="Makes this item accessible by a URL link.",
    )
    def enable_link_access(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = PageIdPathParam,
    ) -> SharingStatus:
        """Makes this item accessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.enable_link_access(trans, id)

    @router.put(
        "/api/pages/{id}/disable_link_access",
        summary="Makes this item inaccessible by a URL link.",
    )
    def disable_link_access(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = PageIdPathParam,
    ) -> SharingStatus:
        """Makes this item inaccessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.disable_link_access(trans, id)

    @router.put(
        "/api/pages/{id}/publish",
        summary="Makes this item public and accessible by a URL link.",
    )
    def publish(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = PageIdPathParam,
    ) -> SharingStatus:
        """Makes this item publicly available by a URL link and return the current sharing status."""
        return self.service.shareable_service.publish(trans, id)

    @router.put(
        "/api/pages/{id}/unpublish",
        summary="Removes this item from the published list.",
    )
    def unpublish(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = PageIdPathParam,
    ) -> SharingStatus:
        """Removes this item from the published list and return the current sharing status."""
        return self.service.shareable_service.unpublish(trans, id)

    @router.put(
        "/api/pages/{id}/share_with_users",
        summary="Share this item with specific users.",
    )
    def share_with_users(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = PageIdPathParam,
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
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = PageIdPathParam,
        payload: SetSlugPayload = Body(...),
    ):
        """Sets a new slug to access this item by URL. The new slug must be unique."""
        self.service.shareable_service.set_slug(trans, id, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
