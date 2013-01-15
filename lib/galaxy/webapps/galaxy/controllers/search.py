
"""
Contains the main interface in the Universe class
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *
from galaxy.model.item_attrs import UsesAnnotations

log = logging.getLogger( __name__ )

class SearchController( BaseUIController ):
    @web.expose
    def index(self, trans):
        return trans.fill_template( "search/index.mako")