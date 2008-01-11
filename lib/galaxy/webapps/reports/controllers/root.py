import sys, sets, string, shutil
import re, socket

from galaxy import web

from cgi import escape, FieldStorage
import urllib

import operator, os
from galaxy.webapps.reports.base.controller import *

import logging, sets, time
log = logging.getLogger( __name__ )

class Report( BaseController ):
    @web.expose
    def index( self, trans, **kwd ):
        return trans.fill_template( 'index.tmpl' )

    @web.expose
    def masthead( self, trans ):
        brand = trans.app.config.get( "brand", None )
        wiki_url = trans.app.config.get( "wiki_url", None )
        bugs_email = trans.app.config.get( "bugs_email", None )
        blog_url = trans.app.config.get( "blog_url", None )
        screencasts_url = trans.app.config.get( "screencasts_url", None )
        return trans.fill_template( "masthead.tmpl", brand=brand, wiki_url=wiki_url, blog_url=blog_url,bugs_email=bugs_email, screencasts_url=screencasts_url )

    @web.expose
    def main_frame( self, trans ):
        return trans.fill_template( "main_frame.tmpl" )

