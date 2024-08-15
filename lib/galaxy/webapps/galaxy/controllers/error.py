from galaxy.webapps.base.controller import (
    BaseUIController,
    web,
)


class Error(BaseUIController):
    @web.expose
    def index(self, trans):
        raise Exception("Fake error")
