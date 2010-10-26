"""
API operations on a sample tracking system.
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *
from galaxy.util.bunch import Bunch

log = logging.getLogger( __name__ )

class SamplesController( BaseController ):

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/requests/{encoded_request_id}/samples
        Displays a collection (list) of sample of a sequencing request.
        """
        try:
            request_id = trans.security.decode_id( kwd[ 'request_id' ] )
        except TypeError:
            trans.response.status = 400
            return "Malformed  request id ( %s ) specified, unable to decode." % str( encoded_request_id )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( request_id )
        except:
            request = None
        if not request or not ( trans.user_is_admin() or request.user.id == trans.user.id ):
            trans.response.status = 400
            return "Invalid request id ( %s ) specified." % str( request_id )
        rval = []
        for sample in request.samples:
            item = sample.get_api_value()
            item['url'] = url_for( 'samples', 
                                   request_id=trans.security.encode_id( request_id ), 
                                   id=trans.security.encode_id( sample.id ) )
            item['id'] = trans.security.encode_id( item['id'] )
            rval.append( item )
        return rval

    
