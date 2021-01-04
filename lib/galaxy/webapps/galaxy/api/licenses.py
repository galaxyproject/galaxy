from galaxy.managers.licenses import LicensesManager
from galaxy.web import expose_api_anonymous_and_sessionless
from galaxy.webapps.base.controller import BaseAPIController


class LicensesController(BaseAPIController):

    def __init__(self, app):
        self.licenses_manager = LicensesManager()

    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwd):
        """
        GET /api/licenses

        Return an index of known licenses.
        """
        return self.licenses_manager.index()

    @expose_api_anonymous_and_sessionless
    def get(self, trans, id, **kwd):
        """
        GET /api/licenses/<license_id>

        Return license metadata by URI or SPDX id.
        """
        license_id = id
        return self.licenses_manager.get(license_id)
