"""
API for searching Galaxy Datasets
"""
import logging
from galaxy import web
from galaxy.web.base.controller import SharableItemSecurityMixin, BaseAPIController
from galaxy.model.search import GalaxySearchEngine
from galaxy.exceptions import ItemAccessibilityException

log = logging.getLogger( __name__ )

class PagesController( BaseAPIController, SharableItemSecurityMixin ):

    @web.expose_api
    def index( self, trans, deleted='False', **kwd ):
        r = trans.sa_session.query( trans.app.model.Page )
        out = []
        for row in r:
            out.append( self.encode_all_ids( trans, row.to_dict(), True) )
        return out


    @web.expose_api
    def create( self, trans, payload, **kwd ):
        return {}

    @web.expose_api
    def show( self, trans, id, deleted='False', **kwd ):
        page = trans.sa_session.query( trans.app.model.Page ).get( trans.security.decode_id( id ) )
        rval = self.encode_all_ids( trans, page.to_dict(), True) 
        rval['content'] = page.latest_revision.content
        return rval