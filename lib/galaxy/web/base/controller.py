"""
Contains functionality needed in every web interface
"""
import logging
import operator
import os
import re
from gettext import gettext

import pkg_resources
pkg_resources.require("SQLAlchemy >= 0.4")
from sqlalchemy import func, and_, select

from paste.httpexceptions import HTTPBadRequest, HTTPInternalServerError
from paste.httpexceptions import HTTPNotImplemented, HTTPRequestRangeNotSatisfiable
from galaxy import exceptions
from galaxy.exceptions import ItemAccessibilityException, ItemDeletionException, ItemOwnershipException
from galaxy.exceptions import MessageException

from galaxy import web
from galaxy import model
from galaxy import security
from galaxy import util
from galaxy import objectstore

from galaxy.web import error, url_for
from galaxy.web.form_builder import AddressField, CheckboxField, SelectField, TextArea, TextField
from galaxy.web.form_builder import build_select_field, HistoryField, PasswordField, WorkflowField, WorkflowMappingField
from galaxy.workflow.modules import module_factory, WorkflowModuleInjector, MissingToolException
from galaxy.model.orm import eagerload, eagerload_all, desc, not_
from galaxy.security.validate_user_input import validate_publicname
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.item_attrs import Dictifiable, UsesAnnotations

from galaxy.datatypes.interval import ChromatinInteractions
from galaxy.datatypes.data import Text

from galaxy.model import ExtendedMetadata, ExtendedMetadataIndex, LibraryDatasetDatasetAssociation, HistoryDatasetAssociation

from galaxy.managers import api_keys
from galaxy.managers import tags
from galaxy.managers import base as managers_base
from galaxy.datatypes.metadata import FileParameter
from galaxy.tools.parameters import visit_input_values
from galaxy.tools.parameters.basic import DataToolParameter
from galaxy.tools.parameters.basic import DataCollectionToolParameter
from galaxy.util.json import dumps
from galaxy.workflow.modules import ToolModule
from galaxy.workflow.steps import attach_ordered_steps
from galaxy.util import validation


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
        return managers_base.get_class( class_name )

    def get_object( self, trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None ):
        """
        Convenience method to get a model object with the specified checks.
        """
        return managers_base.get_object( trans, id, class_name, check_ownership=check_ownership, check_accessible=check_accessible, deleted=deleted )
  
    # this should be here - but catching errors from sharable item controllers that *should* have SharableItemMixin
    #   but *don't* then becomes difficult
    #def security_check( self, trans, item, check_ownership=False, check_accessible=False ):
    #    log.warn( 'BaseController.security_check: %s, %b, %b', str( item ), check_ownership, check_accessible )
    #    # meant to be overridden in SharableSecurityMixin
    #    return item

    def get_user( self, trans, id, check_ownership=False, check_accessible=False, deleted=None ):
        return self.get_object( trans, id, 'User', check_ownership=False, check_accessible=False, deleted=deleted )

    def get_group( self, trans, id, check_ownership=False, check_accessible=False, deleted=None ):
        return self.get_object( trans, id, 'Group', check_ownership=False, check_accessible=False, deleted=deleted )

    def get_role( self, trans, id, check_ownership=False, check_accessible=False, deleted=None ):
        return self.get_object( trans, id, 'Role', check_ownership=False, check_accessible=False, deleted=deleted )

    def encode_all_ids( self, trans, rval, recursive=False ):
        """
        Encodes all integer values in the dict rval whose keys are 'id' or end with '_id'

        It might be useful to turn this in to a decorator
        """
        return trans.security.encode_all_ids( rval, recursive=recursive )

    # incoming param validation
    # should probably be in sep. serializer class/object _used_ by controller
    def validate_and_sanitize_basestring( self, key, val ):
        return validation.validate_and_sanitize_basestring( key, val )

    def validate_and_sanitize_basestring_list( self, key, val ):
        return validation.validate_and_sanitize_basestring_list( key, val )

    def validate_boolean( self, key, val ):
        return validation.validate_boolean( key, val )


Root = BaseController


class BaseUIController( BaseController ):

    def get_object( self, trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None ):
        try:
            return BaseController.get_object( self, trans, id, class_name,
                check_ownership=check_ownership, check_accessible=check_accessible, deleted=deleted )

        except MessageException:
            raise       # handled in the caller
        except:
            log.exception( "Exception in get_object check for %s %s:" % ( class_name, str( id ) ) )
            raise Exception( 'Server error retrieving %s id ( %s ).' % ( class_name, str( id ) ) )


class BaseAPIController( BaseController ):

    def get_object( self, trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None ):
        try:
            return BaseController.get_object( self, trans, id, class_name,
                check_ownership=check_ownership, check_accessible=check_accessible, deleted=deleted )

        except ItemDeletionException, e:
            raise HTTPBadRequest( detail="Invalid %s id ( %s ) specified: %s" % ( class_name, str( id ), str( e ) ) )
        except MessageException, e:
            raise HTTPBadRequest( detail=e.err_msg )
        except Exception, e:
            log.exception( "Exception in get_object check for %s %s." % ( class_name, str( id ) ) )
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


class CreatesUsersMixin:
    """
    Mixin centralizing logic for user creation between web and API controller.

    Web controller handles additional features such e-mail subscription, activation,
    user forms, etc.... API created users are much more vanilla for the time being.
    """

    def create_user( self, trans, email, username, password ):
        user = trans.app.model.User( email=email )
        user.set_password_cleartext( password )
        user.username = username
        if trans.app.config.user_activation_on:
            user.active = False
        else:
            user.active = True  # Activation is off, every new user is active by default.
        trans.sa_session.add( user )
        trans.sa_session.flush()
        trans.app.security_agent.create_private_user_role( user )
        if trans.webapp.name == 'galaxy':
            # We set default user permissions, before we log in and set the default history permissions
            trans.app.security_agent.user_set_default_permissions( user,
                                                                   default_access_private=trans.app.config.new_user_dataset_access_role_default_private )
        return user


class CreatesApiKeysMixin:
    """
    Mixing centralizing logic for creating API keys for user objects.

    Deprecated - please use api_keys.ApiKeyManager for new development.
    """

    def create_api_key( self, trans, user ):
        return api_keys.ApiKeyManager( trans.app ).create_api_key( user )


class SharableItemSecurityMixin:
    """ Mixin for handling security for sharable items. """

    def security_check( self, trans, item, check_ownership=False, check_accessible=False ):
        """ Security checks for an item: checks if (a) user owns item or (b) item is accessible to user. """
        return managers_base.security_check( trans, item, check_ownership=check_ownership, check_accessible=check_accessible )


