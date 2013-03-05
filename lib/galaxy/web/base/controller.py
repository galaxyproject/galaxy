"""
Contains functionality needed in every web interface
"""
import logging
import operator
import os
import re
import pkg_resources
pkg_resources.require("SQLAlchemy >= 0.4")

from sqlalchemy import func, and_, select
from paste.httpexceptions import HTTPBadRequest, HTTPInternalServerError, HTTPNotImplemented, HTTPRequestRangeNotSatisfiable

from galaxy import util, web
from galaxy.datatypes.interval import ChromatinInteractions
from galaxy.exceptions import ItemAccessibilityException, ItemDeletionException, ItemOwnershipException, MessageException
from galaxy.security.validate_user_input import validate_publicname
from galaxy.util.sanitize_html import sanitize_html
from galaxy.visualization.genome.visual_analytics import get_tool_def
from galaxy.web import error, url_for
from galaxy.web.form_builder import AddressField, CheckboxField, SelectField, TextArea, TextField
from galaxy.web.form_builder import build_select_field, HistoryField, PasswordField, WorkflowField, WorkflowMappingField
from galaxy.workflow.modules import module_factory
from galaxy.model.orm import eagerload, eagerload_all
from galaxy.datatypes.data import Text


log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

def _is_valid_slug( slug ):
    """ Returns true if slug is valid. """

    VALID_SLUG_RE = re.compile( "^[a-z0-9\-]+$" )
    return VALID_SLUG_RE.match( slug )

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
        elif class_name == 'ToolShedRepository':
            item_class = self.app.model.ToolShedRepository
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
            self.security_check( trans, item, check_ownership, check_accessible, id )
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
        except MessageException:
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
    
    def get_dataset( self, trans, dataset_id, check_ownership=True, check_accessible=False, check_state=True ):
        """ Get an HDA object by id. """
        # DEPRECATION: We still support unencoded ids for backward compatibility
        try:
            # encoded id?
            dataset_id = trans.security.decode_id( dataset_id )

        except ( AttributeError, TypeError ):
            # unencoded id
            dataset_id = int( dataset_id )

        try:
            data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( int( dataset_id ) )
        except:
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

            if not trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset ):
                error( "You are not allowed to access this dataset" )

            if check_state and data.state == trans.model.Dataset.states.UPLOAD:
                    return trans.show_error_message( "Please wait until this dataset finishes uploading "
                                                   + "before attempting to view it." )
        return data
        
    def get_history_dataset_association( self, trans, history, dataset_id,
                                         check_ownership=True, check_accessible=False, check_state=False ):
        """Get a HistoryDatasetAssociation from the database by id, verifying ownership."""
        self.security_check( trans, history, check_ownership=check_ownership, check_accessible=check_accessible )
        hda = self.get_object( trans, dataset_id, 'HistoryDatasetAssociation', check_ownership=False, check_accessible=False, deleted=False )
        
        if check_accessible:
            if not trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), hda.dataset ):
                error( "You are not allowed to access this dataset" )

                if check_state and hda.state == trans.model.Dataset.states.UPLOAD:
                    error( "Please wait until this dataset finishes uploading before attempting to view it." )
        return hda
        
    def get_data( self, dataset, preview=True ):
        """ Gets a dataset's data. """

        # Get data from file, truncating if necessary.
        truncated = False
        dataset_data = None
        if os.path.exists( dataset.file_name ):
            if isinstance( dataset.datatype, Text ):
                max_peek_size = 1000000 # 1 MB
                if preview and os.stat( dataset.file_name ).st_size > max_peek_size:
                    dataset_data = open( dataset.file_name ).read(max_peek_size)
                    truncated = True
                else:
                    dataset_data = open( dataset.file_name ).read(max_peek_size)
                    truncated = False
            else:
                # For now, cannot get data from non-text datasets.
                dataset_data = None
        return truncated, dataset_data
        
    def check_dataset_state( self, trans, dataset ):
        """
        Returns a message if dataset is not ready to be used in visualization.
        """
        if not dataset:
            return dataset.conversion_messages.NO_DATA
        if dataset.state == trans.app.model.Job.states.ERROR:
            return dataset.conversion_messages.ERROR
        if dataset.state != trans.app.model.Job.states.OK:
            return dataset.conversion_messages.PENDING
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
    
    viz_types = [ "trackster" ]

    def create_visualization( self, trans, type, title="Untitled Genome Vis", slug=None, dbkey=None, annotation=None, config={}, save=True ):
        """ Create visualiation and first revision. """
        visualization = self._create_visualization( trans, title, type, dbkey, slug, annotation, save )

        # Create and save first visualization revision
        revision = trans.model.VisualizationRevision( visualization=visualization, title=title, config=config, dbkey=dbkey )
        visualization.latest_revision = revision

        if save:
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
        return { "vis_id": encoded_id, "url": url_for( controller='visualization', action=vis.type, id=encoded_id ) }

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
        if visualization.type in [ 'trackster', 'genome' ]:
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
        
    def _create_visualization( self, trans, title, type, dbkey=None, slug=None, annotation=None, save=True ):
        """ Create visualization but not first revision. Returns Visualization object. """
        user = trans.get_user()

        # Error checking.
        title_err = slug_err = ""
        if not title:
            title_err = "visualization name is required"
        elif slug and not _is_valid_slug( slug ):
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

        if save:
            session = trans.sa_session
            session.add( visualization )
            session.flush()

        return visualization

    def _get_genome_data( self, trans, dataset, dbkey=None ):
        """
        Returns genome-wide data for dataset if available; if not, message is returned.
        """
        rval = None

        # Get data sources.
        data_sources = dataset.get_datasources( trans )
        query_dbkey = dataset.dbkey
        if query_dbkey == "?":
            query_dbkey = dbkey
        chroms_info = self.app.genomes.chroms( trans, dbkey=query_dbkey )

        # If there are no messages (messages indicate data is not ready/available), get data.
        messages_list = [ data_source_dict[ 'message' ] for data_source_dict in data_sources.values() ]
        message = self._get_highest_priority_msg( messages_list )
        if message:
            rval = message
        else:
            # HACK: chromatin interactions tracks use data as source.
            source = 'index'
            if isinstance( dataset.datatype, ChromatinInteractions ):
                source = 'data'

            data_provider = trans.app.data_provider_registry.get_data_provider( trans, 
                                                                                original_dataset=dataset, 
                                                                                source=source )
            # HACK: pass in additional params which are used for only some 
            # types of data providers; level, cutoffs used for summary tree, 
            # num_samples for BBI, and interchromosomal used for chromatin interactions.
            rval = data_provider.get_genome_data( chroms_info, 
                                                  level=4, detail_cutoff=0, draw_cutoff=0,
                                                  num_samples=150,
                                                  interchromosomal=True )

        return rval

    # FIXME: this method probably belongs down in the model.Dataset class.
    def _get_highest_priority_msg( self, message_list ):
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
                elif message == "no converter":
                    return_message = message
                elif return_message == None and message == "pending":
                    return_message = message
        return return_message



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
                    #DBTODO BUG: errors doesn't exist in this scope, intent?
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

    def get_hda_state_counts( self, trans, history, include_deleted=False, include_hidden=False ):
        """
        Returns a dictionary with state counts for history's HDAs. Key is a 
        dataset state, value is the number of states in that count.
        """

        # Build query to get (state, count) pairs.
        cols_to_select = [ trans.app.model.Dataset.table.c.state, func.count( '*' ) ] 
        from_obj = trans.app.model.HistoryDatasetAssociation.table.join( trans.app.model.Dataset.table )
        
        conditions = [ trans.app.model.HistoryDatasetAssociation.table.c.history_id == history.id ]
        if not include_deleted:
            # Only count datasets that have not been deleted.
            conditions.append( trans.app.model.HistoryDatasetAssociation.table.c.deleted == False )
        if not include_hidden:
            # Only count datasets that are visible.
            conditions.append( trans.app.model.HistoryDatasetAssociation.table.c.visible == True )
        
        group_by = trans.app.model.Dataset.table.c.state
        query = select( columns=cols_to_select,
                        from_obj=from_obj,
                        whereclause=and_( *conditions ),
                        group_by=group_by )

        # Initialize count dict with all states.
        state_count_dict = {}
        for k, state in trans.app.model.Dataset.states.items():
            state_count_dict[ state ] = 0
                        
        # Process query results, adding to count dict.
        for row in trans.sa_session.execute( query ):
            state, count = row
            state_count_dict[ state ] = count

        return state_count_dict

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
        message = util.restore_text( params.get( 'message', ''  ) )
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
        else:
            if in_library:
                info_association.deleted = True
                trans.sa_session.add( info_association )
                trans.sa_session.flush()
            elif in_sample_tracking:
                trans.sa_session.delete( info_association )
                trans.sa_session.flush()
            message = 'The template for this %s has been deleted.' % item_type
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

    def _is_valid_slug( self, slug ):
        """ Returns true if slug is valid. """
        return _is_valid_slug( slug )
    
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

    @web.expose
    @web.require_login( "modify Galaxy items" )
    def set_slug_async( self, trans, id, new_slug ):
        item = self.get_item( trans, id )
        if item:
            # Only update slug if slug is not already in use.
            if trans.sa_session.query( item.__class__ ).filter_by( user=item.user, slug=new_slug, importable=True ).count() == 0: 
                item.slug = new_slug
                trans.sa_session.flush()

        return item.slug

    def _make_item_accessible( self, sa_session, item ):
        """ Makes item accessible--viewable and importable--and sets item's slug.
            Does not flush/commit changes, however. Item must have name, user, 
            importable, and slug attributes. """
        item.importable = True
        self.create_item_slug( sa_session, item )
    
    def create_item_slug( self, sa_session, item ):
        """ Create/set item slug. Slug is unique among user's importable items 
            for item's class. Returns true if item's slug was set/changed; false 
            otherwise. 
        """
        cur_slug = item.slug

        # Setup slug base.
        if cur_slug is None or cur_slug == "":
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
        else:
            slug_base = cur_slug

        # Using slug base, find a slug that is not taken. If slug is taken, 
        # add integer to end.
        new_slug = slug_base
        count = 1
        while sa_session.query( item.__class__ ).filter_by( user=item.user, slug=new_slug, importable=True ).count() != 0:
            # Slug taken; choose a new slug based on count. This approach can
            # handle numerous items with the same name gracefully.
            new_slug = '%s-%i' % ( slug_base, count )
            count += 1
        
        # Set slug and return.
        item.slug = new_slug
        return item.slug == cur_slug
        
    # -- Abstract methods. -- 
    
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
    
    def get_item( self, trans, id ):
        """ Return item based on id. """
        raise "Unimplemented Method"

