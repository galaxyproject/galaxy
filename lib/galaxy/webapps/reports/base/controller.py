"""Contains functionality needed in every webapp interface"""
import os, time, logging
# Pieces of Galaxy to make global in every controller
from galaxy import web, util
from Cheetah.Template import Template

log = logging.getLogger( __name__ )

class BaseController( object ):
    """Base class for Galaxy webapp application controllers."""
    def __init__( self, app ):
        """Initialize an interface for application 'app'"""
        self.app = app