class UsesHistoryMixin( SharableItemSecurityMixin ):
    """ Mixin for controllers that use History objects. """

    def get_history( self, trans, id, check_ownership=True, check_accessible=False, deleted=None ):
        """
        Get a History from the database by id, verifying ownership.
        """
        history = self.get_object( trans, id, 'History',
            check_ownership=check_ownership, check_accessible=check_accessible, deleted=deleted )
        history = self.security_check( trans, history, check_ownership, check_accessible )
        return history

    def get_user_histories( self, trans, user=None, include_deleted=False, only_deleted=False ):
        """
        Get all the histories for a given user (defaulting to `trans.user`)
        ordered by update time and filtered on whether they've been deleted.
        """
        # handle default and/or anonymous user (which still may not have a history yet)
        user = user or trans.user
        if not user:
            current_history = trans.get_history()
            return [ current_history ] if current_history else []

        history_model = trans.model.History
        query = ( trans.sa_session.query( history_model )
            .filter( history_model.user == user )
            .order_by( desc( history_model.table.c.update_time ) ) )
        if only_deleted:
            query = query.filter( history_model.deleted == True )
        elif not include_deleted:
            query = query.filter( history_model.deleted == False )

        return query.all()

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

    def get_hda_summary_dicts( self, trans, history ):
        """Returns a list of dictionaries containing summary information
        for each HDA in the given history.
        """
        hda_model = trans.model.HistoryDatasetAssociation

        # get state, name, etc.
        columns = ( hda_model.name, hda_model.hid, hda_model.id, hda_model.deleted,
                    trans.model.Dataset.state )
        column_keys = [ "name", "hid", "id", "deleted", "state" ]

        query = ( trans.sa_session.query( *columns )
                    .enable_eagerloads( False )
                    .filter( hda_model.history == history )
                    .join( trans.model.Dataset )
                    .order_by( hda_model.hid ) )

        # build dictionaries, adding history id and encoding all ids
        hda_dicts = []
        for hda_tuple in query.all():
            hda_dict = dict( zip( column_keys, hda_tuple ) )
            hda_dict[ 'history_id' ] = history.id
            trans.security.encode_dict_ids( hda_dict )
            hda_dicts.append( hda_dict )
        return hda_dicts

    def _get_hda_state_summaries( self, trans, hda_dict_list ):
        """Returns two dictionaries (in a tuple): state_counts and state_ids.
        Each is keyed according to the possible hda states:
            _counts contains a sum of the datasets in each state
            _ids contains a list of the encoded ids for each hda in that state

        hda_dict_list should be a list of hda data in dictionary form.
        """
        #TODO: doc to rst
        # init counts, ids for each state
        state_counts = {}
        state_ids = {}
        for key, state in trans.app.model.Dataset.states.items():
            state_counts[ state ] = 0
            state_ids[ state ] = []

        for hda_dict in hda_dict_list:
            item_state = hda_dict['state']
            if not hda_dict['deleted']:
                state_counts[ item_state ] = state_counts[ item_state ] + 1
            # needs to return all ids (no deleted check)
            state_ids[ item_state ].append( hda_dict['id'] )

        return ( state_counts, state_ids )

    def _get_history_state_from_hdas( self, trans, history, hda_state_counts ):
        """Returns the history state based on the states of the HDAs it contains.
        """
        states = trans.app.model.Dataset.states

        num_hdas = sum( hda_state_counts.values() )
        # (default to ERROR)
        state = states.ERROR
        if num_hdas == 0:
            state = states.NEW

        else:
            if( ( hda_state_counts[ states.RUNNING ] > 0 )
            or  ( hda_state_counts[ states.SETTING_METADATA ] > 0 )
            or  ( hda_state_counts[ states.UPLOAD ] > 0 ) ):
                state = states.RUNNING

            elif hda_state_counts[ states.QUEUED ] > 0:
                state = states.QUEUED

            elif( ( hda_state_counts[ states.ERROR ] > 0 )
            or    ( hda_state_counts[ states.FAILED_METADATA ] > 0 ) ):
                state = states.ERROR

            elif hda_state_counts[ states.OK ] == num_hdas:
                state = states.OK

        return state

    def get_history_dict( self, trans, history, hda_dictionaries=None ):
        """Returns history data in the form of a dictionary.
        """
        history_dict = history.to_dict( view='element', value_mapper={ 'id':trans.security.encode_id })
        history_dict[ 'user_id' ] = None
        if history.user_id:
            history_dict[ 'user_id' ] = trans.security.encode_id( history.user_id )

        history_dict[ 'nice_size' ] = history.get_disk_size( nice_size=True )
        history_dict[ 'annotation' ] = history.get_item_annotation_str( trans.sa_session, trans.user, history )
        if not history_dict[ 'annotation' ]:
            history_dict[ 'annotation' ] = ''
        #TODO: item_slug url
        if history_dict[ 'importable' ] and history_dict[ 'slug' ]:
            #TODO: this should be in History (or a superclass of)
            username_and_slug = ( '/' ).join(( 'u', history.user.username, 'h', history_dict[ 'slug' ] ))
            history_dict[ 'username_and_slug' ] = username_and_slug

        hda_summaries = hda_dictionaries if hda_dictionaries else self.get_hda_summary_dicts( trans, history )
        #TODO remove the following in v2
        ( state_counts, state_ids ) = self._get_hda_state_summaries( trans, hda_summaries )
        history_dict[ 'state_details' ] = state_counts
        history_dict[ 'state_ids' ] = state_ids
        history_dict[ 'state' ] = self._get_history_state_from_hdas( trans, history, state_counts )

        return history_dict

    def set_history_from_dict( self, trans, history, new_data ):
        """
        Changes history data using the given dictionary new_data.
        """
        #precondition: ownership of the history has already been checked
        #precondition: user is not None (many of these attributes require a user to set properly)
        user = trans.get_user()

        # published histories should always be importable
        if 'published' in new_data and new_data[ 'published' ] and not history.importable:
            new_data[ 'importable' ] = True
        # send what we can down into the model
        changed = history.set_from_dict( new_data )

        # the rest (often involving the trans) - do here
        #TODO: the next two could be an aspect/mixin
        #TODO: also need a way to check whether they've changed - assume they have for now
        if 'annotation' in new_data:
            history.add_item_annotation( trans.sa_session, user, history, new_data[ 'annotation' ] )
            changed[ 'annotation' ] = new_data[ 'annotation' ]

        if 'tags' in new_data:
            self.set_tags_from_list( trans, history, new_data[ 'tags' ], user=user )
            changed[ 'tags' ] = new_data[ 'tags' ]

        #TODO: sharing with user/permissions?

        if changed.keys():
            trans.sa_session.flush()

            # create a slug if none exists (setting importable to false should not remove the slug)
            if 'importable' in changed and changed[ 'importable' ] and not history.slug:
                self._create_history_slug( trans, history )

        return changed

    def _create_history_slug( self, trans, history ):
        #TODO: mixins need to die a quick, horrible death
        #   (this is duplicate from SharableMixin which can't be added to UsesHistory without exposing various urls)
        cur_slug = history.slug

        # Setup slug base.
        if cur_slug is None or cur_slug == "":
            # Item can have either a name or a title.
            item_name = history.name
            slug_base = util.ready_name_for_url( item_name.lower() )
        else:
            slug_base = cur_slug

        # Using slug base, find a slug that is not taken. If slug is taken,
        # add integer to end.
        new_slug = slug_base
        count = 1
        while ( trans.sa_session.query( trans.app.model.History )
                    .filter_by( user=history.user, slug=new_slug, importable=True )
                    .count() != 0 ):
            # Slug taken; choose a new slug based on count. This approach can
            # handle numerous items with the same name gracefully.
            new_slug = '%s-%i' % ( slug_base, count )
            count += 1

        # Set slug and return.
        trans.sa_session.add( history )
        history.slug = new_slug
        trans.sa_session.flush()
        return history.slug == cur_slug


