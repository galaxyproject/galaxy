"""
Contains functionality needed in every web interface
"""
import os, time, logging, re, string, sys, glob, shutil, tempfile, subprocess, operator
from datetime import date, datetime, timedelta
from time import strftime
from galaxy import config, tools, web, util
from galaxy.util import inflector
from galaxy.util.hash_util import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web import error, form, url_for
from galaxy.model.orm import *
from galaxy.workflow.modules import *
from galaxy.web.framework import simplejson
from galaxy.web.form_builder import AddressField, CheckboxField, SelectField, TextArea, TextField
from galaxy.web.form_builder import WorkflowField, WorkflowMappingField, HistoryField, PasswordField, build_select_field
from galaxy.visualization.genome.visual_analytics import get_tool_def
from galaxy.security.validate_user_input import validate_publicname
from paste.httpexceptions import *
from galaxy.exceptions import *
from galaxy.model import NoConverterException, ConverterDependencyException

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
        self.sa_session = app.model.context
    def get_toolbox(self):
        """Returns the application toolbox"""
        return self.app.toolbox
    def get_class( self, class_name ):
        """ Returns the class object that a string denotes. Without this method, we'd have to do eval(<class_name>). """
        if class_name == 'History':
            item_class = self.app.model.History
        elif class_name == 'HistoryDatasetAssociation':
            item_class = self.app.model.HistoryDatasetAssociation
        elif class_name == 'Page':
            item_class = self.app.model.Page
        elif class_name == 'StoredWorkflow':
            item_class = self.app.model.StoredWorkflow
        elif class_name == 'Visualization':
            item_class = self.app.model.Visualization
        elif class_name == 'Tool':
            item_class = self.app.model.Tool
        elif class_name == 'Job':
            item_class = self.app.model.Job
        elif class_name == 'User':
            item_class = self.app.model.User
        elif class_name == 'Group':
            item_class = self.app.model.Group
        elif class_name == 'Role':
            item_class = self.app.model.Role
        elif class_name == 'Quota':
            item_class = self.app.model.Quota
        elif class_name == 'Library':
            item_class = self.app.model.Library
        elif class_name == 'LibraryFolder':
            item_class = self.app.model.LibraryFolder
        elif class_name == 'LibraryDatasetDatasetAssociation':
            item_class = self.app.model.LibraryDatasetDatasetAssociation
        elif class_name == 'LibraryDataset':
            item_class = self.app.model.LibraryDataset
        else:
            item_class = None
        return item_class
    def get_object( self, trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None ):
        """
        Convenience method to get a model object with the specified checks.
        """
        try:
            decoded_id = trans.security.decode_id( id )
        except:
            raise MessageException( "Malformed %s id ( %s ) specified, unable to decode" % ( class_name, str( id ) ), type='error' )
        try:
            item_class = self.get_class( class_name )
            assert item_class is not None
            item = trans.sa_session.query( item_class ).get( decoded_id )
            assert item is not None
        except:
            log.exception( "Invalid %s id ( %s ) specified" % ( class_name, id ) )
            raise MessageException( "Invalid %s id ( %s ) specified" % ( class_name, id ), type="error" )
        if check_ownership or check_accessible:
            self.security_check( trans, item, check_ownership, check_accessible, encoded_id )
        if deleted == True and not item.deleted:
            raise ItemDeletionException( '%s "%s" is not deleted' % ( class_name, getattr( item, 'name', id ) ), type="warning" )
        elif deleted == False and item.deleted:
            raise ItemDeletionException( '%s "%s" is deleted' % ( class_name, getattr( item, 'name', id ) ), type="warning" )
        return item
    def get_user( self, trans, id, check_ownership=False, check_accessible=False, deleted=None ):
        return self.get_object( trans, id, 'User', check_ownership=False, check_accessible=False, deleted=deleted )
    def get_group( self, trans, id, check_ownership=False, check_accessible=False, deleted=None ):
        return self.get_object( trans, id, 'Group', check_ownership=False, check_accessible=False, deleted=deleted )
    def get_role( self, trans, id, check_ownership=False, check_accessible=False, deleted=None ):
        return self.get_object( trans, id, 'Role', check_ownership=False, check_accessible=False, deleted=deleted )
    def encode_all_ids( self, trans, rval ):
        """
        Encodes all integer values in the dict rval whose keys are 'id' or end with '_id'

        It might be useful to turn this in to a decorator
        """
        if type( rval ) != dict:
            return rval
        for k, v in rval.items():
            if k == 'id' or k.endswith( '_id' ):
                try:
                    rval[k] = trans.security.encode_id( v )
                except:
                    pass # probably already encoded
        return rval

Root = BaseController

class BaseUIController( BaseController ):
    def get_object( self, trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None ):
        try:
            return BaseController.get_object( self, trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None )
        except MessageException, e:
            raise       # handled in the caller
        except:
            log.exception( "Execption in get_object check for %s %s:" % ( class_name, str( id ) ) )
            raise Exception( 'Server error retrieving %s id ( %s ).' % ( class_name, str( id ) ) )

class BaseAPIController( BaseController ):
    def get_object( self, trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None ):
        try:
            return BaseController.get_object( self, trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None )
        except ItemDeletionException, e:
            raise HTTPBadRequest( detail="Invalid %s id ( %s ) specified" % ( class_name, str( id ) ) )
        except MessageException, e:
            raise HTTPBadRequest( detail=e.err_msg )
        except Exception, e:
            log.exception( "Execption in get_object check for %s %s:" % ( class_name, str( id ) ) )
            raise HTTPInternalServerError( comment=str( e ) )
    def validate_in_users_and_groups( self, trans, payload ):
        """
        For convenience, in_users and in_groups can be encoded IDs or emails/group names in the API.
        """
        def get_id( item, model_class, column ):
            try:
                return trans.security.decode_id( item )
            except:
                pass # maybe an email/group name
            # this will raise if the item is invalid
            return trans.sa_session.query( model_class ).filter( column == item ).first().id
        new_in_users = []
        new_in_groups = []
        invalid = []
        for item in util.listify( payload.get( 'in_users', [] ) ):
            try:
                new_in_users.append( get_id( item, trans.app.model.User, trans.app.model.User.table.c.email ) )
            except:
                invalid.append( item )
        for item in util.listify( payload.get( 'in_groups', [] ) ):
            try:
                new_in_groups.append( get_id( item, trans.app.model.Group, trans.app.model.Group.table.c.name ) )
            except:
                invalid.append( item )
        if invalid:
            msg = "The following value(s) for associated users and/or groups could not be parsed: %s." % ', '.join( invalid )
            msg += "  Valid values are email addresses of users, names of groups, or IDs of both."
            raise Exception( msg )
        payload['in_users'] = map( str, new_in_users )
        payload['in_groups'] = map( str, new_in_groups )
    def not_implemented( self, trans, **kwd ):
        raise HTTPNotImplemented()

class Datatype( object ):
    """Used for storing in-memory list of datatypes currently in the datatypes registry."""
    def __init__( self, extension, dtype, type_extension, mimetype, display_in_upload ):
        self.extension = extension
        self.dtype = dtype
        self.type_extension = type_extension
        self.mimetype = mimetype
        self.display_in_upload = display_in_upload
#        
# -- Mixins for working with Galaxy objects. --
#

# Message strings returned to browser
messages = Bunch(
    PENDING = "pending",
    NO_DATA = "no data",
    NO_CHROMOSOME = "no chromosome",
    NO_CONVERTER = "no converter",
    NO_TOOL = "no tool",
    DATA = "data",
    ERROR = "error",
    OK = "ok"
)

