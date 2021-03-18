"""
API for updating Galaxy Pages
"""
import io
import logging

from fastapi import (
    Body,
    Path,
    Query,
    status,
)
from starlette.responses import StreamingResponse

from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.pages import (
    CreatePagePayload,
    PageDetails,
    PageSerializer,
    PagesManager,
    PageSummary,
    PageSummaryList,
)
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.web import (
    expose_api,
    expose_api_anonymous_and_sessionless,
    expose_api_raw_anonymous_and_sessionless
)
from . import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=['pages'])

DeletedQueryParam: bool = Query(
    default=False,
    title="Display deleted",
    description="Whether to include deleted pages in the result."
)

PageIdPathParam: EncodedDatabaseIdField = Path(
    ...,  # Required
    title="Page ID",
    description="The encoded indentifier of the Page."
)


@router.cbv
class FastAPIPages:
    manager: PagesManager = depends(PagesManager)

    @router.get(
        '/api/pages',
        summary="Lists all Pages viewable by the user.",
        response_description="A list with summary page information.",
    )
    async def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        deleted: bool = DeletedQueryParam,
    ) -> PageSummaryList:
        """Get a list with summary information of all Pages available to the user."""
        return self.manager.index(trans, deleted)

    @router.post(
        '/api/pages',
        summary="Create a page and return summary information.",
        response_description="The page summary information.",
    )
    def create(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: CreatePagePayload = Body(...),
    ) -> PageSummary:
        """Get a list with details of all Pages available to the user."""
        return self.manager.create(trans, payload)

    @router.delete(
        '/api/pages/{id}',
        summary="Marks the specific Page as deleted.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = PageIdPathParam,
    ):
        """Marks the Page with the given ID as deleted."""
        self.manager.delete(trans, id)

    @router.get(
        '/api/pages/{id}',
        summary="Return a page summary and the content of the last revision.",
        response_description="The page summary information.",
    )
    async def show(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = PageIdPathParam,
    ) -> PageDetails:
        """Return summary information about a specific Page and the content of the last revision."""
        return self.manager.show(trans, id)

    @router.get(
        '/api/pages/{id}.pdf',
        summary="Return a PDF document of the last revision of the Page.",
        response_class=StreamingResponse,
        responses={
            200: {
                "description": "PDF document with the last revision of the page.",
                "content": {"application/pdf": {}},
            },
            400: {
                "description": "PDF conversion service not available."
            }
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
        pdf_bytes = self.manager.show_pdf(trans, id)
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf")


class PagesController(BaseGalaxyAPIController):
    """
    RESTful controller for interactions with pages.
    """
    manager: PagesManager = depends(PagesManager)
    serializer: PageSerializer = depends(PageSerializer)

    @expose_api_anonymous_and_sessionless
    def index(self, trans, deleted=False, **kwd):
        """
        index( self, trans, deleted=False, **kwd )
        * GET /api/pages
            return a list of Pages viewable by the user

        :param deleted: Display deleted pages

        :rtype:     list
        :returns:   dictionaries containing summary or detailed Page information
        """
        return self.manager.index(trans, deleted)

    @expose_api
    def create(self, trans, payload, **kwd):
        """
        create( self, trans, payload, **kwd )
        * POST /api/pages
            Create a page and return dictionary containing Page summary

        :param  payload:    dictionary structure containing::
            'slug'           = The title slug for the page URL, must be unique
            'title'          = Title of the page
            'content'        = contents of the first page revision (type dependent on content_format)
            'content_format' = 'html' or 'markdown'
            'annotation'     = Annotation that will be attached to the page

        :rtype:     dict
        :returns:   Dictionary return of the Page.to_dict call
        """
        return self.manager.create(trans, CreatePagePayload(**payload))

    @expose_api
    def delete(self, trans, id, **kwd):
        """
        delete( self, trans, id, **kwd )
        * DELETE /api/pages/{id}
            Create a page and return dictionary containing Page summary

        :param  id:    ID of page to be deleted

        :rtype:     dict
        :returns:   Dictionary with 'success' or 'error' element to indicate the result of the request
        """
        self.manager.delete(trans, id)
        trans.response.status = 204

    @expose_api_anonymous_and_sessionless
    def show(self, trans, id, **kwd):
        """
        show( self, trans, id, **kwd )
        * GET /api/pages/{id}
            View a page summary and the content of the latest revision

        :param  id:    ID of page to be displayed

        :rtype:     dict
        :returns:   Dictionary return of the Page.to_dict call with the 'content' field populated by the most recent revision
        """
        return self.manager.show(trans, id)

    @expose_api_raw_anonymous_and_sessionless
    def show_pdf(self, trans, id, **kwd):
        """
        GET /api/pages/{id}.pdf

        View a page summary and the content of the latest revision as PDF.

        :param  id: ID of page to be displayed

        :rtype: dict
        :returns: Dictionary return of the Page.to_dict call with the 'content' field populated by the most recent revision
        """
        return self.manager.show_pdf(trans, id)