class ExportsHistoryMixin:

    def serve_ready_history_export( self, trans, jeha ):
        assert jeha.ready
        if jeha.compressed:
            trans.response.set_content_type( 'application/x-gzip' )
        else:
            trans.response.set_content_type( 'application/x-tar' )
        disposition = 'attachment; filename="%s"' % jeha.export_name
        trans.response.headers["Content-Disposition"] = disposition
        return open( trans.app.object_store.get_filename( jeha.dataset ) )

    def queue_history_export( self, trans, history, gzip=True, include_hidden=False, include_deleted=False ):
        # Convert options to booleans.
        #
        if isinstance( gzip, basestring ):
            gzip = ( gzip in [ 'True', 'true', 'T', 't' ] )
        if isinstance( include_hidden, basestring ):
            include_hidden = ( include_hidden in [ 'True', 'true', 'T', 't' ] )
        if isinstance( include_deleted, basestring ):
            include_deleted = ( include_deleted in [ 'True', 'true', 'T', 't' ] )

        # Run job to do export.
        history_exp_tool = trans.app.toolbox.get_tool( '__EXPORT_HISTORY__' )
        params = {
            'history_to_export': history,
            'compress': gzip,
            'include_hidden': include_hidden,
            'include_deleted': include_deleted
        }

        history_exp_tool.execute( trans, incoming=params, history=history, set_output_hid=True )


class ImportsHistoryMixin:

    def queue_history_import( self, trans, archive_type, archive_source ):
        # Run job to do import.
        history_imp_tool = trans.app.toolbox.get_tool( '__IMPORT_HISTORY__' )
        incoming = { '__ARCHIVE_SOURCE__' : archive_source, '__ARCHIVE_TYPE__' : archive_type }
        history_imp_tool.execute( trans, incoming=incoming )


class UsesHistoryDatasetAssociationMixin:
    """
    Mixin for controllers that use HistoryDatasetAssociation objects.
    """

    def get_dataset( self, trans, dataset_id, check_ownership=True, check_accessible=False, check_state=True ):
        """
        Get an HDA object by id performing security checks using
        the current transaction.
        """
        try:
            dataset_id = trans.security.decode_id( dataset_id )
        except ( AttributeError, TypeError ):
            # DEPRECATION: We still support unencoded ids for backward compatibility
            try:
                dataset_id = int( dataset_id )
            except ValueError, v_err:
                raise HTTPBadRequest( "Invalid dataset id: %s." % str( dataset_id ) )

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
        """
        Get a HistoryDatasetAssociation from the database by id, verifying ownership.
        """
        #TODO: duplicate of above? alias to above (or vis-versa)
        self.security_check( trans, history, check_ownership=check_ownership, check_accessible=check_accessible )
        hda = self.get_object( trans, dataset_id, 'HistoryDatasetAssociation',
                               check_ownership=False, check_accessible=False )

        if check_accessible:
            if( not trans.user_is_admin()
            and not trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), hda.dataset ) ):
                error( "You are not allowed to access this dataset" )

            if check_state and hda.state == trans.model.Dataset.states.UPLOAD:
                error( "Please wait until this dataset finishes uploading before attempting to view it." )
        return hda

    def get_history_dataset_association_from_ids( self, trans, id, history_id ):
        # Just to echo other TODOs, there seems to be some overlap here, still
        # this block appears multiple places (dataset show, history_contents
        # show, upcoming history job show) so I am consolodating it here.
        # Someone smarter than me should determine if there is some redundancy here.

        # for anon users:
        #TODO: check login_required?
        #TODO: this isn't actually most_recently_used (as defined in histories)
        if( ( trans.user == None )
        and ( history_id == trans.security.encode_id( trans.history.id ) ) ):
            history = trans.history
            #TODO: dataset/hda by id (from history) OR check_ownership for anon user
            hda = self.get_history_dataset_association( trans, history, id,
                check_ownership=False, check_accessible=True )
        else:
            #TODO: do we really need the history?
            history = self.get_history( trans, history_id,
                check_ownership=False, check_accessible=True, deleted=False )
            hda = self.get_history_dataset_association( trans, history, id,
                check_ownership=False, check_accessible=True )
        return hda

    def get_hda_list( self, trans, hda_ids, check_ownership=True, check_accessible=False, check_state=True ):
        """
        Returns one or more datasets in a list.

        If a dataset is not found or is inaccessible to trans.user,
        add None in its place in the list.
        """
        # precondtion: dataset_ids is a list of encoded id strings
        hdas = []
        for id in hda_ids:
            hda = None
            try:
                hda = self.get_dataset( trans, id,
                    check_ownership=check_ownership,
                    check_accessible=check_accessible,
                    check_state=check_state )
            except Exception, exception:
                pass
            hdas.append( hda )
        return hdas

    def get_data( self, dataset, preview=True ):
        """
        Gets a dataset's data.
        """
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

    def get_hda_dict( self, trans, hda ):
        """Return full details of this HDA in dictionary form.
        """
        #precondition: the user's access to this hda has already been checked
        #TODO:?? postcondition: all ids are encoded (is this really what we want at this level?)
        expose_dataset_path = trans.user_is_admin() or trans.app.config.expose_dataset_path
        hda_dict = hda.to_dict( view='element', expose_dataset_path=expose_dataset_path )
        hda_dict[ 'api_type' ] = "file"

        # Add additional attributes that depend on trans can hence must be added here rather than at the model level.
        can_access_hda = trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), hda.dataset )
        can_access_hda = ( trans.user_is_admin() or can_access_hda )
        if not can_access_hda:
            return self.get_inaccessible_hda_dict( trans, hda )
        hda_dict[ 'accessible' ] = True

        #TODO: I'm unclear as to which access pattern is right
        hda_dict[ 'annotation' ] = hda.get_item_annotation_str( trans.sa_session, trans.user, hda )
        #annotation = getattr( hda, 'annotation', hda.get_item_annotation_str( trans.sa_session, trans.user, hda ) )

        # ---- return here if deleted AND purged OR can't access
        purged = ( hda.purged or hda.dataset.purged )
        if ( hda.deleted and purged ):
            #TODO: to_dict should really go AFTER this - only summary data
            return trans.security.encode_dict_ids( hda_dict )

        if expose_dataset_path:
            try:
                hda_dict[ 'file_name' ] = hda.file_name
            except objectstore.ObjectNotFound:
                log.exception( 'objectstore.ObjectNotFound, HDA %s.', hda.id )

        hda_dict[ 'download_url' ] = url_for( 'history_contents_display',
            history_id = trans.security.encode_id( hda.history.id ),
            history_content_id = trans.security.encode_id( hda.id ) )

        # resubmitted is not a real state
        hda_dict[ 'resubmitted' ] = False
        if hda.state == trans.app.model.Dataset.states.RESUBMITTED:
            hda_dict[ 'state' ] = hda.dataset.state
            hda_dict[ 'resubmitted' ] = True

        # indeces, assoc. metadata files, etc.
        meta_files = []
        for meta_type in hda.metadata.spec.keys():
            if isinstance( hda.metadata.spec[ meta_type ].param, FileParameter ):
                meta_files.append( dict( file_type=meta_type ) )
        if meta_files:
            hda_dict[ 'meta_files' ] = meta_files

        # currently, the viz reg is optional - handle on/off
        if trans.app.visualizations_registry:
            hda_dict[ 'visualizations' ] = trans.app.visualizations_registry.get_visualizations( trans, hda )
        else:
            hda_dict[ 'visualizations' ] = hda.get_visualizations()
        #TODO: it may also be wiser to remove from here and add as API call that loads the visualizations
        #           when the visualizations button is clicked (instead of preloading/pre-checking)

        # ---- return here if deleted
        if hda.deleted and not purged:
            return trans.security.encode_dict_ids( hda_dict )

        return trans.security.encode_dict_ids( hda_dict )

    def get_inaccessible_hda_dict( self, trans, hda ):
        return trans.security.encode_dict_ids({
            'id'        : hda.id,
            'history_id': hda.history.id,
            'hid'       : hda.hid,
            'name'      : hda.name,
            'state'     : hda.state,
            'deleted'   : hda.deleted,
            'visible'   : hda.visible,
            'accessible': False
        })

    def get_hda_dict_with_error( self, trans, hda=None, history_id=None, id=None, error_msg='Error' ):
        return trans.security.encode_dict_ids({
            'id'        : hda.id if hda else id,
            'history_id': hda.history.id if hda else history_id,
            'hid'       : hda.hid if hda else '(unknown)',
            'name'      : hda.name if hda else '(unknown)',
            'error'     : error_msg,
            'state'     : trans.model.Dataset.states.NEW
        })

    def get_display_apps( self, trans, hda ):
        display_apps = []
        for display_app in hda.get_display_applications( trans ).itervalues():

            app_links = []
            for link_app in display_app.links.itervalues():
                app_links.append({
                    'target': link_app.url.get( 'target_frame', '_blank' ),
                    'href'  : link_app.get_display_url( hda, trans ),
                    'text'  : gettext( link_app.name )
                })
            if app_links:
                display_apps.append( dict( label=display_app.name, links=app_links ) )

        return display_apps

    def get_old_display_applications( self, trans, hda ):
        display_apps = []
        if not trans.app.config.enable_old_display_applications:
            return display_apps

        for display_app in hda.datatype.get_display_types():
            target_frame, display_links = hda.datatype.get_display_links( hda,
                display_app, trans.app, trans.request.base )

            if len( display_links ) > 0:
                display_label = hda.datatype.get_display_label( display_app )

                app_links = []
                for display_name, display_link in display_links:
                    app_links.append({
                        'target': target_frame,
                        'href'  : display_link,
                        'text'  : gettext( display_name )
                    })
                if app_links:
                    display_apps.append( dict( label=display_label, links=app_links ) )

        return display_apps

    def set_hda_from_dict( self, trans, hda, new_data ):
        """
        Changes HDA data using the given dictionary new_data.
        """
        # precondition: access of the hda has already been checked

        # send what we can down into the model
        changed = hda.set_from_dict( new_data )
        # the rest (often involving the trans) - do here
        if 'annotation' in new_data.keys() and trans.get_user():
            hda.add_item_annotation( trans.sa_session, trans.get_user(), hda, new_data[ 'annotation' ] )
            changed[ 'annotation' ] = new_data[ 'annotation' ]
        if 'tags' in new_data.keys() and trans.get_user():
            self.set_tags_from_list( trans, hda, new_data[ 'tags' ], user=trans.user )
        # sharing/permissions?
        # purged

        if changed.keys():
            trans.sa_session.flush()

        return changed

    def get_hda_job( self, hda ):
        # Get dataset's job.
        job = None
        for job_output_assoc in hda.creating_job_associations:
            job = job_output_assoc.job
            break
        return job

    def stop_hda_creating_job( self, hda ):
        """
        Stops an HDA's creating job if all the job's other outputs are deleted.
        """
        if hda.parent_id is None and len( hda.creating_job_associations ) > 0:
            # Mark associated job for deletion
            job = hda.creating_job_associations[0].job
            if job.state in [ self.app.model.Job.states.QUEUED, self.app.model.Job.states.RUNNING, self.app.model.Job.states.NEW ]:
                # Are *all* of the job's other output datasets deleted?
                if job.check_if_output_datasets_deleted():
                    job.mark_deleted( self.app.config.track_jobs_in_database )
                    self.app.job_manager.job_stop_queue.put( job.id )