def get_highest_priority_msg( message_list ):
    """
    Returns highest priority message from a list of messages.
    """
    return_message = None
    
    # For now, priority is: job error (dict), no converter, pending.
    for message in message_list:
        if message is not None:
            if isinstance(message, dict):
                return_message = message
                break
            elif message == messages.NO_CONVERTER:
                return_message = message
            elif return_message == None and message == messages.PENDING:
                return_message = message
    return return_message


class SharableItemSecurityMixin:
    """ Mixin for handling security for sharable items. """
    def security_check( self, trans, item, check_ownership=False, check_accessible=False ):
        """ Security checks for an item: checks if (a) user owns item or (b) item is accessible to user. """
        if check_ownership:
            # Verify ownership.
            if not trans.user:
                raise ItemOwnershipException( "Must be logged in to manage Galaxy items", type='error' )
            if item.user != trans.user:
                raise ItemOwnershipException( "%s is not owned by the current user" % item.__class__.__name__, type='error' )
        if check_accessible:
            if type( item ) in ( trans.app.model.LibraryFolder, trans.app.model.LibraryDatasetDatasetAssociation, trans.app.model.LibraryDataset ):
                if not ( trans.user_is_admin() or trans.app.security_agent.can_access_library_item( trans.get_current_user_roles(), item, trans.user ) ):
                    raise ItemAccessibilityException( "%s is not accessible to the current user" % item.__class__.__name__, type='error' )
            else:
                # Verify accessible.
                if ( item.user != trans.user ) and ( not item.importable ) and ( trans.user not in item.users_shared_with_dot_users ):
                    raise ItemAccessibilityException( "%s is not accessible to the current user" % item.__class__.__name__, type='error' )
        return item

class UsesHistoryDatasetAssociationMixin:
    """ Mixin for controllers that use HistoryDatasetAssociation objects. """
    
    def get_dataset( self, trans, dataset_id, check_ownership=True, check_accessible=False ):
        """ Get an HDA object by id. """
        # DEPRECATION: We still support unencoded ids for backward compatibility
        try:
            data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( trans.security.decode_id( dataset_id ) )
            if data is None:
                raise ValueError( 'Invalid reference dataset id: %s.' % dataset_id )
        except:
            try:
                data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( int( dataset_id ) )
            except:
                data = None
        if not data:
            raise HTTPRequestRangeNotSatisfiable( "Invalid dataset id: %s." % str( dataset_id ) )
        if check_ownership:
            # Verify ownership.
            user = trans.get_user()
            if not user:
                error( "Must be logged in to manage Galaxy items" )
            if data.history.user != user:
                error( "%s is not owned by current user" % data.__class__.__name__ )
        if check_accessible:
            current_user_roles = trans.get_current_user_roles()
            if trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset ):
                if data.state == trans.model.Dataset.states.UPLOAD:
                    return trans.show_error_message( "Please wait until this dataset finishes uploading before attempting to view it." )
            else:
                error( "You are not allowed to access this dataset" )
        return data
        
    def get_history_dataset_association( self, trans, history, dataset_id, check_ownership=True, check_accessible=False ):
        """Get a HistoryDatasetAssociation from the database by id, verifying ownership."""
        self.security_check( trans, history, check_ownership=check_ownership, check_accessible=check_accessible )
        hda = self.get_object( trans, dataset_id, 'HistoryDatasetAssociation', check_ownership=False, check_accessible=False, deleted=False )
        
        if check_accessible:
            if trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), hda.dataset ):
                if hda.state == trans.model.Dataset.states.UPLOAD:
                    error( "Please wait until this dataset finishes uploading before attempting to view it." )
            else:
                error( "You are not allowed to access this dataset" )
        return hda
        
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
        
    def check_dataset_state( self, trans, dataset ):
        """
        Returns a message if dataset is not ready to be used in visualization.
        """
        if not dataset:
            return messages.NO_DATA
        if dataset.state == trans.app.model.Job.states.ERROR:
            return messages.ERROR
        if dataset.state != trans.app.model.Job.states.OK:
            return messages.PENDING
        return None
    

class UsesLibraryMixin:
    def get_library( self, trans, id, check_ownership=False, check_accessible=True ):
        l = self.get_object( trans, id, 'Library' )
        if check_accessible and not ( trans.user_is_admin() or trans.app.security_agent.can_access_library( trans.get_current_user_roles(), l ) ):
            error( "LibraryFolder is not accessible to the current user" )
        return l

class UsesLibraryMixinItems( SharableItemSecurityMixin ):
    def get_library_folder( self, trans, id, check_ownership=False, check_accessible=True ):
        return self.get_object( trans, id, 'LibraryFolder', check_ownership=False, check_accessible=check_accessible )
    def get_library_dataset_dataset_association( self, trans, id, check_ownership=False, check_accessible=True ):
        return self.get_object( trans, id, 'LibraryDatasetDatasetAssociation', check_ownership=False, check_accessible=check_accessible )
    def get_library_dataset( self, trans, id, check_ownership=False, check_accessible=True ):
        return self.get_object( trans, id, 'LibraryDataset', check_ownership=False, check_accessible=check_accessible )

