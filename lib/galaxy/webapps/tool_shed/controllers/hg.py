import logging

from mercurial.hgweb.hgwebdir_mod import hgwebdir
from mercurial.hgweb.request import wsgiapplication

from galaxy import web
from galaxy.web.base.controller import BaseUIController

log = logging.getLogger(__name__)


class HgController( BaseUIController ):
    @web.expose
    def handle_request( self, trans, **kwd ):
        # The os command that results in this method being called will look something like:
        # hg clone http://test@127.0.0.1:9009/repos/test/convert_characters1
        hgweb_config = trans.app.hgweb_config_manager.hgweb_config

        def make_web_app():
            hgwebapp = hgwebdir( hgweb_config )
            return hgwebapp
        wsgi_app = wsgiapplication( make_web_app )
        return wsgi_app