class UsesLibraryMixin:

    def get_library( self, trans, id, check_ownership=False, check_accessible=True ):
        l = self.get_object( trans, id, 'Library' )
        if check_accessible and not ( trans.user_is_admin() or trans.app.security_agent.can_access_library( trans.get_current_user_roles(), l ) ):
            error( "LibraryFolder is not accessible to the current user" )
        return l


class UsesLibraryMixinItems( SharableItemSecurityMixin ):

    def get_library_folder( self, trans, id, check_ownership=False, check_accessible=True ):
        return self.get_object( trans, id, 'LibraryFolder',
                                check_ownership=False, check_accessible=check_accessible )

    def get_library_dataset_dataset_association( self, trans, id, check_ownership=False, check_accessible=True ):
        # Deprecated in lieu to galaxy.managers.lddas.LDDAManager.get() but not
        # reusing that exactly because of subtle differences in exception handling
        # logic (API controller override get_object to be slightly different).
        return self.get_object( trans, id, 'LibraryDatasetDatasetAssociation',
                                check_ownership=False, check_accessible=check_accessible )

    def get_library_dataset( self, trans, id, check_ownership=False, check_accessible=True ):
        return self.get_object( trans, id, 'LibraryDataset',
                                check_ownership=False, check_accessible=check_accessible )

    #TODO: it makes no sense that I can get roles from a user but not user.is_admin()
    #def can_user_add_to_library_item( self, trans, user, item ):
    #    if not user: return False
    #    return (  ( user.is_admin() )
    #           or ( trans.app.security_agent.can_add_library_item( user.all_roles(), item ) ) )

    def can_current_user_add_to_library_item( self, trans, item ):
        if not trans.user: return False
        return (  ( trans.user_is_admin() )
               or ( trans.app.security_agent.can_add_library_item( trans.get_current_user_roles(), item ) ) )

    def check_user_can_add_to_library_item( self, trans, item, check_accessible=True ):
        """
        Raise exception if user cannot add to the specified library item (i.e.
        Folder). Can set check_accessible to False if folder was loaded with
        this check.
        """
        if not trans.user:
            return False

        current_user_roles = trans.get_current_user_roles()
        if trans.user_is_admin():
            return True

        if check_accessible:
            if not trans.app.security_agent.can_access_library_item( current_user_roles, item, trans.user ):
                raise ItemAccessibilityException( )

        if not trans.app.security_agent.can_add_library_item( trans.get_current_user_roles(), item ):
            # Slight misuse of ItemOwnershipException?
            raise ItemOwnershipException( "User cannot add to library item." )

    def copy_hda_to_library_folder( self, trans, hda, library_folder, roles=None, ldda_message='' ):
        #PRECONDITION: permissions for this action on hda and library_folder have been checked
        roles = roles or []

        # this code was extracted from library_common.add_history_datasets_to_library
        #TODO: refactor library_common.add_history_datasets_to_library to use this for each hda to copy

        # create the new ldda and apply the folder perms to it
        ldda = hda.to_library_dataset_dataset_association( trans, target_folder=library_folder,
                                                           roles=roles, ldda_message=ldda_message )
        self._apply_library_folder_permissions_to_ldda( trans, library_folder, ldda )
        self._apply_hda_permissions_to_ldda( trans, hda, ldda )
        #TODO:?? not really clear on how permissions are being traded here
        #   seems like hda -> ldda permissions should be set in to_library_dataset_dataset_association
        #   then they get reset in _apply_library_folder_permissions_to_ldda
        #   then finally, re-applies hda -> ldda for missing actions in _apply_hda_permissions_to_ldda??
        return ldda

    def _apply_library_folder_permissions_to_ldda( self, trans, library_folder, ldda ):
        """
        Copy actions/roles from library folder to an ldda (and its library_dataset).
        """
        #PRECONDITION: permissions for this action on library_folder and ldda have been checked
        security_agent = trans.app.security_agent
        security_agent.copy_library_permissions( trans, library_folder, ldda )
        security_agent.copy_library_permissions( trans, library_folder, ldda.library_dataset )
        return security_agent.get_permissions( ldda )

    def _apply_hda_permissions_to_ldda( self, trans, hda, ldda ):
        """
        Copy actions/roles from hda to ldda.library_dataset (and then ldda) if ldda
        doesn't already have roles for the given action.
        """
        #PRECONDITION: permissions for this action on hda and ldda have been checked
        # Make sure to apply any defined dataset permissions, allowing the permissions inherited from the
        #   library_dataset to over-ride the same permissions on the dataset, if they exist.
        security_agent = trans.app.security_agent
        dataset_permissions_dict = security_agent.get_permissions( hda.dataset )
        library_dataset = ldda.library_dataset
        library_dataset_actions = [ permission.action for permission in library_dataset.actions ]

        # except that: if DATASET_MANAGE_PERMISSIONS exists in the hda.dataset permissions,
        #   we need to instead apply those roles to the LIBRARY_MANAGE permission to the library dataset
        dataset_manage_permissions_action = security_agent.get_action( 'DATASET_MANAGE_PERMISSIONS' ).action
        library_manage_permissions_action = security_agent.get_action( 'LIBRARY_MANAGE' ).action
        #TODO: test this and remove if in loop below
        #TODO: doesn't handle action.action
        #if dataset_manage_permissions_action in dataset_permissions_dict:
        #    managing_roles = dataset_permissions_dict.pop( dataset_manage_permissions_action )
        #    dataset_permissions_dict[ library_manage_permissions_action ] = managing_roles

        flush_needed = False
        for action, dataset_permissions_roles in dataset_permissions_dict.items():
            if isinstance( action, security.Action ):
                action = action.action

            # alter : DATASET_MANAGE_PERMISSIONS -> LIBRARY_MANAGE (see above)
            if action == dataset_manage_permissions_action:
                action = library_manage_permissions_action

            #TODO: generalize to util.update_dict_without_overwrite
            # add the hda actions & roles to the library_dataset
            #NOTE: only apply an hda perm if it's NOT set in the library_dataset perms (don't overwrite)
            if action not in library_dataset_actions:
                for role in dataset_permissions_roles:
                    ldps = trans.model.LibraryDatasetPermissions( action, library_dataset, role )
                    ldps = [ ldps ] if not isinstance( ldps, list ) else ldps
                    for ldp in ldps:
                        trans.sa_session.add( ldp )
                        flush_needed = True

        if flush_needed:
            trans.sa_session.flush()

        # finally, apply the new library_dataset to its associated ldda (must be the same)
        security_agent.copy_library_permissions( trans, library_dataset, ldda )
        return security_agent.get_permissions( ldda )