class UsesVisualizationMixin( UsesHistoryDatasetAssociationMixin, 
                              UsesLibraryMixinItems ):
    """ Mixin for controllers that use Visualization objects. """
    
    viz_types = [ "trackster", "circster" ]

    def create_visualization( self, trans, title, slug, type, dbkey, annotation=None, config={} ):
        """ Create visualiation and first revision. """
        visualization = self._create_visualization( trans, title, type, dbkey, slug, annotation )

        # Create and save first visualization revision
        revision = trans.model.VisualizationRevision( visualization=visualization, title=title, config=config, dbkey=dbkey )
        visualization.latest_revision = revision
        session = trans.sa_session
        session.add( revision )
        session.flush()

        return visualization
        
    def save_visualization( self, trans, config, type, id=None, title=None, dbkey=None, slug=None, annotation=None ):
        session = trans.sa_session
        
        # Create/get visualization. 
        if not id:
            # Create new visualization.
            vis = self._create_visualization( trans, title, type, dbkey, slug, annotation )
        else:
            decoded_id = trans.security.decode_id( id )
            vis = session.query( trans.model.Visualization ).get( decoded_id )
            
        # Create new VisualizationRevision that will be attached to the viz
        vis_rev = trans.model.VisualizationRevision()
        vis_rev.visualization = vis
        vis_rev.title = vis.title
        vis_rev.dbkey = dbkey
        
        # -- Validate config. --
        
        if vis.type == 'trackster':
            def unpack_track( track_json ):
                """ Unpack a track from its json. """
                return {
                    "dataset_id": trans.security.decode_id( track_json['dataset_id'] ),
                    "hda_ldda": track_json.get('hda_ldda', 'hda'),
                    "name": track_json['name'],
                    "track_type": track_json['track_type'],
                    "prefs": track_json['prefs'],
                    "mode": track_json['mode'],
                    "filters": track_json['filters'],
                    "tool_state": track_json['tool_state']
                }

            def unpack_collection( collection_json ):
                """ Unpack a collection from its json. """
                unpacked_drawables = []
                drawables = collection_json[ 'drawables' ]
                for drawable_json in drawables:
                    if 'track_type' in drawable_json:
                        drawable = unpack_track( drawable_json )
                    else:
                        drawable = unpack_collection( drawable_json )
                    unpacked_drawables.append( drawable )
                return {
                    "name": collection_json.get( 'name', '' ),
                    "obj_type": collection_json[ 'obj_type' ],
                    "drawables": unpacked_drawables,
                    "prefs": collection_json.get( 'prefs' , [] ),
                    "filters": collection_json.get( 'filters', None )
                }

            # TODO: unpack and validate bookmarks:
            def unpack_bookmarks( bookmarks_json ):
                return bookmarks_json

            # Unpack and validate view content.
            view_content = unpack_collection( config[ 'view' ] )
            bookmarks = unpack_bookmarks( config[ 'bookmarks' ] )
            vis_rev.config = { "view": view_content, "bookmarks": bookmarks }
            # Viewport from payload
            if 'viewport' in config:
                chrom = config['viewport']['chrom']
                start = config['viewport']['start']
                end = config['viewport']['end']
                overview = config['viewport']['overview']
                vis_rev.config[ "viewport" ] = { 'chrom': chrom, 'start': start, 'end': end, 'overview': overview }
        else:
            # Default action is to save the config as is with no validation.
            vis_rev.config = config

        vis.latest_revision = vis_rev
        session.add( vis_rev )
        session.flush()
        encoded_id = trans.security.encode_id( vis.id )
        return { "vis_id": encoded_id, "url": url_for( action=vis.type, id=encoded_id ) }

    def get_visualization( self, trans, id, check_ownership=True, check_accessible=False ):
        """ Get a Visualization from the database by id, verifying ownership. """
        # Load workflow from database
        try:
            visualization = trans.sa_session.query( trans.model.Visualization ).get( trans.security.decode_id( id ) )
        except TypeError:
            visualization = None
        if not visualization:
            error( "Visualization not found" )
        else:
            return self.security_check( trans, visualization, check_ownership, check_accessible )

    def get_visualization_config( self, trans, visualization ):
        """ Returns a visualization's configuration. Only works for trackster visualizations right now. """

        config = None
        if visualization.type == 'trackster':
            # Unpack Trackster config.
            latest_revision = visualization.latest_revision
            bookmarks = latest_revision.config.get( 'bookmarks', [] )
            
            def pack_track( track_dict ):
                dataset_id = track_dict['dataset_id']
                hda_ldda = track_dict.get('hda_ldda', 'hda')
                if hda_ldda == 'ldda':
                    # HACK: need to encode library dataset ID because get_hda_or_ldda 
                    # only works for encoded datasets.
                    dataset_id = trans.security.encode_id( dataset_id )
                dataset = self.get_hda_or_ldda( trans, hda_ldda, dataset_id )

                try:
                    prefs = track_dict['prefs']
                except KeyError:
                    prefs = {}

                track_type, _ = dataset.datatype.get_track_type()
                track_data_provider = trans.app.data_provider_registry.get_data_provider( trans, 
                                                                                          original_dataset=dataset, 
                                                                                          source='data' )
                
                return {
                    "track_type": track_type,
                    "name": track_dict['name'],
                    "hda_ldda": track_dict.get("hda_ldda", "hda"),
                    "dataset_id": trans.security.encode_id( dataset.id ),
                    "prefs": prefs,
                    "mode": track_dict.get( 'mode', 'Auto' ),
                    "filters": track_dict.get( 'filters', { 'filters' : track_data_provider.get_filters() } ),
                    "tool": get_tool_def( trans, dataset ),
                    "tool_state": track_dict.get( 'tool_state', {} )
                }
            
            def pack_collection( collection_dict ):
                drawables = []
                for drawable_dict in collection_dict[ 'drawables' ]:
                    if 'track_type' in drawable_dict:
                        drawables.append( pack_track( drawable_dict ) )
                    else:
                        drawables.append( pack_collection( drawable_dict ) )
                return {
                    'name': collection_dict.get( 'name', 'dummy' ),
                    'obj_type': collection_dict[ 'obj_type' ],
                    'drawables': drawables,
                    'prefs': collection_dict.get( 'prefs', [] ),
                    'filters': collection_dict.get( 'filters', {} )
                }
                
            def encode_dbkey( dbkey ):
                """ 
                Encodes dbkey as needed. For now, prepends user's public name 
                to custom dbkey keys.
                """
                encoded_dbkey = dbkey
                user = visualization.user
                if 'dbkeys' in user.preferences and dbkey in user.preferences[ 'dbkeys' ]:
                    encoded_dbkey = "%s:%s" % ( user.username, dbkey )
                return encoded_dbkey
                    
            # Set tracks.
            tracks = []
            if 'tracks' in latest_revision.config:
                # Legacy code.
                for track_dict in visualization.latest_revision.config[ 'tracks' ]:
                    tracks.append( pack_track( track_dict ) )
            elif 'view' in latest_revision.config:
                for drawable_dict in visualization.latest_revision.config[ 'view' ][ 'drawables' ]:
                    if 'track_type' in drawable_dict:
                        tracks.append( pack_track( drawable_dict ) )
                    else:
                        tracks.append( pack_collection( drawable_dict ) )
                
            config = {  "title": visualization.title, 
                        "vis_id": trans.security.encode_id( visualization.id ),
                        "tracks": tracks, 
                        "bookmarks": bookmarks, 
                        "chrom": "", 
                        "dbkey": encode_dbkey( visualization.dbkey ) }

            if 'viewport' in latest_revision.config:
                config['viewport'] = latest_revision.config['viewport']
        else:
            # Default action is to return config unaltered.
            latest_revision = visualization.latest_revision
            config = latest_revision.config

        return config
        
    def get_new_track_config( self, trans, dataset ):
        """
        Returns track configuration dict for a dataset.
        """
        # Get data provider.
        track_type, _ = dataset.datatype.get_track_type()
        track_data_provider = trans.app.data_provider_registry.get_data_provider( trans, original_dataset=dataset )
 
        
        if isinstance( dataset, trans.app.model.HistoryDatasetAssociation ):
            hda_ldda = "hda"
        elif isinstance( dataset, trans.app.model.LibraryDatasetDatasetAssociation ):
            hda_ldda = "ldda"
        
        # Get track definition.
        return {
            "track_type": track_type,
            "name": dataset.name,
            "hda_ldda": hda_ldda,
            "dataset_id": trans.security.encode_id( dataset.id ),
            "prefs": {},
            "filters": { 'filters' : track_data_provider.get_filters() },
            "tool": get_tool_def( trans, dataset ),
            "tool_state": {}
        }
        
    def get_hda_or_ldda( self, trans, hda_ldda, dataset_id ):
        """ Returns either HDA or LDDA for hda/ldda and id combination. """
        if hda_ldda == "hda":
            return self.get_dataset( trans, dataset_id, check_ownership=False, check_accessible=True )
        else:
            return self.get_library_dataset_dataset_association( trans, dataset_id )
        
    # -- Helper functions --
        
    def _create_visualization( self, trans, title, type, dbkey, slug=None, annotation=None ):
        """ Create visualization but not first revision. Returns Visualization object. """
        user = trans.get_user()

        # Error checking.
        title_err = slug_err = ""
        if not title:
            title_err = "visualization name is required"
        elif slug and not VALID_SLUG_RE.match( slug ):
            slug_err = "visualization identifier must consist of only lowercase letters, numbers, and the '-' character"
        elif slug and trans.sa_session.query( trans.model.Visualization ).filter_by( user=user, slug=slug, deleted=False ).first():
            slug_err = "visualization identifier must be unique"

        if title_err or slug_err:
            return { 'title_err': title_err, 'slug_err': slug_err }
            

        # Create visualization
        visualization = trans.model.Visualization( user=user, title=title, dbkey=dbkey, type=type )
        if slug:
            visualization.slug = slug
        else:
            self.create_item_slug( trans.sa_session, visualization )
        if annotation:
            annotation = sanitize_html( annotation, 'utf-8', 'text/html' )
            self.add_item_annotation( trans.sa_session, trans.user, visualization, annotation )

        session = trans.sa_session
        session.add( visualization )
        session.flush()

        return visualization

