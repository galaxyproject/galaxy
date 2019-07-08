from galaxy import web
from galaxy.webapps.base.controller import BaseAPIController


class GenomesController(BaseAPIController):

    @web.expose_api_raw
    def index(self, trans, **kwd):
        return trans.webapp.build_apispec().to_yaml()