class UsesVisualizationMixin( UsesHistoryDatasetAssociationMixin, UsesLibraryMixinItems ):
    """
    Mixin for controllers that use Visualization objects.
    """

    viz_types = [ "trackster" ]

    def get_visualization( self, trans, id, check_ownership=True, check_accessible=False ):
        """
        Get a Visualization from the database by id, verifying ownership.
        """
        # Load workflow from database
        try:
            visualization = trans.sa_session.query( trans.model.Visualization ).get( trans.security.decode_id( id ) )
        except TypeError:
            visualization = None
        if not visualization:
            error( "Visualization not found" )
        else:
            return self.security_check( trans, visualization, check_ownership, check_accessible )

    def get_visualizations_by_user( self, trans, user, order_by=None, query_only=False ):
        """
        Return query or query results of visualizations filtered by a user.

        Set `order_by` to a column or list of columns to change the order
        returned. Defaults to `DEFAULT_ORDER_BY`.
        Set `query_only` to return just the query for further filtering or
        processing.
        """
        #TODO: move into model (as class attr)
        DEFAULT_ORDER_BY = [ model.Visualization.title ]
        if not order_by:
            order_by = DEFAULT_ORDER_BY
        if not isinstance( order_by, list ):
            order_by = [ order_by ]
        query = trans.sa_session.query( model.Visualization )
        query = query.filter( model.Visualization.user == user )
        if order_by:
            query = query.order_by( *order_by )
        if query_only:
            return query
        return query.all()

    def get_visualizations_shared_with_user( self, trans, user, order_by=None, query_only=False ):
        """
        Return query or query results for visualizations shared with the given user.

        Set `order_by` to a column or list of columns to change the order
        returned. Defaults to `DEFAULT_ORDER_BY`.
        Set `query_only` to return just the query for further filtering or
        processing.
        """
        DEFAULT_ORDER_BY = [ model.Visualization.title ]
        if not order_by:
            order_by = DEFAULT_ORDER_BY
        if not isinstance( order_by, list ):
            order_by = [ order_by ]
        query = trans.sa_session.query( model.Visualization ).join( model.VisualizationUserShareAssociation )
        query = query.filter( model.VisualizationUserShareAssociation.user_id == user.id )
        # remove duplicates when a user shares with themselves?
        query = query.filter( model.Visualization.user_id != user.id )
        if order_by:
            query = query.order_by( *order_by )
        if query_only:
            return query
        return query.all()

    def get_published_visualizations( self, trans, exclude_user=None, order_by=None, query_only=False ):
        """
        Return query or query results for published visualizations optionally excluding
        the user in `exclude_user`.

        Set `order_by` to a column or list of columns to change the order
        returned. Defaults to `DEFAULT_ORDER_BY`.
        Set `query_only` to return just the query for further filtering or
        processing.
        """
        DEFAULT_ORDER_BY = [ model.Visualization.title ]
        if not order_by:
            order_by = DEFAULT_ORDER_BY
        if not isinstance( order_by, list ):
            order_by = [ order_by ]
        query = trans.sa_session.query( model.Visualization )
        query = query.filter( model.Visualization.published == True )
        if exclude_user:
            query = query.filter( model.Visualization.user != exclude_user )
        if order_by:
            query = query.order_by( *order_by )
        if query_only:
            return query
        return query.all()

    #TODO: move into model (to_dict)
    def get_visualization_summary_dict( self, visualization ):
        """
        Return a set of summary attributes for a visualization in dictionary form.
        NOTE: that encoding ids isn't done here should happen at the caller level.
        """
        #TODO: deleted
        #TODO: importable
        return {
            'id'        : visualization.id,
            'title'     : visualization.title,
            'type'      : visualization.type,
            'dbkey'     : visualization.dbkey,
        }

    def get_visualization_dict( self, visualization ):
        """
        Return a set of detailed attributes for a visualization in dictionary form.
        The visualization's latest_revision is returned in its own sub-dictionary.
        NOTE: that encoding ids isn't done here should happen at the caller level.
        """
        return {
            'model_class': 'Visualization',
            'id'        : visualization.id,
            'title'     : visualization.title,
            'type'      : visualization.type,
            'user_id'   : visualization.user.id,
            'dbkey'     : visualization.dbkey,
            'slug'      : visualization.slug,
            # to_dict only the latest revision (allow older to be fetched elsewhere)
            'latest_revision' : self.get_visualization_revision_dict( visualization.latest_revision ),
            'revisions' : [ r.id for r in visualization.revisions ],
        }

    def get_visualization_revision_dict( self, revision ):
        """
        Return a set of detailed attributes for a visualization in dictionary form.
        NOTE: that encoding ids isn't done here should happen at the caller level.
        """
        return {
            'model_class': 'VisualizationRevision',
            'id'        : revision.id,
            'visualization_id' : revision.visualization.id,
            'title'     : revision.title,
            'dbkey'     : revision.dbkey,
            'config'    : revision.config,
        }

    def import_visualization( self, trans, id, user=None ):
        """
        Copy the visualization with the given id and associate the copy
        with the given user (defaults to trans.user).

        Raises `ItemAccessibilityException` if `user` is not passed and
        the current user is anonymous, and if the visualization is not `importable`.
        Raises `ItemDeletionException` if the visualization has been deleted.
        """
        # default to trans.user, error if anon
        if not user:
            if not trans.user:
                raise ItemAccessibilityException( "You must be logged in to import Galaxy visualizations" )
            user = trans.user

        # check accessibility
        visualization = self.get_visualization( trans, id, check_ownership=False )
        if not visualization.importable:
            raise ItemAccessibilityException( "The owner of this visualization has disabled imports via this link." )
        if visualization.deleted:
            raise ItemDeletionException( "You can't import this visualization because it has been deleted." )

        # copy vis and alter title
        #TODO: need to handle custom db keys.
        imported_visualization = visualization.copy( user=user, title="imported: " + visualization.title )
        trans.sa_session.add( imported_visualization )
        trans.sa_session.flush()
        return imported_visualization

    def create_visualization( self, trans, type, title="Untitled Visualization", slug=None,
                              dbkey=None, annotation=None, config={}, save=True ):
        """
        Create visualiation and first revision.
        """
        visualization = self._create_visualization( trans, title, type, dbkey, slug, annotation, save )
        #TODO: handle this error structure better either in _create or here
        if isinstance( visualization, dict ):
            err_dict = visualization
            raise ValueError( err_dict[ 'title_err' ] or err_dict[ 'slug_err' ] )

        # Create and save first visualization revision
        revision = trans.model.VisualizationRevision( visualization=visualization, title=title,
                                                      config=config, dbkey=dbkey )
        visualization.latest_revision = revision

        if save:
            session = trans.sa_session
            session.add( revision )
            session.flush()

        return visualization

    def add_visualization_revision( self, trans, visualization, config, title, dbkey ):
        """
        Adds a new `VisualizationRevision` to the given `visualization` with
        the given parameters and set its parent visualization's `latest_revision`
        to the new revision.
        """
        #precondition: only add new revision on owned vis's
        #TODO:?? should we default title, dbkey, config? to which: visualization or latest_revision?
        revision = trans.model.VisualizationRevision( visualization, title, dbkey, config )
        visualization.latest_revision = revision
        #TODO:?? does this automatically add revision to visualzation.revisions?
        trans.sa_session.add( revision )
        trans.sa_session.flush()
        return revision

    def save_visualization( self, trans, config, type, id=None, title=None, dbkey=None, slug=None, annotation=None ):
        session = trans.sa_session

        # Create/get visualization.
        if not id:
            # Create new visualization.
            vis = self._create_visualization( trans, title, type, dbkey, slug, annotation )
        else:
            decoded_id = trans.security.decode_id( id )
            vis = session.query( trans.model.Visualization ).get( decoded_id )
            #TODO: security check?

        # Create new VisualizationRevision that will be attached to the viz
        vis_rev = trans.model.VisualizationRevision()
        vis_rev.visualization = vis
        # do NOT alter the dbkey
        vis_rev.dbkey = vis.dbkey
        # do alter the title and config
        vis_rev.title = title

        # -- Validate config. --

        if vis.type == 'trackster':
            def unpack_track( track_dict ):
                """ Unpack a track from its json. """
                dataset_dict = track_dict[ 'dataset' ]
                return {
                    "dataset_id": trans.security.decode_id( dataset_dict['id'] ),
                    "hda_ldda": dataset_dict.get('hda_ldda', 'hda'),
                    "track_type": track_dict['track_type'],
                    "prefs": track_dict['prefs'],
                    "mode": track_dict['mode'],
                    "filters": track_dict['filters'],
                    "tool_state": track_dict['tool_state']
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

    def get_tool_def( self, trans, hda ):
        """ Returns definition of an interactive tool for an HDA. """

        job = self.get_hda_job( hda )
        if not job:
            return None
        tool = trans.app.toolbox.get_tool( job.tool_id )
        if not tool:
            return None

        # Tool must have a Trackster configuration.
        if not tool.trackster_conf:
            return None

        # -- Get tool definition and add input values from job. --
        tool_dict = tool.to_dict( trans, io_details=True )
        tool_param_values = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        tool_param_values = tool.params_from_strings( tool_param_values, trans.app, ignore_errors=True )

        # Only get values for simple inputs for now.
        inputs_dict = [ i for i in tool_dict[ 'inputs' ] if i[ 'type' ] not in [ 'data', 'hidden_data', 'conditional' ] ]
        for t_input in inputs_dict:
            # Add value to tool.
            if 'name' in t_input:
                name = t_input[ 'name' ]
                if name in tool_param_values:
                    value = tool_param_values[ name ]
                    if isinstance( value, Dictifiable ):
                        value = value.to_dict()
                    t_input[ 'value' ] = value

        return tool_dict

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

                track_data_provider = trans.app.data_provider_registry.get_data_provider( trans,
                                                                                          original_dataset=dataset,
                                                                                          source='data' )
                return {
                    "track_type": dataset.datatype.track_type,
                    "dataset": trans.security.encode_dict_ids( dataset.to_dict() ),
                    "prefs": prefs,
                    "mode": track_dict.get( 'mode', 'Auto' ),
                    "filters": track_dict.get( 'filters', { 'filters' : track_data_provider.get_filters() } ),
                    "tool": self.get_tool_def( trans, dataset ),
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
        track_data_provider = trans.app.data_provider_registry.get_data_provider( trans, original_dataset=dataset )

        if isinstance( dataset, trans.app.model.HistoryDatasetAssociation ):
            hda_ldda = "hda"
        elif isinstance( dataset, trans.app.model.LibraryDatasetDatasetAssociation ):
            hda_ldda = "ldda"

        # Get track definition.
        return {
            "track_type": dataset.datatype.track_type,
            "name": dataset.name,
            "dataset": trans.security.encode_dict_ids( dataset.to_dict() ),
            "prefs": {},
            "filters": { 'filters' : track_data_provider.get_filters() },
            "tool": self.get_tool_def( trans, dataset ),
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
            #TODO: if this is to stay in the mixin, UsesAnnotations should be added to the superclasses
            #   right now this is depending on the classes that include this mixin to have UsesAnnotations
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


class UsesStoredWorkflowMixin( SharableItemSecurityMixin, UsesAnnotations ):
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
            self.security_check( trans, workflow, check_ownership, check_accessible )

            # Older workflows may be missing slugs, so set them here.
            if not workflow.slug:
                self.create_item_slug( trans.sa_session, workflow )
                trans.sa_session.flush()

        return workflow

    def get_stored_workflow_steps( self, trans, stored_workflow ):
        """ Restores states for a stored workflow's steps. """
        module_injector = WorkflowModuleInjector( trans )
        for step in stored_workflow.latest_workflow.steps:
            try:
                module_injector.inject( step )
            except MissingToolException:
                # Now upgrade_messages is a string instead of a dict, why?
                step.upgrade_messages = "Unknown Tool ID"

    def _import_shared_workflow( self, trans, stored):
        """ """
        # Copy workflow.
        imported_stored = model.StoredWorkflow()
        imported_stored.name = "imported: " + stored.name
        imported_stored.latest_workflow = stored.latest_workflow
        imported_stored.user = trans.user
        # Save new workflow.
        session = trans.sa_session
        session.add( imported_stored )
        session.flush()

        # Copy annotations.
        self.copy_item_annotation( session, stored.user, stored, imported_stored.user, imported_stored )
        for order_index, step in enumerate( stored.latest_workflow.steps ):
            self.copy_item_annotation( session, stored.user, step, \
                                        imported_stored.user, imported_stored.latest_workflow.steps[order_index] )
        session.flush()
        return imported_stored

    def _workflow_from_dict( self, trans, data, source=None, add_to_menu=False, publish=False ):
        """
        Creates a workflow from a dict. Created workflow is stored in the database and returned.
        """

        # Put parameters in workflow mode
        trans.workflow_building_mode = True
        # Create new workflow from incoming dict
        workflow = model.Workflow()
        # If there's a source, put it in the workflow name.
        if source:
            name = "%s (imported from %s)" % ( data['name'], source )
        else:
            name = data['name']
        workflow.name = name
        # Assume no errors until we find a step that has some
        workflow.has_errors = False
        # Create each step
        steps = []
        # The editor will provide ids for each step that we don't need to save,
        # but do need to use to make connections
        steps_by_external_id = {}
        # Keep track of tools required by the workflow that are not available in
        # the local Galaxy instance.  Each tuple in the list of missing_tool_tups
        # will be ( tool_id, tool_name, tool_version ).
        missing_tool_tups = []
        supplied_steps = data[ 'steps' ]
        # Try to iterate through imported workflow in such a way as to
        # preserve step order.
        step_indices = supplied_steps.keys()
        try:
            step_indices = sorted( step_indices, key=int )
        except ValueError:
            # to defensive, were these ever or will they ever not be integers?
            pass
        # First pass to build step objects and populate basic values
        for step_index in step_indices:
            step_dict = supplied_steps[ step_index ]
            # Create the model class for the step
            step = model.WorkflowStep()
            steps.append( step )
            steps_by_external_id[ step_dict['id' ] ] = step
            # FIXME: Position should be handled inside module
            step.position = step_dict['position']
            module = module_factory.from_dict( trans, step_dict, secure=False )
            module.save_to_step( step )
            if module.type == 'tool' and module.tool is None:
                # A required tool is not available in the local Galaxy instance.
                missing_tool_tup = ( step_dict[ 'tool_id' ], step_dict[ 'name' ], step_dict[ 'tool_version' ] )
                if missing_tool_tup not in missing_tool_tups:
                    missing_tool_tups.append( missing_tool_tup )
                # Save the entire step_dict in the unused config field, be parsed later
                # when we do have the tool
                step.config = dumps(step_dict)
            if step.tool_errors:
                workflow.has_errors = True
            # Stick this in the step temporarily
            step.temp_input_connections = step_dict['input_connections']
            # Save step annotation.
            annotation = step_dict[ 'annotation' ]
            if annotation:
                annotation = sanitize_html( annotation, 'utf-8', 'text/html' )
                self.add_item_annotation( trans.sa_session, trans.get_user(), step, annotation )
        # Second pass to deal with connections between steps
        for step in steps:
            # Input connections
            for input_name, conn_list in step.temp_input_connections.iteritems():
                if not conn_list:
                    continue
                if not isinstance(conn_list, list):  # Older style singleton connection
                    conn_list = [conn_list]
                for conn_dict in conn_list:
                    conn = model.WorkflowStepConnection()
                    conn.input_step = step
                    conn.input_name = input_name
                    conn.output_name = conn_dict['output_name']
                    conn.output_step = steps_by_external_id[ conn_dict['id'] ]
            del step.temp_input_connections

        # Order the steps if possible
        attach_ordered_steps( workflow, steps )

        # Connect up
        stored = model.StoredWorkflow()
        stored.name = workflow.name
        workflow.stored_workflow = stored
        stored.latest_workflow = workflow
        stored.user = trans.user
        stored.published = publish
        if data[ 'annotation' ]:
            self.add_item_annotation( trans.sa_session, stored.user, stored, data[ 'annotation' ] )

        # Persist
        trans.sa_session.add( stored )
        trans.sa_session.flush()

        if add_to_menu:
            if trans.user.stored_workflow_menu_entries == None:
                trans.user.stored_workflow_menu_entries = []
            menuEntry = model.StoredWorkflowMenuEntry()
            menuEntry.stored_workflow = stored
            trans.user.stored_workflow_menu_entries.append( menuEntry )
            trans.sa_session.flush()

        return stored, missing_tool_tups

    def _workflow_to_dict( self, trans, stored ):
        """
        Converts a workflow to a dict of attributes suitable for exporting.
        """
        workflow = stored.latest_workflow
        workflow_annotation = self.get_item_annotation_obj( trans.sa_session, trans.user, stored )
        annotation_str = ""
        if workflow_annotation:
            annotation_str = workflow_annotation.annotation
        # Pack workflow data into a dictionary and return
        data = {}
        data['a_galaxy_workflow'] = 'true' # Placeholder for identifying galaxy workflow
        data['format-version'] = "0.1"
        data['name'] = workflow.name
        data['annotation'] = annotation_str
        if workflow.uuid is not None:
            data['uuid'] = str(workflow.uuid)  
        data['steps'] = {}
        # For each step, rebuild the form and encode the state
        for step in workflow.steps:
            # Load from database representation
            module = module_factory.from_workflow_step( trans, step )
            if not module:
                return None
            # Get user annotation.
            step_annotation = self.get_item_annotation_obj(trans.sa_session, trans.user, step )
            annotation_str = ""
            if step_annotation:
                annotation_str = step_annotation.annotation
            # Step info
            step_dict = {
                'id': step.order_index,
                'type': module.type,
                'tool_id': module.get_tool_id(),
                'tool_version' : step.tool_version,
                'name': module.get_name(),
                'tool_state': module.get_state( secure=False ),
                'tool_errors': module.get_errors(),
                ## 'data_inputs': module.get_data_inputs(),
                ## 'data_outputs': module.get_data_outputs(),
                'annotation' : annotation_str
            }
            # Add post-job actions to step dict.
            if module.type == 'tool':
                pja_dict = {}
                for pja in step.post_job_actions:
                    pja_dict[pja.action_type+pja.output_name] = dict( action_type = pja.action_type,
                                                                      output_name = pja.output_name,
                                                                      action_arguments = pja.action_arguments )
                step_dict[ 'post_job_actions' ] = pja_dict
            # Data inputs
            step_dict['inputs'] = module.get_runtime_input_dicts( annotation_str )
            # User outputs
            step_dict['user_outputs'] = []
            """
            module_outputs = module.get_data_outputs()
            step_outputs = trans.sa_session.query( WorkflowOutput ).filter( step=step )
            for output in step_outputs:
                name = output.output_name
                annotation = ""
                for module_output in module_outputs:
                    if module_output.get( 'name', None ) == name:
                        output_type = module_output.get( 'extension', '' )
                        break
                data['outputs'][name] = { 'name' : name, 'annotation' : annotation, 'type' : output_type }
            """

            # All step outputs
            step_dict['outputs'] = []
            if type( module ) is ToolModule:
                for output in module.get_data_outputs():
                    step_dict['outputs'].append( { 'name' : output['name'], 'type' : output['extensions'][0] } )
            # Connections
            input_connections = step.input_connections
            if step.type is None or step.type == 'tool':
                # Determine full (prefixed) names of valid input datasets
                data_input_names = {}

                def callback( input, value, prefixed_name, prefixed_label ):
                    if isinstance( input, DataToolParameter ) or isinstance( input, DataCollectionToolParameter ):
                        data_input_names[ prefixed_name ] = True
                # FIXME: this updates modules silently right now; messages from updates should be provided.
                module.check_and_update_state()
                visit_input_values( module.tool.inputs, module.state.inputs, callback )
                # Filter
                # FIXME: this removes connection without displaying a message currently!
                input_connections = [ conn for conn in input_connections if conn.input_name in data_input_names ]
            # Encode input connections as dictionary
            input_conn_dict = {}
            unique_input_names = set( [conn.input_name for conn in input_connections] )
            for input_name in unique_input_names:
                input_conn_dict[ input_name ] = \
                    [ dict( id=conn.output_step.order_index, output_name=conn.output_name ) for conn in input_connections if conn.input_name == input_name ]
            # Preserve backward compatability. Previously Galaxy
            # assumed input connections would be dictionaries not
            # lists of dictionaries, so replace any singleton list
            # with just the dictionary so that workflows exported from
            # newer Galaxy instances can be used with older Galaxy
            # instances if they do no include multiple input
            # tools. This should be removed at some point. Mirrored
            # hack in _workflow_from_dict should never be removed so
            # existing workflow exports continue to function.
            for input_name, input_conn in dict(input_conn_dict).iteritems():
                if len(input_conn) == 1:
                    input_conn_dict[input_name] = input_conn[0]
            step_dict['input_connections'] = input_conn_dict
            # Position
            step_dict['position'] = step.position
            # Add to return value
            data['steps'][step.order_index] = step_dict
        return data


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
                        # A LibraryFolder is a special case because if it inherited the template from its parent,
                        # we want to set inheritable to True for its info_association.  This allows for the default
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
            if trans.sa_session.query( item.__class__ ).filter_by( user=item.user, slug=new_slug ).count() == 0:
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
            slug_base = util.ready_name_for_url( item_name.lower() )
        else:
            slug_base = cur_slug

        # Using slug base, find a slug that is not taken. If slug is taken,
        # add integer to end.
        new_slug = slug_base
        count = 1
        # Ensure unique across model class and user and don't include this item
        # in the check in case it has previously been assigned a valid slug.
        while sa_session.query( item.__class__ ).filter( item.__class__.user == item.user, item.__class__.slug == new_slug, item.__class__.id != item.id).count() != 0:
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


class UsesTagsMixin( SharableItemSecurityMixin ):

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

    def set_tags_from_list( self, trans, item, new_tags_list, user=None ):
        # Method deprecated - try to use TagsHandler instead.
        tags_manager = tags.TagsManager( trans.app )
        return tags_manager.set_tags_from_list( trans, item, new_tags_list, user=user )

    def get_user_tags_used( self, trans, user=None ):
        """
        Return a list of distinct 'user_tname:user_value' strings that the
        given user has used.

        user defaults to trans.user.
        Returns an empty list if no user is given and trans.user is anonymous.
        """
        #TODO: for lack of a UsesUserMixin - placing this here - maybe into UsesTags, tho
        user = user or trans.user
        if not user:
            return []

        # get all the taggable model TagAssociations
        tag_models = [ v.tag_assoc_class for v in trans.app.tag_handler.item_tag_assoc_info.values() ]
        # create a union of subqueries for each for this user - getting only the tname and user_value
        all_tags_query = None
        for tag_model in tag_models:
            subq = ( trans.sa_session.query( tag_model.user_tname, tag_model.user_value )
                        .filter( tag_model.user == trans.user ) )
            all_tags_query = subq if all_tags_query is None else all_tags_query.union( subq )

        # if nothing init'd the query, bail
        if all_tags_query is None:
            return []

        # boil the tag tuples down into a sorted list of DISTINCT name:val strings
        tags = all_tags_query.distinct().all()
        tags = [( ( name + ':' + val ) if val else name ) for name, val in tags ]
        return sorted( tags )



class UsesExtendedMetadataMixin( SharableItemSecurityMixin ):
    """ Mixin for getting and setting item extended metadata. """

    def get_item_extended_metadata_obj( self, trans, item ):
        """
        Given an item object (such as a LibraryDatasetDatasetAssociation), find the object
        of the associated extended metadata
        """
        if item.extended_metadata:
            return item.extended_metadata
        return None

    def set_item_extended_metadata_obj( self, trans, item, extmeta_obj, check_writable=False):
        if item.__class__ == LibraryDatasetDatasetAssociation:
            if not check_writable or trans.app.security_agent.can_modify_library_item( trans.get_current_user_roles(), item, trans.user ):
                item.extended_metadata = extmeta_obj
                trans.sa_session.flush()
        if item.__class__ == HistoryDatasetAssociation:
            history = None
            if check_writable:
                history = self.security_check( trans, item, check_ownership=True, check_accessible=True )
            else:
                history = self.security_check( trans, item, check_ownership=False, check_accessible=True )
            if history:
                item.extended_metadata = extmeta_obj
                trans.sa_session.flush()

    def unset_item_extended_metadata_obj( self, trans, item, check_writable=False):
        if item.__class__ == LibraryDatasetDatasetAssociation:
            if not check_writable or trans.app.security_agent.can_modify_library_item( trans.get_current_user_roles(), item, trans.user ):
                item.extended_metadata = None
                trans.sa_session.flush()
        if item.__class__ == HistoryDatasetAssociation:
            history = None
            if check_writable:
                history = self.security_check( trans, item, check_ownership=True, check_accessible=True )
            else:
                history = self.security_check( trans, item, check_ownership=False, check_accessible=True )
            if history:
                item.extended_metadata = None
                trans.sa_session.flush()

    def create_extended_metadata(self, trans, extmeta):
        """
        Create/index an extended metadata object. The returned object is
        not associated with any items
        """
        ex_meta = ExtendedMetadata(extmeta)
        trans.sa_session.add( ex_meta )
        trans.sa_session.flush()
        for path, value in self._scan_json_block(extmeta):
            meta_i = ExtendedMetadataIndex(ex_meta, path, value)
            trans.sa_session.add(meta_i)
        trans.sa_session.flush()
        return ex_meta

    def delete_extended_metadata( self, trans, item):
        if item.__class__ == ExtendedMetadata:
            trans.sa_session.delete( item )
            trans.sa_session.flush()

    def _scan_json_block(self, meta, prefix=""):
        """
        Scan a json style data structure, and emit all fields and their values.
        Example paths

        Data
        { "data" : [ 1, 2, 3 ] }

        Path:
        /data == [1,2,3]

        /data/[0] == 1

        """
        if isinstance(meta, dict):
            for a in meta:
                for path, value in self._scan_json_block(meta[a], prefix + "/" + a):
                    yield path, value
        elif isinstance(meta, list):
            for i, a in enumerate(meta):
                for path, value in self._scan_json_block(a, prefix + "[%d]" % (i)):
                    yield path, value
        else:
            #BUG: Everything is cast to string, which can lead to false positives
            #for cross type comparisions, ie "True" == True
            yield prefix, ("%s" % (meta)).encode("utf8", errors='replace')


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
