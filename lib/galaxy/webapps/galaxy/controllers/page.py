from galaxy import (
    model,
    web,
)
from galaxy.structured_app import StructuredApp
from galaxy.webapps.base.controller import BaseUIController


class PageController(BaseUIController):

    def __init__(self, app: StructuredApp):
        super().__init__(app)

    @web.expose
    @web.require_login()
    def display(self, trans, id, **kwargs):
        id = self.decode_id(id)
        page = trans.sa_session.get(model.Page, id)
        if not page:
            raise web.httpexceptions.HTTPNotFound()
        return self.display_by_username_and_slug(trans, page.user.username, page.slug)