class UsesQuotaMixin( object ):
    def get_quota( self, trans, id, check_ownership=False, check_accessible=False, deleted=None ):
        return self.get_object( trans, id, 'Quota', check_ownership=False, check_accessible=False, deleted=deleted )

class UsesTagsMixin( object ):

    def get_tag_handler( self, trans ):
        return trans.app.tag_handler

    def _get_user_tags( self, trans, item_class_name, id ):
        user = trans.user
        tagged_item = self._get_tagged_item( trans, item_class_name, id )
        return [ tag for tag in tagged_item.tags if ( tag.user == user ) ]

    def _get_tagged_item( self, trans, item_class_name, id, check_ownership=True ):
        tagged_item = self.get_object( trans, id, item_class_name, check_ownership=check_ownership, check_accessible=True )
        return tagged_item

    def _remove_items_tag( self, trans, item_class_name, id, tag_name ):
        """Remove a tag from an item."""
        user = trans.user
        tagged_item = self._get_tagged_item( trans, item_class_name, id )
        deleted = tagged_item and self.get_tag_handler( trans ).remove_item_tag( trans, user, tagged_item, tag_name )
        trans.sa_session.flush()
        return deleted

    def _apply_item_tag( self, trans, item_class_name, id, tag_name, tag_value=None ):
        user = trans.user
        tagged_item = self._get_tagged_item( trans, item_class_name, id )
        tag_assoc = self.get_tag_handler( trans ).apply_item_tag( trans, user, tagged_item, tag_name, tag_value )
        trans.sa_session.flush()
        return tag_assoc

    def _get_item_tag_assoc( self, trans, item_class_name, id, tag_name ):
        user = trans.user
        tagged_item = self._get_tagged_item( trans, item_class_name, id )
        log.debug( "In get_item_tag_assoc with tagged_item %s" % tagged_item )
        return self.get_tag_handler( trans )._get_item_tag_assoc( user, tagged_item, tag_name )

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
