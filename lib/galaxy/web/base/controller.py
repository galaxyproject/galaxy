"""
Contains functionality needed in every web interface
"""

import os, time, logging

# Pieces of Galaxy to make global in every controller
from galaxy import config, tools, web, model, util
from galaxy.web import error, url_for

from Cheetah.Template import Template

log = logging.getLogger( __name__ )

class BaseController( object ):
    """
    Base class for Galaxy web application controllers.
    """
    
    beta = False

    def __init__( self, app ):
        """Initialize an interface for application 'app'"""
        self.app = app

    def get_toolbox(self):
        """Returns the application toolbox"""
        return self.app.toolbox
        
Root = BaseController
"""
Deprecated: `BaseController` used to be available under the name `Root`
"""