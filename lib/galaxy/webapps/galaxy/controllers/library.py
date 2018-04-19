import logging

from galaxy import web
from galaxy.web.base.controller import BaseUIController


log = logging.getLogger(__name__)


class Library(BaseUIController):

    @web.expose
    def list(self, trans, **kwd):
        # define app configuration for generic mako template
        app = {
            'jscript'       : "library"
        }
        return trans.fill_template('galaxy.panels.mako',
                                   config={
                                       'title': 'Data Libraries',
                                       'app': app,
                                       'bundle': 'extended'})
