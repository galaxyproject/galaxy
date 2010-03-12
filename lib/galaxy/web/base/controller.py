"""
Contains functionality needed in every web interface
"""

import os, time, logging, re

# Pieces of Galaxy to make global in every controller
from galaxy import config, tools, web, model, util
from galaxy.web import error, form, url_for
from galaxy.model.orm import *
from galaxy.workflow.modules import *

from Cheetah.Template import Template

log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

# RE that tests for valid slug.
VALID_SLUG_RE = re.compile( "^[a-z0-9\-]+$" )
    
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
        elif class_name == 'Visualization':
            item_class = model.Visualization
        else:
            item_class = None
        return item_class
        
Root = BaseController

class UsesAnnotations:
    """ Mixin for getting and setting item annotations. """
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
        elif item.__class__ == model.Page:
            annotation_assoc = annotation_assoc.filter_by( page=item )
        elif item.__class__ == model.Visualization:
            annotation_assoc = annotation_assoc.filter_by( visualization=item )
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

class SharableItemSecurity:
    """ Mixin for handling security for sharable items. """

    def security_check( self, user, item, check_ownership=False, check_accessible=False ):
        """ Security checks for an item: checks if (a) user owns item or (b) item is accessible to user. """
        if check_ownership:
            # Verify ownership.
            if not user:
                error( "Must be logged in to manage Galaxy items" )
            if item.user != user:
                error( "%s is not owned by current user" % item.__class__.__name__ )
        if check_accessible:
            # Verify accessible.
            if ( item.user != user ) and ( not item.importable ) and ( user not in item.users_shared_with_dot_users ):
                error( "%s is not accessible to current user" % item.__class__.__name__ )
        return item
        
class UsesHistoryDatasetAssociation:
    """ Mixin for controllers that use HistoryDatasetAssociation objects. """
    
    def get_dataset( self, trans, dataset_id, check_accessible=True ):
        """ Get an HDA object by id. """
        # DEPRECATION: We still support unencoded ids for backward compatibility
        try:
            dataset_id = int( dataset_id )
        except ValueError:
            dataset_id = trans.security.decode_id( dataset_id )
        data = trans.sa_session.query( model.HistoryDatasetAssociation ).get( dataset_id )
        if not data:
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable( "Invalid dataset id: %s." % str( dataset_id ) )
        if check_accessible:
            current_user_roles = trans.get_current_user_roles()
            if trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset ):
                if data.state == trans.model.Dataset.states.UPLOAD:
                    return trans.show_error_message( "Please wait until this dataset finishes uploading before attempting to view it." )
            else:
                error( "You are not allowed to access this dataset" )
        return data
        
    def get_data( self, dataset, preview=True ):
        """ Gets a dataset's data. """
        # Get data from file, truncating if necessary.
        truncated = False
        dataset_data = None
        if os.path.exists( dataset.file_name ):
            max_peek_size = 1000000 # 1 MB
            if preview and os.stat( dataset.file_name ).st_size > max_peek_size:
                dataset_data = open( dataset.file_name ).read(max_peek_size)
                truncated = True
            else:
                dataset_data = open( dataset.file_name ).read(max_peek_size)
                truncated = False
        return truncated, dataset_data
        
class UsesVisualization( SharableItemSecurity ):
    """ Mixin for controllers that use Visualization objects. """

    def get_visualization( self, trans, id, check_ownership=True, check_accessible=False ):
        """ Get a Visualization from the database by id, verifying ownership. """
        # Load workflow from database
        id = trans.security.decode_id( id )
        visualization = trans.sa_session.query( model.Visualization ).get( id )
        if not visualization:
            error( "Visualization not found" )
        else:
            return self.security_check( trans.get_user(), stored, check_ownership, check_accessible )
        
