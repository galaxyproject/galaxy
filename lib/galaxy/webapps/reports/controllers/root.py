import sys, os, operator, string, shutil, re, socket, urllib, time
from galaxy import web
from cgi import escape, FieldStorage
from galaxy.webapps.reports.base.controller import *
import logging
log = logging.getLogger( __name__ )

class Report( BaseController ):
    @web.expose
    def index( self, trans, **kwd ):
        return trans.fill_template( 'index.mako' )
    @web.expose
    def masthead( self, trans ):
        brand = trans.app.config.get( "brand", "" )
        if brand:
            brand ="<span class='brand'>/%s</span>" % brand
        wiki_url = trans.app.config.get( "wiki_url", "http://bitbucket.org/galaxy/galaxy-central/wiki/Home" )
        bugs_email = trans.app.config.get( "bugs_email", "mailto:galaxy-bugs@bx.psu.edu"  )
        screencasts_url = trans.app.config.get( "screencasts_url", "http://galaxycast.org" )
        return trans.fill_template( "masthead.mako",
                                    brand=brand,
                                    wiki_url=wiki_url,
                                    bugs_email=bugs_email,
                                    screencasts_url=screencasts_url )