class UsesStoredWorkflowMixin( SharableItemSecurityMixin ):
    """ Mixin for controllers that use StoredWorkflow objects. """
    def get_stored_workflow( self, trans, id, check_ownership=True, check_accessible=False ):
        """ Get a StoredWorkflow from the database by id, verifying ownership. """
        # Load workflow from database
        try:
            workflow = trans.sa_session.query( trans.model.StoredWorkflow ).get( trans.security.decode_id( id ) )
        except TypeError:
            workflow = None
        if not workflow:
            error( "Workflow not found" )
        else:
            return self.security_check( trans, workflow, check_ownership, check_accessible )
    def get_stored_workflow_steps( self, trans, stored_workflow ):
        """ Restores states for a stored workflow's steps. """
        for step in stored_workflow.latest_workflow.steps:
            step.upgrade_messages = {}
            if step.type == 'tool' or step.type is None:
                # Restore the tool state for the step
                module = module_factory.from_workflow_step( trans, step )
                if module:
                    #Check if tool was upgraded
                    step.upgrade_messages = module.check_and_update_state()
                    # Any connected input needs to have value DummyDataset (these
                    # are not persisted so we need to do it every time)
                    module.add_dummy_datasets( connections=step.input_connections )
                    # Store state with the step
                    step.module = module
                    step.state = module.state
                else:
                    step.upgrade_messages = "Unknown Tool ID"
                    step.module = None
                    step.state = None
                # Error dict
                if step.tool_errors:
                    errors[step.id] = step.tool_errors
            else:
                ## Non-tool specific stuff?
                step.module = module_factory.from_workflow_step( trans, step )
                step.state = step.module.get_runtime_state()
            # Connections by input name
            step.input_connections_by_name = dict( ( conn.input_name, conn ) for conn in step.input_connections )

class UsesHistoryMixin( SharableItemSecurityMixin ):
    """ Mixin for controllers that use History objects. """
    def get_history( self, trans, id, check_ownership=True, check_accessible=False, deleted=None ):
        """Get a History from the database by id, verifying ownership."""
        history = self.get_object( trans, id, 'History', check_ownership=check_ownership, check_accessible=check_accessible, deleted=deleted )
        return self.security_check( trans, history, check_ownership, check_accessible )
    def get_history_datasets( self, trans, history, show_deleted=False, show_hidden=False, show_purged=False ):
        """ Returns history's datasets. """
        query = trans.sa_session.query( trans.model.HistoryDatasetAssociation ) \
            .filter( trans.model.HistoryDatasetAssociation.history == history ) \
            .options( eagerload( "children" ) ) \
            .join( "dataset" ) \
            .options( eagerload_all( "dataset.actions" ) ) \
            .order_by( trans.model.HistoryDatasetAssociation.hid )
        if not show_deleted:
            query = query.filter( trans.model.HistoryDatasetAssociation.deleted == False )
        if not show_purged:
            query = query.filter( trans.model.Dataset.purged == False )
        return query.all()

