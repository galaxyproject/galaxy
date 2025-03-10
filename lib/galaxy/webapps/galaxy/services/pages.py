import logging
from typing import (
    Tuple,
    Union,
)

from galaxy import exceptions
from galaxy.celery.tasks import prepare_pdf_download
from galaxy.managers import base
from galaxy.managers.markdown_util import (
    internal_galaxy_markdown_to_pdf,
    to_basic_markdown,
)
from galaxy.managers.pages import (
    PageManager,
    PageSerializer,
)
from galaxy.schema import PdfDocumentType
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    AsyncFile,
    CreatePagePayload,
    PageContentFormat,
    PageDetails,
    PageIndexQueryPayload,
    PageSummary,
    PageSummaryList,
)
from galaxy.schema.tasks import GeneratePdfDownload
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.short_term_storage import ShortTermStorageAllocator
from galaxy.webapps.galaxy.services.base import (
    async_task_summary,
    ensure_celery_tasks_enabled,
    ServiceBase,
)
from galaxy.webapps.galaxy.services.notifications import NotificationService
from galaxy.webapps.galaxy.services.sharable import ShareableService

log = logging.getLogger(__name__)


class PagesService(ServiceBase):
    """Common interface/service logic for interactions with pages in the context of the API.

    Provides the logic of the actions invoked by API controllers and uses type definitions
    and pydantic models to declare its parameters and return types.
    """

    def __init__(
        self,
        security: IdEncodingHelper,
        manager: PageManager,
        serializer: PageSerializer,
        short_term_storage_allocator: ShortTermStorageAllocator,
        notification_service: NotificationService,
    ):
        super().__init__(security)
        self.manager = manager
        self.serializer = serializer
        self.shareable_service = ShareableService(self.manager, self.serializer, notification_service)
        self.short_term_storage_allocator = short_term_storage_allocator

    def index(
        self, trans, payload: PageIndexQueryPayload, include_total_count: bool = False
    ) -> Tuple[PageSummaryList, Union[int, None]]:
        """Return a list of Pages viewable by the user

        :rtype:     list
        :returns:   dictionaries containing summary or detailed Page information
        """
        if not trans.user_is_admin:
            user_id = trans.user and trans.user.id
            if payload.user_id and payload.user_id != user_id:
                raise exceptions.AdminRequiredException("Only admins can index the pages of others")

        pages, total_matches = self.manager.index_query(trans, payload, include_total_count)
        return (
            PageSummaryList(root=[p.to_dict() for p in pages]),
            total_matches,
        )

    def create(self, trans, payload: CreatePagePayload) -> PageSummary:
        """
        Create a page and return Page summary
        """
        page = self.manager.create_page(trans, payload)
        rval = page.to_dict()
        rval["content"] = page.latest_revision.content
        self.manager.rewrite_content_for_export(trans, rval)
        return PageSummary(**rval)

    def delete(self, trans, id: DecodedDatabaseIdField):
        """
        Mark page as deleted

        :param  id:    ID of the page to be deleted
        """
        page = base.get_object(trans, id, "Page", check_ownership=True)

        page.deleted = True
        trans.sa_session.commit()

    def undelete(self, trans, id: DecodedDatabaseIdField):
        """
        Undelete page

        :param  id:    ID of the page to be undeleted
        """
        page = base.get_object(trans, id, "Page", check_ownership=True)

        page.deleted = False
        trans.sa_session.commit()

    def show(self, trans, id: DecodedDatabaseIdField) -> PageDetails:
        """View a page summary and the content of the latest revision

        :param  id:    ID of page to be displayed

        :rtype:     dict
        :returns:   Dictionary return of the Page.to_dict call with the 'content' field populated by the most recent revision
        """
        page = base.get_object(trans, id, "Page", check_ownership=False, check_accessible=True)
        rval = page.to_dict()
        rval["content"] = page.latest_revision.content
        rval["content_format"] = page.latest_revision.content_format
        self.manager.rewrite_content_for_export(trans, rval)
        return PageDetails(**rval)

    def show_pdf(self, trans, id: DecodedDatabaseIdField):
        """
        View a page summary and the content of the latest revision as PDF.

        :param  id: ID of page to be displayed

        :rtype: dict
        :returns: Dictionary return of the Page.to_dict call with the 'content' field populated by the most recent revision
        """
        page = base.get_object(trans, id, "Page", check_ownership=False, check_accessible=True)
        if page.latest_revision.content_format != PageContentFormat.markdown.value:
            raise exceptions.RequestParameterInvalidException("PDF export only allowed for Markdown based pages")
        internal_galaxy_markdown = page.latest_revision.content
        return internal_galaxy_markdown_to_pdf(trans, internal_galaxy_markdown, PdfDocumentType.page)

    def prepare_pdf(self, trans, id: DecodedDatabaseIdField) -> AsyncFile:
        ensure_celery_tasks_enabled(trans.app.config)
        page = base.get_object(trans, id, "Page", check_ownership=False, check_accessible=True)
        short_term_storage_target = self.short_term_storage_allocator.new_target(
            f"{page.title}.pdf",
            "application/pdf",
        )
        request_id = short_term_storage_target.request_id
        internal_galaxy_markdown = page.latest_revision.content
        basic_markdown = to_basic_markdown(trans, internal_galaxy_markdown)
        pdf_download_request = GeneratePdfDownload(
            basic_markdown=basic_markdown,
            document_type=PdfDocumentType.page,
            short_term_storage_request_id=request_id,
        )
        result = prepare_pdf_download.delay(request=pdf_download_request, task_user_id=getattr(trans.user, "id", None))
        return AsyncFile(storage_request_id=request_id, task=async_task_summary(result))
