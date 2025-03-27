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
    page_exists,
    PageManager,
)
from galaxy.managers.sharable import SlugBuilder
from galaxy.managers.workflows import WorkflowsManager
from galaxy.model.db.user import get_user_by_username
from galaxy.model.item_attrs import UsesItemRatings
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

    def get_page(self, trans, id, check_ownership=True, check_accessible=False):
        """Get a page from the database by id."""
        # Load history from database
        id = self.decode_id(id)
        page = trans.sa_session.get(model.Page, id)
        if not page:
            error("Page not found")
        else:
            return self.security_check(trans, page, check_ownership, check_accessible)
