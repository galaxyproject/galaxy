"""
Contains functionality needed in every web interface

"""

import os, time, logging
from galaxy import tools, web

from Cheetah.Template import Template

log = logging.getLogger( __name__ )

class Root( object ):
    """
    All interfaces should inherit from this class
    """

    def __init__( self, app ):
        """Initialize an interface for application 'app'"""
        self.app = app

    def get_toolbox(self):
        """Returns the application toolbox"""
        return self.app.toolbox