class UsesFormDefinitionsMixin:
    """Mixin for controllers that use Galaxy form objects."""
    def get_all_forms( self, trans, all_versions=False, filter=None, form_type='All' ):
        """
        Return all the latest forms from the form_definition_current table
        if all_versions is set to True. Otherwise return all the versions
        of all the forms from the form_definition table.
        """
        if all_versions:
            return trans.sa_session.query( trans.app.model.FormDefinition )
        if filter:
            fdc_list = trans.sa_session.query( trans.app.model.FormDefinitionCurrent ).filter_by( **filter )
        else:
            fdc_list = trans.sa_session.query( trans.app.model.FormDefinitionCurrent )
        if form_type == 'All':
            return [ fdc.latest_form for fdc in fdc_list ]
        else:
            return [ fdc.latest_form for fdc in fdc_list if fdc.latest_form.type == form_type ]
    def get_all_forms_by_type( self, trans, cntrller, form_type ):
        forms = self.get_all_forms( trans,
                                    filter=dict( deleted=False ),
                                    form_type=form_type )
        if not forms:
            message = "There are no forms on which to base the template, so create a form and then add the template."
            return trans.response.send_redirect( web.url_for( controller='forms',
                                                              action='create_form_definition',
                                                              cntrller=cntrller,
                                                              message=message,
                                                              status='done',
                                                              form_type=form_type ) )
        return forms
    @web.expose
    def add_template( self, trans, cntrller, item_type, form_type, **kwd ):
        params = util.Params( kwd )
        form_id = params.get( 'form_id', 'none' )
        message = util.restore_text( params.get( 'message', ''  ) )
        action = ''
        status = params.get( 'status', 'done' )
        forms = self.get_all_forms_by_type( trans, cntrller, form_type )
        # form_type must be one of: RUN_DETAILS_TEMPLATE, LIBRARY_INFO_TEMPLATE
        in_library = form_type == trans.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE
        in_sample_tracking = form_type == trans.model.FormDefinition.types.RUN_DETAILS_TEMPLATE
        if in_library:
            show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
            use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
            library_id = params.get( 'library_id', None )
            folder_id = params.get( 'folder_id', None )
            ldda_id = params.get( 'ldda_id', None )
            is_admin = trans.user_is_admin() and cntrller in [ 'library_admin', 'requests_admin' ]
            current_user_roles = trans.get_current_user_roles()
        elif in_sample_tracking:
            request_type_id = params.get( 'request_type_id', None )
            sample_id = params.get( 'sample_id', None )
        try:
            if in_sample_tracking:
                item, item_desc, action, id = self.get_item_and_stuff( trans,
                                                                       item_type=item_type,
                                                                       request_type_id=request_type_id,
                                                                       sample_id=sample_id )
            elif in_library:
                item, item_desc, action, id = self.get_item_and_stuff( trans,
                                                                       item_type=item_type,
                                                                       library_id=library_id,
                                                                       folder_id=folder_id,
                                                                       ldda_id=ldda_id,
                                                                       is_admin=is_admin )
            if not item:
                message = "Invalid %s id ( %s ) specified." % ( item_desc, str( id ) )
                if in_sample_tracking:
                    return trans.response.send_redirect( web.url_for( controller='request_type',
                                                                      action='browse_request_types',
                                                                      id=request_type_id,
                                                                      message=util.sanitize_text( message ),
                                                                      status='error' ) )
                if in_library:
                    return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                      action='browse_library',
                                                                      cntrller=cntrller,
                                                                      id=library_id,
                                                                      show_deleted=show_deleted,
                                                                      message=util.sanitize_text( message ),
                                                                      status='error' ) )
        except ValueError:
            # At this point, the client has already redirected, so this is just here to prevent the unnecessary traceback
            return None
        if in_library:
            # Make sure the user is authorized to do what they are trying to do.
            authorized = True
            if not ( is_admin or trans.app.security_agent.can_modify_library_item( current_user_roles, item ) ):
                authorized = False
                unauthorized = 'modify'
            if not ( is_admin or trans.app.security_agent.can_access_library_item( current_user_roles, item, trans.user ) ):
                authorized = False
                unauthorized = 'access'
            if not authorized:
                message = "You are not authorized to %s %s '%s'." % ( unauthorized, item_desc, item.name )
                return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                  action='browse_library',
                                                                  cntrller=cntrller,
                                                                  id=library_id,
                                                                  show_deleted=show_deleted,
                                                                  message=util.sanitize_text( message ),
                                                                  status='error' ) )
            # If the inheritable checkbox is checked, the param will be in the request
            inheritable = CheckboxField.is_checked( params.get( 'inheritable', '' ) )
        if params.get( 'add_template_button', False ):
            if form_id not in [ None, 'None', 'none' ]:
                form = trans.sa_session.query( trans.app.model.FormDefinition ).get( trans.security.decode_id( form_id ) )
                form_values = trans.app.model.FormValues( form, {} )
                trans.sa_session.add( form_values )
                trans.sa_session.flush()
                if item_type == 'library':
                    assoc = trans.model.LibraryInfoAssociation( item, form, form_values, inheritable=inheritable )
                elif item_type == 'folder':
                    assoc = trans.model.LibraryFolderInfoAssociation( item, form, form_values, inheritable=inheritable )
                elif item_type == 'ldda':
                    assoc = trans.model.LibraryDatasetDatasetInfoAssociation( item, form, form_values )
                elif item_type in [ 'request_type', 'sample' ]:
                    run = trans.model.Run( form, form_values )
                    trans.sa_session.add( run )
                    trans.sa_session.flush()
                    if item_type == 'request_type':
                        # Delete current RequestTypeRunAssociation, if one exists.
                        rtra = item.run_details
                        if rtra:
                            trans.sa_session.delete( rtra )
                            trans.sa_session.flush()
                        # Add the new RequestTypeRunAssociation.  Templates associated with a RequestType
                        # are automatically inherited to the samples.
                        assoc = trans.model.RequestTypeRunAssociation( item, run )
                    elif item_type == 'sample':
                        assoc = trans.model.SampleRunAssociation( item, run )
                trans.sa_session.add( assoc )
                trans.sa_session.flush()
                message = 'A template based on the form "%s" has been added to this %s.' % ( form.name, item_desc )
                new_kwd = dict( action=action,
                                cntrller=cntrller,
                                message=util.sanitize_text( message ),
                                status='done' )
                if in_sample_tracking:
                    new_kwd.update( dict( controller='request_type',
                                          request_type_id=request_type_id,
                                          sample_id=sample_id,
                                          id=id ) )
                    return trans.response.send_redirect( web.url_for( **new_kwd ) )
                elif in_library:
                    new_kwd.update( dict( controller='library_common',
                                          use_panels=use_panels,
                                          library_id=library_id,
                                          folder_id=folder_id,
                                          id=id,
                                          show_deleted=show_deleted ) )
                    return trans.response.send_redirect( web.url_for( **new_kwd ) )
            else:
                message = "Select a form on which to base the template."
                status = "error"
        form_id_select_field = self.build_form_id_select_field( trans, forms, selected_value=kwd.get( 'form_id', 'none' ) )
        try:
            decoded_form_id = trans.security.decode_id( form_id )
        except:
            decoded_form_id = None
        if decoded_form_id:
            for form in forms:
                if decoded_form_id == form.id:
                    widgets = form.get_widgets( trans.user )
                    break
        else:
            widgets = []
        new_kwd = dict( cntrller=cntrller,
                        item_name=item.name,
                        item_desc=item_desc,
                        item_type=item_type,
                        form_type=form_type,
                        widgets=widgets,
                        form_id_select_field=form_id_select_field,
                        message=message,
                        status=status )
        if in_sample_tracking:
            new_kwd.update( dict( request_type_id=request_type_id,
                                  sample_id=sample_id ) )
        elif in_library:
            new_kwd.update( dict( use_panels=use_panels,
                                  library_id=library_id,
                                  folder_id=folder_id,
                                  ldda_id=ldda_id,
                                  inheritable_checked=inheritable,
                                  show_deleted=show_deleted ) )
        return trans.fill_template( '/common/select_template.mako',
                                    **new_kwd )
    @web.expose
    def edit_template( self, trans, cntrller, item_type, form_type, **kwd ):
        # Edit the template itself, keeping existing field contents, if any.
        params = util.Params( kwd )
        form_id = params.get( 'form_id', 'none' )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        edited = util.string_as_bool( params.get( 'edited', False ) )
        action = ''
        # form_type must be one of: RUN_DETAILS_TEMPLATE, LIBRARY_INFO_TEMPLATE
        in_library = form_type == trans.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE
        in_sample_tracking = form_type == trans.model.FormDefinition.types.RUN_DETAILS_TEMPLATE
        if in_library:
            show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
            use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
            library_id = params.get( 'library_id', None )
            folder_id = params.get( 'folder_id', None )
            ldda_id = params.get( 'ldda_id', None )
            is_admin = trans.user_is_admin() and cntrller in [ 'library_admin', 'requests_admin' ]
            current_user_roles = trans.get_current_user_roles()
        elif in_sample_tracking:
            request_type_id = params.get( 'request_type_id', None )
            sample_id = params.get( 'sample_id', None )
        try:
            if in_library:
                item, item_desc, action, id = self.get_item_and_stuff( trans,
                                                                       item_type=item_type,
                                                                       library_id=library_id,
                                                                       folder_id=folder_id,
                                                                       ldda_id=ldda_id,
                                                                       is_admin=is_admin )
            elif in_sample_tracking:
                item, item_desc, action, id = self.get_item_and_stuff( trans,
                                                                       item_type=item_type,
                                                                       request_type_id=request_type_id,
                                                                       sample_id=sample_id )
        except ValueError:
            return None
        if in_library:
            if not ( is_admin or trans.app.security_agent.can_modify_library_item( current_user_roles, item ) ):
                message = "You are not authorized to modify %s '%s'." % ( item_desc, item.name )
                return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                  action='browse_library',
                                                                  cntrller=cntrller,
                                                                  id=library_id,
                                                                  show_deleted=show_deleted,
                                                                  message=util.sanitize_text( message ),
                                                                  status='error' ) )
        # An info_association must exist at this point
        if in_library:
            info_association, inherited = item.get_info_association( restrict=True )
        elif in_sample_tracking:
            # Here run_details is a RequestTypeRunAssociation
            rtra = item.run_details
            info_association = rtra.run
        template = info_association.template
        info = info_association.info
        form_values = trans.sa_session.query( trans.app.model.FormValues ).get( info.id )
        if edited:
            # The form on which the template is based has been edited, so we need to update the
            # info_association with the current form
            fdc = trans.sa_session.query( trans.app.model.FormDefinitionCurrent ).get( template.form_definition_current_id )
            info_association.template = fdc.latest_form
            trans.sa_session.add( info_association )
            trans.sa_session.flush()
            message = "The template for this %s has been updated with your changes." % item_desc
            new_kwd = dict( action=action,
                            cntrller=cntrller,
                            id=id,
                            message=util.sanitize_text( message ),
                            status='done' )
            if in_library:
                new_kwd.update( dict( controller='library_common',
                                      use_panels=use_panels,
                                      library_id=library_id,
                                      folder_id=folder_id,
                                      show_deleted=show_deleted ) )
                return trans.response.send_redirect( web.url_for( **new_kwd ) )
            elif in_sample_tracking:
                new_kwd.update( dict( controller='request_type',
                                      request_type_id=request_type_id,
                                      sample_id=sample_id ) )
                return trans.response.send_redirect( web.url_for( **new_kwd ) )
        # "template" is a FormDefinition, so since we're changing it, we need to use the latest version of it.
        vars = dict( id=trans.security.encode_id( template.form_definition_current_id ),
                     response_redirect=web.url_for( controller='request_type',
                                                    action='edit_template',
                                                    cntrller=cntrller,
                                                    item_type=item_type,
                                                    form_type=form_type,
                                                    edited=True,
                                                    **kwd ) )
        return trans.response.send_redirect( web.url_for( controller='forms', action='edit_form_definition', **vars ) )
    @web.expose
    def edit_template_info( self, trans, cntrller, item_type, form_type, **kwd ):
        # Edit the contents of the template fields without altering the template itself.
        params = util.Params( kwd )
        # form_type must be one of: RUN_DETAILS_TEMPLATE, LIBRARY_INFO_TEMPLATE
        in_library = form_type == trans.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE
        in_sample_tracking = form_type == trans.model.FormDefinition.types.RUN_DETAILS_TEMPLATE
        if in_library:
            library_id = params.get( 'library_id', None )
            folder_id = params.get( 'folder_id', None )
            ldda_id = params.get( 'ldda_id', None )
            show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
            use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
            is_admin = ( trans.user_is_admin() and cntrller == 'library_admin' )
            current_user_roles = trans.get_current_user_roles()
        elif in_sample_tracking:
            request_type_id = params.get( 'request_type_id', None )
            sample_id = params.get( 'sample_id', None )
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        try:
            if in_library:
                item, item_desc, action, id = self.get_item_and_stuff( trans,
                                                                       item_type=item_type,
                                                                       library_id=library_id,
                                                                       folder_id=folder_id,
                                                                       ldda_id=ldda_id,
                                                                       is_admin=is_admin )
            elif in_sample_tracking:
                item, item_desc, action, id = self.get_item_and_stuff( trans,
                                                                       item_type=item_type,
                                                                       request_type_id=request_type_id,
                                                                       sample_id=sample_id )
        except ValueError:
            if cntrller == 'api':
                trans.response.status = 400
                return None
            return None
        if in_library:
            if not ( is_admin or trans.app.security_agent.can_modify_library_item( current_user_roles, item ) ):
                message = "You are not authorized to modify %s '%s'." % ( item_desc, item.name )
                if cntrller == 'api':
                    trans.response.status = 400
                    return message
                return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                  action='browse_library',
                                                                  cntrller=cntrller,
                                                                  id=library_id,
                                                                  show_deleted=show_deleted,
                                                                  message=util.sanitize_text( message ),
                                                                  status='error' ) )
        # We need the type of each template field widget
        widgets = item.get_template_widgets( trans )
        # The list of widgets may include an AddressField which we need to save if it is new
        for index, widget_dict in enumerate( widgets ):
            widget = widget_dict[ 'widget' ]
            if isinstance( widget, AddressField ):
                value = util.restore_text( params.get( widget.name, '' ) )
                if value == 'new':
                    if params.get( 'edit_info_button', False ):
                        if self.field_param_values_ok( widget.name, 'AddressField', **kwd ):
                            # Save the new address
                            address = trans.app.model.UserAddress( user=trans.user )
                            self.save_widget_field( trans, address, widget.name, **kwd )
                            widget.value = str( address.id )
                        else:
                            message = 'Required fields are missing contents.'
                            if cntrller == 'api':
                                trans.response.status = 400
                                return message
                            new_kwd = dict( action=action,
                                            id=id,
                                            message=util.sanitize_text( message ),
                                            status='error' )
                            if in_library:
                                new_kwd.update( dict( controller='library_common',
                                                      cntrller=cntrller,
                                                      use_panels=use_panels,
                                                      library_id=library_id,
                                                      folder_id=folder_id,
                                                      show_deleted=show_deleted ) )
                                return trans.response.send_redirect( web.url_for( **new_kwd ) )
                            if in_sample_tracking:
                                new_kwd.update( dict( controller='request_type',
                                                      request_type_id=request_type_id,
                                                      sample_id=sample_id ) )
                                return trans.response.send_redirect( web.url_for( **new_kwd ) )
                    else:
                        # Form was submitted via refresh_on_change
                        widget.value = 'new'
                elif value == unicode( 'none' ):
                    widget.value = ''
                else:
                    widget.value = value
            elif isinstance( widget, CheckboxField ):
                # We need to check the value from kwd since util.Params would have munged the list if
                # the checkbox is checked.
                value = kwd.get( widget.name, '' )
                if CheckboxField.is_checked( value ):
                    widget.value = 'true'
            else:
                widget.value = util.restore_text( params.get( widget.name, '' ) )
        # Save updated template field contents
        field_contents = self.clean_field_contents( widgets, **kwd )
        if field_contents:
            if in_library:
                # In in a library, since information templates are inherited, the template fields can be displayed
                # on the information page for a folder or ldda when it has no info_association object.  If the user
                #  has added field contents on an inherited template via a parent's info_association, we'll need to
                # create a new form_values and info_association for the current object.  The value for the returned
                # inherited variable is not applicable at this level.
                info_association, inherited = item.get_info_association( restrict=True )
            elif in_sample_tracking:
                assoc = item.run_details
                if item_type == 'request_type' and assoc:
                    # If we're dealing with a RequestType, assoc will be a ReuqestTypeRunAssociation.
                    info_association = assoc.run
                elif item_type == 'sample' and assoc:
                    # If we're dealing with a Sample, assoc will be a SampleRunAssociation if the
                    # Sample has one.  If the Sample does not have a SampleRunAssociation, assoc will
                    # be the Sample's RequestType RequestTypeRunAssociation, in which case we need to
                    # create a SampleRunAssociation using the inherited template from the RequestType.
                    if isinstance( assoc, trans.model.RequestTypeRunAssociation ):
                        form_definition = assoc.run.template
                        new_form_values = trans.model.FormValues( form_definition, {} )
                        trans.sa_session.add( new_form_values )
                        trans.sa_session.flush()
                        new_run = trans.model.Run( form_definition, new_form_values )
                        trans.sa_session.add( new_run )
                        trans.sa_session.flush()
                        sra = trans.model.SampleRunAssociation( item, new_run )
                        trans.sa_session.add( sra )
                        trans.sa_session.flush()
                        info_association = sra.run
                    else:
                       info_association = assoc.run
                else:
                    info_association = None
            if info_association:
                template = info_association.template
                info = info_association.info
                form_values = trans.sa_session.query( trans.app.model.FormValues ).get( info.id )
                # Update existing content only if it has changed
                flush_required = False
                for field_contents_key, field_contents_value in field_contents.items():
                    if field_contents_key in form_values.content:
                        if form_values.content[ field_contents_key ] != field_contents_value:
                            flush_required = True
                            form_values.content[ field_contents_key ] = field_contents_value
                    else:
                        flush_required = True
                        form_values.content[ field_contents_key ] = field_contents_value
                if flush_required:
                    trans.sa_session.add( form_values )
                    trans.sa_session.flush()
            else:
                if in_library:
                    # Inherit the next available info_association so we can get the template
                    info_association, inherited = item.get_info_association()
                    template = info_association.template
                    # Create a new FormValues object
                    form_values = trans.app.model.FormValues( template, field_contents )
                    trans.sa_session.add( form_values )
                    trans.sa_session.flush()
                    # Create a new info_association between the current library item and form_values
                    if item_type == 'folder':
                        # A LibraryFolder is a special case because if it inherited the template from it's parent,
                        # we want to set inheritable to True for it's info_association.  This allows for the default
                        # inheritance to be False for each level in the Library hierarchy unless we're creating a new
                        # level in the hierarchy, in which case we'll inherit the "inheritable" setting from the parent
                        # level.
                        info_association = trans.app.model.LibraryFolderInfoAssociation( item, template, form_values, inheritable=inherited )
                        trans.sa_session.add( info_association )
                        trans.sa_session.flush()
                    elif item_type == 'ldda':
                        info_association = trans.app.model.LibraryDatasetDatasetInfoAssociation( item, template, form_values )
                        trans.sa_session.add( info_association )
                        trans.sa_session.flush()
        message = 'The information has been updated.'
        if cntrller == 'api':
            return 200, message
        new_kwd = dict( action=action,
                        cntrller=cntrller,
                        id=id,
                        message=util.sanitize_text( message ),
                        status='done' )
        if in_library:
            new_kwd.update( dict( controller='library_common',
                                  use_panels=use_panels,
                                  library_id=library_id,
                                  folder_id=folder_id,
                                  show_deleted=show_deleted ) )
        if in_sample_tracking:
            new_kwd.update( dict( controller='requests_common',
                                  cntrller='requests_admin',
                                  id=trans.security.encode_id( sample.id ),
                                  sample_id=sample_id ) )
        return trans.response.send_redirect( web.url_for( **new_kwd ) )
    @web.expose
    def delete_template( self, trans, cntrller, item_type, form_type, **kwd ):
        params = util.Params( kwd )
        # form_type must be one of: RUN_DETAILS_TEMPLATE, LIBRARY_INFO_TEMPLATE
        in_library = form_type == trans.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE
        in_sample_tracking = form_type == trans.model.FormDefinition.types.RUN_DETAILS_TEMPLATE
        if in_library:
            is_admin = ( trans.user_is_admin() and cntrller == 'library_admin' )
            current_user_roles = trans.get_current_user_roles()
            show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
            use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
            library_id = params.get( 'library_id', None )
            folder_id = params.get( 'folder_id', None )
            ldda_id = params.get( 'ldda_id', None )
        elif in_sample_tracking:
            request_type_id = params.get( 'request_type_id', None )
            sample_id = params.get( 'sample_id', None )
        #id = params.get( 'id', None )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        try:
            if in_library:
                item, item_desc, action, id = self.get_item_and_stuff( trans,
                                                                       item_type=item_type,
                                                                       library_id=library_id,
                                                                       folder_id=folder_id,
                                                                       ldda_id=ldda_id,
                                                                       is_admin=is_admin )
            elif in_sample_tracking:
                item, item_desc, action, id = self.get_item_and_stuff( trans,
                                                                       item_type=item_type,
                                                                       request_type_id=request_type_id,
                                                                       sample_id=sample_id )
        except ValueError:
            return None
        if in_library:
            if not ( is_admin or trans.app.security_agent.can_modify_library_item( current_user_roles, item ) ):
                message = "You are not authorized to modify %s '%s'." % ( item_desc, item.name )
                return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                  action='browse_library',
                                                                  cntrller=cntrller,
                                                                  id=library_id,
                                                                  show_deleted=show_deleted,
                                                                  message=util.sanitize_text( message ),
                                                                  status='error' ) )
        if in_library:
            info_association, inherited = item.get_info_association()
        elif in_sample_tracking:
            info_association = item.run_details
        if not info_association:
            message = "There is no template for this %s" % item_type
            status = 'error'
        else:
            if in_library:
                info_association.deleted = True
                trans.sa_session.add( info_association )
                trans.sa_session.flush()
            elif in_sample_tracking:
                trans.sa_session.delete( info_association )
                trans.sa_session.flush()
            message = 'The template for this %s has been deleted.' % item_type
            status = 'done'
        new_kwd = dict( action=action,
                        cntrller=cntrller,
                        id=id,
                        message=util.sanitize_text( message ),
                        status='done' )
        if in_library:
            new_kwd.update( dict( controller='library_common',
                                  use_panels=use_panels,
                                  library_id=library_id,
                                  folder_id=folder_id,
                                  show_deleted=show_deleted ) )
            return trans.response.send_redirect( web.url_for( **new_kwd ) )
        if in_sample_tracking:
            new_kwd.update( dict( controller='request_type',
                                  request_type_id=request_type_id,
                                  sample_id=sample_id ) )
            return trans.response.send_redirect( web.url_for( **new_kwd ) )
    def widget_fields_have_contents( self, widgets ):
        # Return True if any of the fields in widgets contain contents, widgets is a list of dictionaries that looks something like:
        # [{'widget': <galaxy.web.form_builder.TextField object at 0x10867aa10>, 'helptext': 'Field 0 help (Optional)', 'label': 'Field 0'}]
        for i, field in enumerate( widgets ):
            if ( isinstance( field[ 'widget' ], TextArea ) or isinstance( field[ 'widget' ], TextField ) ) and field[ 'widget' ].value:
                return True
            if isinstance( field[ 'widget' ], SelectField ) and field[ 'widget' ].options:
                for option_label, option_value, selected in field[ 'widget' ].options:
                    if selected:
                        return True
            if isinstance( field[ 'widget' ], CheckboxField ) and field[ 'widget' ].checked:
                return True
            if isinstance( field[ 'widget' ], WorkflowField ) and str( field[ 'widget' ].value ).lower() not in [ 'none' ]:
                return True
            if isinstance( field[ 'widget' ], WorkflowMappingField ) and str( field[ 'widget' ].value ).lower() not in [ 'none' ]:
                return True
            if isinstance( field[ 'widget' ], HistoryField ) and str( field[ 'widget' ].value ).lower() not in [ 'none' ]:
                return True
            if isinstance( field[ 'widget' ], AddressField ) and str( field[ 'widget' ].value ).lower() not in [ 'none' ]:
                return True
        return False
    def clean_field_contents( self, widgets, **kwd ):
        field_contents = {}
        for index, widget_dict in enumerate( widgets ):
            widget = widget_dict[ 'widget' ]
            value = kwd.get( widget.name, ''  )
            if isinstance( widget, CheckboxField ):
                # CheckboxField values are lists if the checkbox is checked
                value = str( widget.is_checked( value ) ).lower()
            elif isinstance( widget, AddressField ):
                # If the address was new, is has already been saved and widget.value is the new address.id
                value = widget.value
            field_contents[ widget.name ] = util.restore_text( value )
        return field_contents
    def field_param_values_ok( self, widget_name, widget_type, **kwd ):
        # Make sure required fields have contents, etc
        params = util.Params( kwd )
        if widget_type == 'AddressField':
            if not util.restore_text( params.get( '%s_short_desc' % widget_name, '' ) ) \
                or not util.restore_text( params.get( '%s_name' % widget_name, '' ) ) \
                or not util.restore_text( params.get( '%s_institution' % widget_name, '' ) ) \
                or not util.restore_text( params.get( '%s_address' % widget_name, '' ) ) \
                or not util.restore_text( params.get( '%s_city' % widget_name, '' ) ) \
                or not util.restore_text( params.get( '%s_state' % widget_name, '' ) ) \
                or not util.restore_text( params.get( '%s_postal_code' % widget_name, '' ) ) \
                or not util.restore_text( params.get( '%s_country' % widget_name, '' ) ):
                return False
        return True
    def save_widget_field( self, trans, field_obj, widget_name, **kwd ):
        # Save a form_builder field object
        params = util.Params( kwd )
        if isinstance( field_obj, trans.model.UserAddress ):
            field_obj.desc = util.restore_text( params.get( '%s_short_desc' % widget_name, '' ) )
            field_obj.name = util.restore_text( params.get( '%s_name' % widget_name, '' ) )
            field_obj.institution = util.restore_text( params.get( '%s_institution' % widget_name, '' ) )
            field_obj.address = util.restore_text( params.get( '%s_address' % widget_name, '' ) )
            field_obj.city = util.restore_text( params.get( '%s_city' % widget_name, '' ) )
            field_obj.state = util.restore_text( params.get( '%s_state' % widget_name, '' ) )
            field_obj.postal_code = util.restore_text( params.get( '%s_postal_code' % widget_name, '' ) )
            field_obj.country = util.restore_text( params.get( '%s_country' % widget_name, '' ) )
            field_obj.phone = util.restore_text( params.get( '%s_phone' % widget_name, '' ) )
            trans.sa_session.add( field_obj )
            trans.sa_session.flush()
    def get_form_values( self, trans, user, form_definition, **kwd ):
        '''
        Returns the name:value dictionary containing all the form values
        '''
        params = util.Params( kwd )
        values = {}
        for index, field in enumerate( form_definition.fields ):
            field_type = field[ 'type' ]
            field_name = field[ 'name' ]
            input_value = params.get( field_name, '' )
            if field_type == AddressField.__name__:
                input_text_value = util.restore_text( input_value )
                if input_text_value == 'new':
                    # Save this new address in the list of this user's addresses
                    user_address = trans.model.UserAddress( user=user )
                    self.save_widget_field( trans, user_address, field_name, **kwd )
                    trans.sa_session.refresh( user )
                    field_value = int( user_address.id )
                elif input_text_value in [ '', 'none', 'None', None ]:
                    field_value = ''
                else:
                    field_value = int( input_text_value )
            elif field_type == CheckboxField.__name__:
                field_value = CheckboxField.is_checked( input_value )
            elif field_type == PasswordField.__name__:
                field_value = kwd.get( field_name, '' )
            else:
                field_value = util.restore_text( input_value )
            values[ field_name ] = field_value
        return values
    def populate_widgets_from_kwd( self, trans, widgets, **kwd ):
        # A form submitted via refresh_on_change requires us to populate the widgets with the contents of
        # the form fields the user may have entered so that when the form refreshes the contents are retained.
        params = util.Params( kwd )
        populated_widgets = []
        for widget_dict in widgets:
            widget = widget_dict[ 'widget' ]
            if params.get( widget.name, False ):
                # The form included a field whose contents should be used to set the
                # value of the current widget (widget.name is the name set by the
                # user when they defined the FormDefinition).
                if isinstance( widget, AddressField ):
                    value = util.restore_text( params.get( widget.name, '' ) )
                    if value == 'none':
                        value = ''
                    widget.value = value
                    widget_dict[ 'widget' ] = widget
                    # Populate the AddressField params with the form field contents
                    widget_params_dict = {}
                    for field_name, label, help_text in widget.fields():
                        form_param_name = '%s_%s' % ( widget.name, field_name )
                        widget_params_dict[ form_param_name ] = util.restore_text( params.get( form_param_name, '' ) )
                    widget.params = widget_params_dict
                elif isinstance( widget, CheckboxField ):
                    # Check the value from kwd since util.Params would have
                    # stringify'd the list if the checkbox is checked.
                    value = kwd.get( widget.name, '' )
                    if CheckboxField.is_checked( value ):
                        widget.value = 'true'
                        widget_dict[ 'widget' ] = widget
                elif isinstance( widget, SelectField ):
                    # Ensure the selected option remains selected.
                    value = util.restore_text( params.get( widget.name, '' ) )
                    processed_options = []
                    for option_label, option_value, option_selected in widget.options:
                        selected = value == option_value
                        processed_options.append( ( option_label, option_value, selected ) )
                    widget.options = processed_options
                else:
                    widget.value = util.restore_text( params.get( widget.name, '' ) )
                    widget_dict[ 'widget' ] = widget
            populated_widgets.append( widget_dict )
        return populated_widgets
    def get_item_and_stuff( self, trans, item_type, **kwd ):
        # Return an item, description, action and an id based on the item_type.  Valid item_types are
        # library, folder, ldda, request_type, sample.
        is_admin = kwd.get( 'is_admin', False )
        #message = None
        current_user_roles = trans.get_current_user_roles()
        if item_type == 'library':
            library_id = kwd.get( 'library_id', None )
            id = library_id
            try:
                item = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
            except:
                item = None
            item_desc = 'data library'
            action = 'library_info'
        elif item_type == 'folder':
            folder_id = kwd.get( 'folder_id', None )
            id = folder_id
            try:
                item = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( folder_id ) )
            except:
                item = None
            item_desc = 'folder'
            action = 'folder_info'
        elif item_type == 'ldda':
            ldda_id = kwd.get( 'ldda_id', None )
            id = ldda_id
            try:
                item = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( ldda_id ) )
            except:
                item = None
            item_desc = 'dataset'
            action = 'ldda_edit_info'
        elif item_type == 'request_type':
            request_type_id = kwd.get( 'request_type_id', None )
            id = request_type_id
            try:
                item = trans.sa_session.query( trans.app.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
            except:
                item = None
            item_desc = 'request type'
            action = 'view_editable_request_type'
        elif item_type == 'sample':
            sample_id = kwd.get( 'sample_id', None )
            id = sample_id
            try:
                item = trans.sa_session.query( trans.app.model.Sample ).get( trans.security.decode_id( sample_id ) )
            except:
                item = None
            item_desc = 'sample'
            action = 'view_sample'
        else:
            item = None
            #message = "Invalid item type ( %s )" % str( item_type )
            item_desc = None
            action = None
            id = None
        return item, item_desc, action, id
    def build_form_id_select_field( self, trans, forms, selected_value='none' ):
        return build_select_field( trans,
                                   objs=forms,
                                   label_attr='name',
                                   select_field_name='form_id',
                                   selected_value=selected_value,
                                   refresh_on_change=True )

class SharableMixin:
    """ Mixin for a controller that manages an item that can be shared. """
    
    # -- Implemented methods. --
    
    @web.expose
    @web.require_login( "share Galaxy items" )
    def set_public_username( self, trans, id, username, **kwargs ):
        """ Set user's public username and delegate to sharing() """
        user = trans.get_user()
        message = validate_publicname( trans, username, user )
        if message:
            return trans.fill_template( '/sharing_base.mako', item=self.get_item( trans, id ), message=message, status='error' )
        user.username = username
        trans.sa_session.flush
        return self.sharing( trans, id, **kwargs )
        
    # -- Abstract methods. -- 
    
    @web.expose
    @web.require_login( "modify Galaxy items" )
    def set_slug_async( self, trans, id, new_slug ):
        """ Set item slug asynchronously. """
        raise "Unimplemented Method"

    @web.expose
    @web.require_login( "share Galaxy items" )
    def sharing( self, trans, id, **kwargs ):
        """ Handle item sharing. """
        raise "Unimplemented Method"

    @web.expose
    @web.require_login( "share Galaxy items" )
    def share( self, trans, id=None, email="", **kwd ):
        """ Handle sharing an item with a particular user. """
        raise "Unimplemented Method"

    @web.expose
    def display_by_username_and_slug( self, trans, username, slug ):
        """ Display item by username and slug. """
        raise "Unimplemented Method"
        
    @web.json
    @web.require_login( "get item name and link" )
    def get_name_and_link_async( self, trans, id=None ):
        """ Returns item's name and link. """
        raise "Unimplemented Method"
        
    @web.expose
    @web.require_login("get item content asynchronously")
    def get_item_content_async( self, trans, id ):
        """ Returns item content in HTML format. """
        raise "Unimplemented Method"
        
    # -- Helper methods. --
    
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
                # Slug taken; choose a new slug based on count. This approach can handle numerous items with the same name gracefully.
                slug = '%s-%i' % ( slug_base, count )
                count += 1
            item.slug = slug
            return True
        return False
    
    def get_item( self, trans, id ):
        """ Return item based on id. """
        raise "Unimplemented Method"

class UsesQuotaMixin( object ):
    def get_quota( self, trans, id, check_ownership=False, check_accessible=False, deleted=None ):
        return self.get_object( trans, id, 'Quota', check_ownership=False, check_accessible=False, deleted=deleted )

"""
Deprecated: `BaseController` used to be available under the name `Root`
"""
class ControllerUnavailable( Exception ):
    pass

## ---- Utility methods -------------------------------------------------------

def sort_by_attr( seq, attr ):
    """
    Sort the sequence of objects by object's attribute
    Arguments:
    seq  - the list or any sequence (including immutable one) of objects to sort.
    attr - the name of attribute to sort by
    """
    # Use the "Schwartzian transform"
    # Create the auxiliary list of tuples where every i-th tuple has form
    # (seq[i].attr, i, seq[i]) and sort it. The second item of tuple is needed not
    # only to provide stable sorting, but mainly to eliminate comparison of objects
    # (which can be expensive or prohibited) in case of equal attribute values.
    intermed = map( None, map( getattr, seq, ( attr, ) * len( seq ) ), xrange( len( seq ) ), seq )
    intermed.sort()
    return map( operator.getitem, intermed, ( -1, ) * len( intermed ) )
