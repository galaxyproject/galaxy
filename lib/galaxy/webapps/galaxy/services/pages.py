import logging

from galaxy import (
    exceptions,
    model,
)
from galaxy.managers import base
from galaxy.managers.markdown_util import internal_galaxy_markdown_to_pdf
from galaxy.managers.pages import (
    PageManager,
    PageSerializer,
)
from galaxy.schema import PdfDocumentType
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import (
    CreatePagePayload,
    PageContentFormat,
    PageDetails,
    PageSummary,
    PageSummaryList,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.galaxy.services.base import ServiceBase
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
    ):
        super().__init__(security)
        self.manager = manager
        self.serializer = serializer
        self.shareable_service = ShareableService(self.manager, self.serializer)

    def index(self, trans, deleted: bool = False) -> PageSummaryList:
        """Return a list of Pages viewable by the user

        :param deleted: Display deleted pages

        :rtype:     list
        :returns:   dictionaries containing summary or detailed Page information
        """
        out = []

        if trans.user_is_admin:
            r = trans.sa_session.query(model.Page)
            if not deleted:
                r = r.filter_by(deleted=False)
            for row in r:
                out.append(trans.security.encode_all_ids(row.to_dict(), recursive=True))
        else:
            # Transaction user's pages (if any)
            user = trans.user
            r = trans.sa_session.query(model.Page).filter_by(user=user)
            if not deleted:
                r = r.filter_by(deleted=False)
            for row in r:
                out.append(trans.security.encode_all_ids(row.to_dict(), recursive=True))
            # Published pages from other users
            r = trans.sa_session.query(model.Page).filter(model.Page.user != user).filter_by(published=True)
            if not deleted:
                r = r.filter_by(deleted=False)
            for row in r:
                out.append(trans.security.encode_all_ids(row.to_dict(), recursive=True))

        return PageSummaryList.parse_obj(out)

    def create(self, trans, payload: CreatePagePayload) -> PageSummary:
        """
        Create a page and return Page summary
        """
        page = self.manager.create(trans, payload.dict())
        rval = trans.security.encode_all_ids(page.to_dict(), recursive=True)
        rval["content"] = page.latest_revision.content
        self.manager.rewrite_content_for_export(trans, rval)
        return PageSummary.parse_obj(rval)

    def delete(self, trans, id: EncodedDatabaseIdField):
        """
        Deletes a page (or marks it as deleted)
        """
        page = base.get_object(trans, id, "Page", check_ownership=True)

        # Mark a page as deleted
        page.deleted = True
        trans.sa_session.flush()

    def show(self, trans, id: EncodedDatabaseIdField) -> PageDetails:
        """View a page summary and the content of the latest revision

        :param  id:    ID of page to be displayed

        :rtype:     dict
        :returns:   Dictionary return of the Page.to_dict call with the 'content' field populated by the most recent revision
        """
        page = base.get_object(trans, id, "Page", check_ownership=False, check_accessible=True)
        rval = trans.security.encode_all_ids(page.to_dict(), recursive=True)
        rval["content"] = page.latest_revision.content
        rval["content_format"] = page.latest_revision.content_format
        self.manager.rewrite_content_for_export(trans, rval)
        return PageDetails.parse_obj(rval)

    def show_pdf(self, trans, id: EncodedDatabaseIdField):
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
