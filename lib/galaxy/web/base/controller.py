"""
Contains functionality needed in every web interface
"""

import os, time, logging

# Pieces of Galaxy to make global in every controller
from galaxy import config, tools, web, model, util
from galaxy.web import error, form, url_for
from galaxy.model.orm import *

from Cheetah.Template import Template

log = logging.getLogger( __name__ )

class BaseController( object ):
    """
    Base class for Galaxy web application controllers.
    """

    def __init__( self, app ):
        """Initialize an interface for application 'app'"""
        self.app = app

    def get_toolbox(self):
        """Returns the application toolbox"""
        return self.app.toolbox
        
    def get_history( self, trans, id, check_ownership=True ):
        """Get a History from the database by id, verifying ownership."""
        # Load history from database
        id = trans.security.decode_id( id )
        history = trans.sa_session.query( model.History ).get( id )
        if not history:
            err+msg( "History not found" )
        if check_ownership:
            # Verify ownership
            user = trans.get_user()
            if not user:
                error( "Must be logged in to manage histories" )
            if history.user != user:
                error( "History is not owned by current user" )
        return history
        
Root = BaseController
"""
Deprecated: `BaseController` used to be available under the name `Root`
"""

class ControllerUnavailable( Exception ):
    pass