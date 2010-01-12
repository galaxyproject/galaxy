"""
Contains functionality needed in every web interface
"""

import os, time, logging, re

# Pieces of Galaxy to make global in every controller
from galaxy import config, tools, web, model, util
from galaxy.web import error, form, url_for
from galaxy.model.orm import *
from galaxy.web.framework.helpers import grids

from Cheetah.Template import Template

log = logging.getLogger( __name__ )

# Useful columns in many grids used by controllers.

# Item's user/owner.
class OwnerColumn( grids.TextColumn ):
    def get_value( self, trans, grid, item ):
        return item.user.username

# Item's public URL based on username and slug.
class PublicURLColumn( grids.TextColumn ):
    def get_link( self, trans, grid, item ):
        if item.user.username:
            return dict( action='display_by_username_and_slug', username=item.user.username, slug=item.slug )
        else:
            return None
        
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
            
    def make_item_importable( self, sa_session, item ):
        """ Makes item importable and sets item's slug. Does not flush/commit changes, however. Item must have name, user, importable, and slug attributes. """
        item.importable = True

        # Set history slug. Slug must be unique among user's importable pages.
        slug_base = re.sub( "\s+", "-", item.name.lower() )
        slug = slug_base
        count = 1
        while sa_session.query( item.__class__ ).filter_by( user=item.user, slug=slug, importable=True ).count() != 0:
            # Slug taken; choose a new slug based on count. This approach can handle numerous histories with the same name gracefully.
            slug = '%s-%i' % ( slug_base, count )
            count += 1
        item.slug = slug
        
Root = BaseController
"""
Deprecated: `BaseController` used to be available under the name `Root`
"""

class ControllerUnavailable( Exception ):
    pass