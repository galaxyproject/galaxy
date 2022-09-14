from galaxy.structured_app import BasicSharedApp
from galaxy.webapps.base.controller import BaseAPIController


class BaseShedAPIController(BaseAPIController):
    def __init__(self, app: BasicSharedApp):
        super().__init__(app)
