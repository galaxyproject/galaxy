from galaxy import web
from galaxy.managers.pages import get_page
from galaxy.model.db.user import get_user_by_username
from galaxy.structured_app import StructuredApp
from galaxy.webapps.base.controller import (
    BaseUIController,
    SharableItemSecurityMixin,
    SharableMixin,
)


class PageController(BaseUIController, SharableMixin, SharableItemSecurityMixin):

    def __init__(self, app: StructuredApp):
        super().__init__(app)

    def _display_by_username_and_slug(self, trans, username, slug, **kwargs):
        """Display page based on a username and slug."""

        # Get page.
        user = get_user_by_username(trans.sa_session, username)
        page = get_page(trans.sa_session, user, slug)
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
