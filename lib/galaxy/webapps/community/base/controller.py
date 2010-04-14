"""Contains functionality needed in every webapp interface"""
import os, time, logging
# Pieces of Galaxy to make global in every controller
from galaxy import config, tools, web, util
from galaxy.web import error, form, url_for
from galaxy.webapps.community import model
from galaxy.model.orm import *

from Cheetah.Template import Template

log = logging.getLogger( __name__ )

class BaseController( object ):
    """Base class for Galaxy webapp application controllers."""
    def __init__( self, app ):
        """Initialize an interface for application 'app'"""
        self.app = app
    def get_class( self, class_name ):
        """ Returns the class object that a string denotes. Without this method, we'd have to do eval(<class_name>). """
        if class_name == 'Tool':
            item_class = model.Tool
        else:
            item_class = None
        return item_class