class UsesStoredWorkflow( SharableItemSecurity ):
    """ Mixin for controllers that use StoredWorkflow objects. """
    
    def get_stored_workflow( self, trans, id, check_ownership=True, check_accessible=False ):
        """ Get a StoredWorkflow from the database by id, verifying ownership. """
        # Load workflow from database
        id = trans.security.decode_id( id )
        stored = trans.sa_session.query( model.StoredWorkflow ).get( id )
        if not stored:
            error( "Workflow not found" )
        else:
            return self.security_check( trans.get_user(), stored, check_ownership, check_accessible )
            
    def get_stored_workflow_steps( self, trans, stored_workflow ):
        """ Restores states for a stored workflow's steps. """
        for step in stored_workflow.latest_workflow.steps:
            if step.type == 'tool' or step.type is None:
                # Restore the tool state for the step
                module = module_factory.from_workflow_step( trans, step )
                # Any connected input needs to have value DummyDataset (these
                # are not persisted so we need to do it every time)
                module.add_dummy_datasets( connections=step.input_connections )                  
                # Store state with the step
                step.module = module
                step.state = module.state
                # Error dict
                if step.tool_errors:
                    errors[step.id] = step.tool_errors
            else:
                ## Non-tool specific stuff?
                step.module = module_factory.from_workflow_step( trans, step )
                step.state = step.module.get_runtime_state()
            # Connections by input name
            step.input_connections_by_name = dict( ( conn.input_name, conn ) for conn in step.input_connections )

class UsesHistory( SharableItemSecurity ):
    """ Mixin for controllers that use History objects. """
    
    def get_history( self, trans, id, check_ownership=True, check_accessible=False ):
        """Get a History from the database by id, verifying ownership."""
        # Load history from database
        id = trans.security.decode_id( id )
        history = trans.sa_session.query( model.History ).get( id )
        if not history:
            err+msg( "History not found" )
        else:
            return self.security_check( trans.get_user(), history, check_ownership, check_accessible )
        
    def get_history_datasets( self, trans, history, show_deleted=False ):
        """ Returns history's datasets. """
        query = trans.sa_session.query( model.HistoryDatasetAssociation ) \
            .filter( model.HistoryDatasetAssociation.history == history ) \
            .options( eagerload( "children" ) ) \
            .join( "dataset" ).filter( model.Dataset.purged == False ) \
            .options( eagerload_all( "dataset.actions" ) ) \
            .order_by( model.HistoryDatasetAssociation.hid )
        if not show_deleted:
            query = query.filter( model.HistoryDatasetAssociation.deleted == False )
        return query.all()
            
class Sharable:
    """ Mixin for a controller that manages an item that can be shared. """
    
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
    @web.require_login( "modify Galaxy items" )
    def set_slug_async( self, trans, id, new_slug ):
        """ Set item slug asynchronously. """
        pass
            
    @web.expose
    @web.require_login( "share Galaxy items" )
    def sharing( self, trans, id, **kwargs ):
        """ Handle item sharing. """
        pass
    
    @web.expose
    @web.require_login( "share Galaxy items" )
    def share( self, trans, id=None, email="", **kwd ):
        """ Handle sharing an item with a particular user. """
        pass
    
    @web.expose
    def display_by_username_and_slug( self, trans, username, slug ):
        """ Display item by username and slug. """
        pass
        
    @web.expose
    @web.json
    @web.require_login( "get item name and link" )
    def get_name_and_link_async( self, trans, id=None ):
        """ Returns item's name and link. """
        pass
        
    @web.expose
    @web.require_login("get item content asynchronously")
    def get_item_content_async( self, trans, id ):
        """ Returns item content in HTML format. """
        pass
        
    # Helper methods.
    
    def _make_item_accessible( self, sa_session, item ):
        """ Makes item accessible--viewable and importable--and sets item's slug. Does not flush/commit changes, however. Item must have name, user, importable, and slug attributes. """
        item.importable = True
        self.create_item_slug( sa_session, item )

    def create_item_slug( self, sa_session, item ):
        """ Create item slug. Slug is unique among user's importable items for item's class. Returns true if item's slug was set; false otherwise. """
        if item.slug is None or item.slug == "":
            # Item can have either a name or a title.
            if hasattr( item, 'name' ):
                item_name = item.name
            elif hasattr( item, 'title' ):
                item_name = item.title
            # Replace whitespace with '-'
            slug_base = re.sub( "\s+", "-", item_name.lower() )
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