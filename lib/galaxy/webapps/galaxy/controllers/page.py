from galaxy import (
    model,
    web,
)
from galaxy.managers.hdas import HDAManager
from galaxy.managers.histories import (
    HistoryManager,
    HistorySerializer,
)
from galaxy.managers.pages import (
    get_page as get_page_,
    page_exists,
    PageManager,
)
from galaxy.managers.sharable import SlugBuilder
from galaxy.managers.workflows import WorkflowsManager
from galaxy.model.base import transaction
from galaxy.model.db.user import get_user_by_username
from galaxy.model.item_attrs import UsesItemRatings
from galaxy.schema.schema import CreatePagePayload
from galaxy.structured_app import StructuredApp
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web import error
from galaxy.webapps.base.controller import (
    BaseUIController,
    SharableMixin,
    UsesStoredWorkflowMixin,
    UsesVisualizationMixin,
)
from galaxy.webapps.galaxy.api import depends


# Adapted from the _BaseHTMLProcessor class of https://github.com/kurtmckee/feedparser
class PageController(BaseUIController, SharableMixin, UsesStoredWorkflowMixin, UsesVisualizationMixin, UsesItemRatings):
    page_manager: PageManager = depends(PageManager)
    history_manager: HistoryManager = depends(HistoryManager)
    history_serializer: HistorySerializer = depends(HistorySerializer)
    hda_manager: HDAManager = depends(HDAManager)
    workflow_manager: WorkflowsManager = depends(WorkflowsManager)
    slug_builder: SlugBuilder = depends(SlugBuilder)

    def __init__(self, app: StructuredApp):
        super().__init__(app)

    @web.expose_api
    @web.require_login("create pages")
    def create(self, trans, payload=None, **kwd):
        """
        Create a new page.
        """
        if trans.request.method == "GET":
            form_title = "Create new Page"
            title = ""
            slug = ""
            content = ""
            content_hide = True
            if "invocation_id" in kwd:
                invocation_id = kwd.get("invocation_id")
                form_title = f"{form_title} from Invocation Report"
                slug = f"invocation-report-{invocation_id}"
                invocation_report = self.workflow_manager.get_invocation_report(
                    trans, trans.security.decode_id(invocation_id)
                )
                title = invocation_report.get("title")
                content = invocation_report.get("markdown")
                content_hide = False
            return {
                "title": form_title,
                "inputs": [
                    {
                        "name": "title",
                        "label": "Name",
                        "value": title,
                    },
                    {
                        "name": "slug",
                        "label": "Identifier",
                        "help": "A unique identifier that will be used for public links to this page. This field can only contain lowercase letters, numbers, and dashes (-).",
                        "value": slug,
                    },
                    {
                        "name": "annotation",
                        "label": "Annotation",
                        "help": "A description of the page. The annotation is shown alongside published pages.",
                    },
                    {
                        "name": "content_format",
                        "label": "Content Format",
                        "value": "markdown",
                        "hidden": True,
                    },
                    {
                        "name": "content",
                        "label": "Content",
                        "area": True,
                        "value": content,
                        "hidden": content_hide,
                    },
                ],
            }
        else:
            page = self.page_manager.create_page(trans, CreatePagePayload(**payload))
            return {"message": f"Page '{page.title}' successfully created.", "status": "success"}

    @web.legacy_expose_api
    @web.require_login("edit pages")
    def edit(self, trans, payload=None, **kwd):
        """
        Edit a page's attributes.
        """
        id = kwd.get("id")
        if not id:
            return self.message_exception(trans, "No page id received for editing.")
        decoded_id = self.decode_id(id)
        user = trans.get_user()
        p = trans.sa_session.get(model.Page, decoded_id)
        p = self.security_check(trans, p, check_ownership=True)
        if trans.request.method == "GET":
            if p.slug is None:
                self.slug_builder.create_item_slug(trans.sa_session, p)
            return {
                "title": "Edit page attributes",
                "inputs": [
                    {"name": "title", "label": "Name", "value": p.title},
                    {
                        "name": "slug",
                        "label": "Identifier",
                        "value": p.slug,
                        "help": "A unique identifier that will be used for public links to this page. This field can only contain lowercase letters, numbers, and dashes (-).",
                    },
                    {
                        "name": "annotation",
                        "label": "Annotation",
                        "value": self.get_item_annotation_str(trans.sa_session, user, p),
                        "help": "A description of the page. The annotation is shown alongside published pages.",
                    },
                ],
            }
        else:
            p_title = payload.get("title")
            p_slug = payload.get("slug")
            p_annotation = payload.get("annotation")
            if not p_title:
                return self.message_exception(trans, "Please provide a page name is required.")
            elif not p_slug:
                return self.message_exception(trans, "Please provide a unique identifier.")
            elif not self._is_valid_slug(p_slug):
                return self.message_exception(
                    trans, "Page identifier can only contain lowercase letters, numbers, and dashes (-)."
                )
            elif p_slug != p.slug and page_exists(trans.sa_session, p.user, p_slug):
                return self.message_exception(trans, "Page id must be unique.")
            else:
                p.title = p_title
                p.slug = p_slug
                if p_annotation:
                    p_annotation = sanitize_html(p_annotation)
                    self.add_item_annotation(trans.sa_session, user, p, p_annotation)
                trans.sa_session.add(p)
                with transaction(trans.sa_session):
                    trans.sa_session.commit()
            return {"message": f"Attributes of '{p.title}' successfully saved.", "status": "success"}

    @web.expose
    @web.require_login()
    def display(self, trans, id, **kwargs):
        id = self.decode_id(id)
        page = trans.sa_session.get(model.Page, id)
        if not page:
            raise web.httpexceptions.HTTPNotFound()
        return self.display_by_username_and_slug(trans, page.user.username, page.slug)

    def _display_by_username_and_slug(self, trans, username, slug, **kwargs):
        """Display page based on a username and slug."""

        # Get page.
        user = get_user_by_username(trans.sa_session, username)
        page = get_page_(trans.sa_session, user, slug)
        if page is None:
            raise web.httpexceptions.HTTPNotFound()

        # Security check raises error if user cannot access page.
        self.security_check(trans, page, False, True)

        # Encode page identifier.
        page_id = trans.security.encode_id(page.id)

        # Redirect to client.
        return trans.response.send_redirect(
            web.url_for(
                controller="published",
                action="page",
                id=page_id,
            )
        )

    def get_page(self, trans, id, check_ownership=True, check_accessible=False):
        """Get a page from the database by id."""
        # Load history from database
        id = self.decode_id(id)
        page = trans.sa_session.get(model.Page, id)
        if not page:
            error("Page not found")
        else:
            return self.security_check(trans, page, check_ownership, check_accessible)
