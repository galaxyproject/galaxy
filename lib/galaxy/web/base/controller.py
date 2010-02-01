"""
Contains functionality needed in every web interface
"""

import os, time, logging, re

# Pieces of Galaxy to make global in every controller
from galaxy import config, tools, web, model, util
from galaxy.web import error, form, url_for
from galaxy.model.orm import *
from galaxy.web.framework.helpers import grids
from galaxy.util.odict import odict

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
        if item.user.username and item.slug:
            return dict( action='display_by_username_and_slug', username=item.user.username, slug=item.slug )
        elif not item.user.username:
            # TODO: provide link to set username.
            return None
        elif not item.user.slug:
            # TODO: provide link to set slg
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
        
    def get_class( self, class_name ):
        """ Returns the class object that a string denotes. Without this method, we'd have to do eval(<class_name>). """
        if class_name == 'History':
            item_class = model.History
        elif class_name == 'HistoryDatasetAssociation':
            item_class = model.HistoryDatasetAssociation
        elif class_name == 'Page':
            item_class = model.Page
        elif class_name == 'StoredWorkflow':
            item_class = model.StoredWorkflow
        else:
            item_class = None
        return item_class
        
    def get_item_annotation_str( self, db_session, user, item ):
        """ Returns a user's annotation string for an item. """
        annotation_obj = self.get_item_annotation_obj( db_session, user, item )
        if annotation_obj:
            return annotation_obj.annotation
        return None
        
    def get_item_annotation_obj( self, db_session, user, item ):
        """ Returns a user's annotation object for an item. """
        # Get annotation association. TODO: we could replace this eval() with a long if/else stmt, but this is more general without sacrificing
        try:
            annotation_assoc_class = eval( "model.%sAnnotationAssociation" % item.__class__.__name__ )
        except:
            # Item doesn't have an annotation association class and cannot be annotated.
            return False
        
        # Get annotation association object.
        annotation_assoc = db_session.query( annotation_assoc_class ).filter_by( user=user )
        if item.__class__ == model.History:
            annotation_assoc = annotation_assoc.filter_by( history=item )
        elif item.__class__ == model.HistoryDatasetAssociation:
            annotation_assoc = annotation_assoc.filter_by( hda=item )
        elif item.__class__ == model.StoredWorkflow:
            annotation_assoc = annotation_assoc.filter_by( stored_workflow=item )
        elif item.__class__ == model.WorkflowStep:
            annotation_assoc = annotation_assoc.filter_by( workflow_step=item )
        return annotation_assoc.first()
        
    def add_item_annotation( self, trans, item, annotation ):
        """ Add or update an item's annotation; a user can only have a single annotation for an item. """

        # Get/create annotation association object.
        annotation_assoc = self.get_item_annotation_obj( trans.sa_session, trans.get_user(), item )
        if not annotation_assoc:
            # Create association.
            # TODO: we could replace this eval() with a long if/else stmt, but this is more general without sacrificing
            try:
                annotation_assoc_class = eval( "model.%sAnnotationAssociation" % item.__class__.__name__ )
            except:
                # Item doesn't have an annotation association class and cannot be annotated.
                return False
            annotation_assoc = annotation_assoc_class()
            item.annotations.append( annotation_assoc )
            annotation_assoc.user = trans.get_user()

        # Set annotation.
        annotation_assoc.annotation = annotation
        return True
        
Root = BaseController

class SharingStatusColumn( grids.GridColumn ):
    """ Grid column to indicate sharing status. """
    def get_value( self, trans, grid, item ):
        # Delete items cannot be shared.
        if item.deleted:
            return ""
            
        # Build a list of sharing for this item.
        sharing_statuses = []
        if item.users_shared_with:
            sharing_statuses.append( "Shared" )
        if item.importable:
            sharing_statuses.append( "Accessible" )
        if item.published:
            sharing_statuses.append( "Published" )
        return ", ".join( sharing_statuses )
        
    def get_link( self, trans, grid, item ):
        if not item.deleted and ( item.users_shared_with or item.importable or item.published ):
            return dict( operation="share or publish", id=item.id )
        return None
        
    def filter( self, db_session, user, query, column_filter ):
        """ Modify query to filter histories by sharing status. """
        if column_filter == "All":
            pass
        elif column_filter:
            if column_filter == "private":
                query = query.filter( self.model_class.users_shared_with == None )
                query = query.filter( self.model_class.importable == False )
            elif column_filter == "shared":
                query = query.filter( self.model_class.users_shared_with != None )
            elif column_filter == "accessible":
                query = query.filter( self.model_class.importable == True )
            elif column_filter == "published":
                query = query.filter( self.model_class.published == True )
        return query
        
    def get_accepted_filters( self ):
        """ Returns a list of accepted filters for this column. """
        accepted_filter_labels_and_vals = odict()
        accepted_filter_labels_and_vals["private"] = "private"
        accepted_filter_labels_and_vals["shared"] = "shared"
        accepted_filter_labels_and_vals["accessible"] = "accessible"
        accepted_filter_labels_and_vals["published"] = "published"
        accepted_filter_labels_and_vals["all"] = "All"
        accepted_filters = []
        for label, val in accepted_filter_labels_and_vals.items():
            args = { self.key: val }
            accepted_filters.append( grids.GridColumnFilter( label, args) )
        return accepted_filters
            
class Sharable:
    """ Mixin for a controller that manages and item that can be shared. """
    
    # Implemented methods.
    @web.expose
    @web.require_login( "share Galaxy items" )
    def set_public_username( self, trans, id, username, **kwargs ):
        """ Set user's public username and delegate to sharing() """
        trans.get_user().username = username
        trans.sa_session.flush
        return self.sharing( trans, id, **kwargs )
            
    # Abstract methods.
            
    @web.expose
    @web.require_login( "share Galaxy items" )
    def sharing( self, trans, id, **kwargs ):
        """ Handle item sharing. """
        pass
    
    @web.expose
    def display_by_username_and_slug( self, trans, username, slug ):
        """ Display item by username and slug. """
        pass
        
    # Helper methods.
    
    def _make_item_accessible( self, sa_session, item ):
        """ Makes item accessible--viewable and importable--and sets item's slug. Does not flush/commit changes, however. Item must have name, user, importable, and slug attributes. """
        item.importable = True
        self.set_item_slug( sa_session, item )

    def set_item_slug( self, sa_session, item ):
        """ Set item slug. Slug is unique among user's importable items for item's class. Returns true if item's slug was set; false otherwise. """
        if item.slug is None or item.slug == "":
            # Replace whitespace with '-'
            slug_base = re.sub( "\s+", "-", item.name.lower() )
            # Remove all non-alphanumeric characters.
            slug_base = re.sub( "[^a-zA-Z0-9\-]", "", slug_base )
            # Remove trailing '-'.
            if slug_base.endswith('-'):
                slug_base = slug_base[:-1]
                
            # Make sure that slug is not taken; if it is, add a number to it.
            slug = slug_base
            count = 1
            while sa_session.query( item.__class__ ).filter_by( user=item.user, slug=slug, importable=True ).count() != 0:
                # Slug taken; choose a new slug based on count. This approach can handle numerous histories with the same name gracefully.
                slug = '%s-%i' % ( slug_base, count )
                count += 1
            item.slug = slug
            return True
            
        return False
        
"""
Deprecated: `BaseController` used to be available under the name `Root`
"""

class ControllerUnavailable( Exception ):
    pass