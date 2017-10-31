import logging

from markupsafe import escape
from sqlalchemy import and_, false, not_, or_

from galaxy import model, util
from galaxy import web
from galaxy.web.base.controller import BaseUIController
from galaxy.web.framework.helpers import grids
from library_common import get_comptypes, lucene_search, whoosh_search


log = logging.getLogger(__name__)


class Library(BaseUIController):

    library_list_grid = LibraryListGrid()

    @web.expose
    def list(self, trans, **kwd):
        # define app configuration for generic mako template
        app = {
            'jscript'       : "galaxy.library"
        }
        return trans.fill_template('galaxy.panels.mako',
                                   config={
                                       'title': 'Data Libraries',
                                       'app': app})
