from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy import util
from galaxy.model.mapping import desc
from galaxy.model.orm import *
from galaxy.util.json import *
from galaxy.util.odict import odict
from galaxy.tags.tag_handler import TagHandler
from sqlalchemy.sql.expression import ClauseElement
import webhelpers, logging, operator
from datetime import datetime
from cgi import escape

log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

class HistoryListGrid( grids.Grid ):
    # Custom column types
    class NameColumn( grids.TextColumn ):
        def get_value(self, trans, grid, history):
            return history.get_display_name()
            
    class DatasetsByStateColumn( grids.GridColumn ):
        def get_value( self, trans, grid, history ):
            rval = []
            for state in ( 'ok', 'running', 'queued', 'error' ):
                total = sum( 1 for d in history.active_datasets if d.state == state )
                if total:
                    rval.append( '<div class="count-box state-color-%s">%s</div>' % ( state, total ) )
                else:
                    rval.append( '' )
            return rval
            
    class StatusColumn( grids.GridColumn ):
        def get_value( self, trans, grid, history ):
            if history.deleted:
                return "deleted"
            elif history.users_shared_with:
                return "shared"
            elif history.importable:
                return "importable"
            return ""
        def get_link( self, trans, grid, item ):
            if item.users_shared_with or item.importable:
                return dict( operation="sharing" )
            return None
                
    class DeletedColumn( grids.GridColumn ):
       def get_accepted_filters( self ):
           """ Returns a list of accepted filters for this column. """
           accepted_filter_labels_and_vals = { "active" : "False", "deleted" : "True", "all": "All" }
           accepted_filters = []
           for label, val in accepted_filter_labels_and_vals.items():
               args = { self.key: val }
               accepted_filters.append( grids.GridColumnFilter( label, args) )
           return accepted_filters
           
    class SharingColumn( grids.GridColumn ):
        def filter( self, db_session, query, column_filter ):
            """ Modify query to filter histories by sharing status. """
            if column_filter == "All":
                pass
            elif column_filter:
                if column_filter == "private":
                    query = query.filter( model.History.users_shared_with == None )
                    query = query.filter( model.History.importable == False )
                elif column_filter == "shared":
                    query = query.filter( model.History.users_shared_with != None )
                elif column_filter == "importable":
                    query = query.filter( model.History.importable == True )
            return query
        def get_accepted_filters( self ):
            """ Returns a list of accepted filters for this column. """
            accepted_filter_labels_and_vals = odict()
            accepted_filter_labels_and_vals["private"] = "private"
            accepted_filter_labels_and_vals["shared"] = "shared"
            accepted_filter_labels_and_vals["importable"] = "importable"
            accepted_filter_labels_and_vals["all"] = "All"
            accepted_filters = []
            for label, val in accepted_filter_labels_and_vals.items():
                args = { self.key: val }
                accepted_filters.append( grids.GridColumnFilter( label, args) )
            return accepted_filters

    # Grid definition
    title = "Saved Histories"
    model_class = model.History
    template='/history/grid.mako'
    default_sort_key = "-create_time"
    columns = [
        NameColumn( "Name", key="name", model_class=model.History,
                          link=( lambda history: iff( history.deleted, None, dict( operation="switch", id=history.id ) ) ),
                          attach_popup=True, filterable="advanced" ),
        DatasetsByStateColumn( "Datasets (by state)", ncells=4 ),
        grids.TagsColumn( "Tags", "tags", model.History, model.HistoryTagAssociation, filterable="advanced"),
        StatusColumn( "Status", attach_popup=False ),
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        # Columns that are valid for filtering but are not visible.
        DeletedColumn( "Deleted", key="deleted", visible=False, filterable="advanced" ),
        SharingColumn( "Shared", key="shared", visible=False, filterable="advanced" ),
    ]
    columns.append( 
        grids.MulticolFilterColumn(  
        "Search", 
        cols_to_filter=[ columns[0], columns[2] ], 
        key="free-text-search", visible=False, filterable="standard" )
                )
                
    operations = [
        grids.GridOperation( "Switch", allow_multiple=False, condition=( lambda item: not item.deleted ) ),
        grids.GridOperation( "Share", condition=( lambda item: not item.deleted )  ),
        grids.GridOperation( "Unshare", condition=( lambda item: not item.deleted )  ),
        grids.GridOperation( "Rename", condition=( lambda item: not item.deleted )  ),
        grids.GridOperation( "Delete", condition=( lambda item: not item.deleted ) ),
        grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) ),
        grids.GridOperation( "Enable import via link", condition=( lambda item: item.deleted ) ),
        grids.GridOperation( "Disable import via link", condition=( lambda item: item.deleted ) )
    ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) ),
    ]
    default_filter = dict( name="All", deleted="False", tags="All", shared="All" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def get_current_item( self, trans ):
        return trans.get_history()
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter_by( user=trans.user, purged=False )

class SharedHistoryListGrid( grids.Grid ):
    # Custom column types
    class DatasetsByStateColumn( grids.GridColumn ):
        def get_value( self, trans, grid, history ):
            rval = []
            for state in ( 'ok', 'running', 'queued', 'error' ):
                total = sum( 1 for d in history.active_datasets if d.state == state )
                if total:
                    rval.append( '<div class="count-box state-color-%s">%s</div>' % ( state, total ) )
                else:
                    rval.append( '' )
            return rval
    class SharedByColumn( grids.GridColumn ):
        def get_value( self, trans, grid, history ):
            return history.user.email
    # Grid definition
    title = "Histories shared with you by others"
    template='/history/grid.mako'
    model_class = model.History
    default_sort_key = "-update_time"
    default_filter = {}
    columns = [
        grids.GridColumn( "Name", key="name" ),
        DatasetsByStateColumn( "Datasets (by state)", ncells=4 ),
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        SharedByColumn( "Shared by", key="user_id" )
    ]
    operations = [
        grids.GridOperation( "Clone" ),
        grids.GridOperation( "Unshare" )
    ]
    standard_filters = []
    def build_initial_query( self, session ):
        return session.query( self.model_class ).join( 'users_shared_with' )
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter( model.HistoryUserShareAssociation.user == trans.user )

class HistoryController( BaseController ):
    @web.expose
    def index( self, trans ):
        return ""
    @web.expose
    def list_as_xml( self, trans ):
        """XML history list for functional tests"""
        return trans.fill_template( "/history/list_as_xml.mako" )
    
    stored_list_grid = HistoryListGrid()
    shared_list_grid = SharedHistoryListGrid()
    
    @web.expose
    @web.require_login( "work with multiple histories" )
    def list( self, trans, **kwargs ):
        """List all available histories"""
        current_history = trans.get_history()
        status = message = None
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "share":
                return self.share( trans, **kwargs )
            if operation == "rename":
                return self.rename( trans, **kwargs )
            history_ids = util.listify( kwargs.get( 'id', [] ) )
            if operation == "sharing":
                return self.sharing( trans, id=history_ids )
            # Display no message by default
            status, message = None, None
            refresh_history = False
            # Load the histories and ensure they all belong to the current user
            histories = []
            for history_id in history_ids:      
                history = get_history( trans, history_id )
                if history:
                    # Ensure history is owned by current user
                    if history.user_id != None and trans.user:
                        assert trans.user.id == history.user_id, "History does not belong to current user"
                    histories.append( history )
                else:
                    log.warn( "Invalid history id '%r' passed to list", history_id )
            if histories:            
                if operation == "switch":
                    status, message = self._list_switch( trans, histories )
                    # Current history changed, refresh history frame
                    trans.template_context['refresh_frames'] = ['history']
                elif operation == "delete":
                    status, message = self._list_delete( trans, histories )
                    if current_history in histories:
                        # Deleted the current history, so a new, empty history was
                        # created automatically, and we need to refresh the history frame
                        trans.template_context['refresh_frames'] = ['history']
                elif operation == "undelete":
                    status, message = self._list_undelete( trans, histories )
                elif operation == "unshare":
                    for history in histories:
                        for husa in trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ) \
                                                    .filter_by( history=history ):
                            trans.sa_session.delete( husa )
                elif operation == "enable import via link":
                    for history in histories:
                        if not history.importable:
                            history.importable = True
                elif operation == "disable import via link":
                    if history_ids:
                        histories = [ get_history( trans, history_id ) for history_id in history_ids ]
                        for history in histories:
                            if history.importable:
                                history.importable = False
                trans.sa_session.flush()
        # Render the list view
        return self.stored_list_grid( trans, status=status, message=message, **kwargs )
    def _list_delete( self, trans, histories ):
        """Delete histories"""
        n_deleted = 0
        deleted_current = False
        message_parts = []
        for history in histories:
            if history.users_shared_with:
                message_parts.append( "History (%s) has been shared with others, unshare it before deleting it.  " % history.name )
            elif not history.deleted:
                # We'll not eliminate any DefaultHistoryPermissions in case we undelete the history later
                history.deleted = True
                # If deleting the current history, make a new current.
                if history == trans.get_history():
                    deleted_current = True
                    trans.new_history()
                trans.log_event( "History (%s) marked as deleted" % history.name )
                n_deleted += 1
        status = SUCCESS
        if n_deleted:
            message_parts.append( "Deleted %d histories.  " % n_deleted )
        if deleted_current:
            message_parts.append( "Your active history was deleted, a new empty history is now active.  " )
            status = INFO
        return ( status, " ".join( message_parts ) )
    def _list_undelete( self, trans, histories ):
        """Undelete histories"""
        n_undeleted = 0
        n_already_purged = 0
        for history in histories:
            if history.purged:
                n_already_purged += 1
            if history.deleted:
                history.deleted = False
                if not history.default_permissions:
                    # For backward compatibility - for a while we were deleting all DefaultHistoryPermissions on
                    # the history when we deleted the history.  We are no longer doing this.
                    # Need to add default DefaultHistoryPermissions in case they were deleted when the history was deleted
                    default_action = trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS
                    private_user_role = trans.app.security_agent.get_private_user_role( history.user )
                    default_permissions = {}
                    default_permissions[ default_action ] = [ private_user_role ]
                    trans.app.security_agent.history_set_default_permissions( history, default_permissions )
                n_undeleted += 1
                trans.log_event( "History (%s) %d marked as undeleted" % ( history.name, history.id ) )
        status = SUCCESS
        message_parts = []
        if n_undeleted:
            message_parts.append( "Undeleted %d histories." % n_undeleted )
        if n_already_purged:
            message_parts.append( "%d histories have already been purged and cannot be undeleted." % n_already_purged )
            status = WARNING
        return status, "".join( message_parts )
    def _list_switch( self, trans, histories ):
        """Switch to a new different history"""
        new_history = histories[0]
        galaxy_session = trans.get_galaxy_session()
        try:
            association = trans.sa_session.query( trans.app.model.GalaxySessionToHistoryAssociation ) \
                                          .filter_by( session_id=galaxy_session.id, history_id=trans.security.decode_id( new_history.id ) ) \
                                          .first()
        except:
            association = None
        new_history.add_galaxy_session( galaxy_session, association=association )
        trans.sa_session.add( new_history )
        trans.sa_session.flush()
        trans.set_history( new_history )
        # No message
        return None, None
    @web.expose
    @web.require_login( "work with shared histories" )
    def list_shared( self, trans, **kwargs ):
        """List histories shared with current user by others"""
        msg = util.restore_text( kwargs.get( 'msg', '' ) )
        status = message = None
        if 'operation' in kwargs:
            ids = util.listify( kwargs.get( 'id', [] ) )
            operation = kwargs['operation'].lower()
            if operation == "clone":
                if not ids:
                    message = "Select a history to clone"
                    return self.shared_list_grid( trans, status='error', message=message, **kwargs )
                # When cloning shared histories, only copy active datasets
                new_kwargs = { 'clone_choice' : 'active' }
                return self.clone( trans, ids, **new_kwargs )
            elif operation == 'unshare':
                if not ids:
                    message = "Select a history to unshare"
                    return self.shared_list_grid( trans, status='error', message=message, **kwargs )
                histories = [ get_history( trans, history_id ) for history_id in ids ]
                for history in histories:
                    # Current user is the user with which the histories were shared
                    association = trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ).filter_by( user=trans.user, history=history ).one()
                    trans.sa_session.delete( association )
                    trans.sa_session.flush()
                message = "Unshared %d shared histories" % len( ids )
                status = 'done'
        # Render the list view
        return self.shared_list_grid( trans, status=status, message=message, **kwargs )
    @web.expose
    def delete_current( self, trans ):
        """Delete just the active history -- this does not require a logged in user."""
        history = trans.get_history()
        if history.users_shared_with:
            return trans.show_error_message( "History (%s) has been shared with others, unshare it before deleting it.  " % history.name )
        if not history.deleted:
            history.deleted = True
            trans.sa_session.add( history )
            trans.sa_session.flush()
            trans.log_event( "History id %d marked as deleted" % history.id )
        # Regardless of whether it was previously deleted, we make a new history active 
        trans.new_history()
        return trans.show_ok_message( "History deleted, a new history is active", refresh_frames=['history'] )
    @web.expose
    def rename_async( self, trans, id=None, new_name=None ):
        history = trans.sa_session.query( model.History ).get( id )
        # Check that the history exists, and is either owned by the current
        # user (if logged in) or the current history
        assert history is not None
        if history.user is None:
            assert history == trans.get_history()
        else:
            assert history.user == trans.user
        # Rename
        history.name = new_name
        trans.sa_session.add( history )
        trans.sa_session.flush()
        
    @web.expose
    def name_autocomplete_data( self, trans, q=None, limit=None, timestamp=None ):
        """Return autocomplete data for history names"""
        user = trans.get_user()
        if not user:
            return

        ac_data = ""
        for history in trans.sa_session.query( model.History ).filter_by( user=user ).filter( func.lower( model.History.name ) .like(q.lower() + "%") ):
            ac_data = ac_data + history.name + "\n"
        return ac_data
        
    @web.expose
    def imp( self, trans, id=None, confirm=False, **kwd ):
        """Import another user's history via a shared URL"""
        msg = ""
        user = trans.get_user()
        user_history = trans.get_history()
        if not id:
            return trans.show_error_message( "You must specify a history you want to import." )
        import_history = get_history( trans, id, check_ownership=False )
        if not import_history:
            return trans.show_error_message( "The specified history does not exist.")
        if not import_history.importable:
            error( "The owner of this history has disabled imports via this link." )
        if user:
            if import_history.user_id == user.id:
                return trans.show_error_message( "You cannot import your own history." )
            new_history = import_history.copy( target_user=user )
            new_history.name = "imported: " + new_history.name
            new_history.user_id = user.id
            galaxy_session = trans.get_galaxy_session()
            try:
                association = trans.sa_session.query( trans.app.model.GalaxySessionToHistoryAssociation ) \
                                              .filter_by( session_id=galaxy_session.id, history_id=new_history.id ) \
                                              .first()
            except:
                association = None
            new_history.add_galaxy_session( galaxy_session, association=association )
            trans.sa_session.add( new_history )
            trans.sa_session.flush()
            if not user_history.datasets:
                trans.set_history( new_history )
            return trans.show_ok_message( """
                History "%s" has been imported. Click <a href="%s">here</a>
                to begin.""" % ( new_history.name, web.url_for( '/' ) ) )
        elif not user_history or not user_history.datasets or confirm:
            new_history = import_history.copy()
            new_history.name = "imported: " + new_history.name
            new_history.user_id = None
            galaxy_session = trans.get_galaxy_session()
            try:
                association = trans.sa_session.query( trans.app.model.GalaxySessionToHistoryAssociation ) \
                                              .filter_by( session_id=galaxy_session.id, history_id=new_history.id ) \
                                              .first()
            except:
                association = None
            new_history.add_galaxy_session( galaxy_session, association=association )
            trans.sa_session.add( new_history )
            trans.sa_session.flush()
            trans.set_history( new_history )
            return trans.show_ok_message( """
                History "%s" has been imported. Click <a href="%s">here</a>
                to begin.""" % ( new_history.name, web.url_for( '/' ) ) )
        return trans.show_warn_message( """
            Warning! If you import this history, you will lose your current
            history. Click <a href="%s">here</a> to confirm.
            """ % web.url_for( id=id, confirm=True ) )
            
    @web.expose
    def view( self, trans, id=None ):
        """View a history. If a history is importable, then it is viewable by any user."""

        # Get history to view.
        if not id:
            return trans.show_error_message( "You must specify a history you want to view." )
        history_to_view = get_history( trans, id, False)

        # Integrity checks.
        if not history_to_view:
            return trans.show_error_message( "The specified history does not exist.")
        # TODO: Use a new flag to determine if history is viewable?
        if not history_to_view.importable:
            error( "The owner of this history has not published this history." )

        # View history.
        query = trans.sa_session.query( model.HistoryDatasetAssociation ) \
                                .filter( model.HistoryDatasetAssociation.history == history_to_view ) \
                                .options( eagerload( "children" ) ) \
                                .join( "dataset" ).filter( model.Dataset.purged == False ) \
                                .options( eagerload_all( "dataset.actions" ) )
        # Do not show deleted datasets.
        query = query.filter( model.HistoryDatasetAssociation.deleted == False )
        user_owns_history = ( trans.get_user() == history_to_view.user )
        return trans.stream_template_mako( "history/view.mako",
                                           history = history_to_view,
                                           datasets = query.all(),
                                           user_owns_history = user_owns_history,
                                           show_deleted = False )
            
    @web.expose
    @web.require_login( "share histories with other users" )
    def share( self, trans, id=None, email="", **kwd ):
        # If a history contains both datasets that can be shared and others that cannot be shared with the desired user,
        # then the entire history is shared, and the protected datasets will be visible, but inaccessible ( greyed out )
        # in the cloned history
        params = util.Params( kwd )
        user = trans.get_user()
        # TODO: we have too many error messages floating around in here - we need
        # to incorporate the messaging system used by the libraries that will display
        # a message on any page.
        err_msg = util.restore_text( params.get( 'err_msg', '' ) )
        if not email:
            if not id:
                # Default to the current history
                id = trans.security.encode_id( trans.history.id )
            id = util.listify( id )
            send_to_err = err_msg
            histories = []
            for history_id in id:
                histories.append( get_history( trans, history_id ) )
            return trans.fill_template( "/history/share.mako",
                                        histories=histories,
                                        email=email,
                                        send_to_err=send_to_err )
        histories, send_to_users, send_to_err = self._get_histories_and_users( trans, user, id, email )
        if not send_to_users:
            if not send_to_err:
                send_to_err += "%s is not a valid Galaxy user.  %s" % ( email, err_msg )
            return trans.fill_template( "/history/share.mako",
                                        histories=histories,
                                        email=email,
                                        send_to_err=send_to_err )
        if params.get( 'share_button', False ):
            # The user has not yet made a choice about how to share, so dictionaries will be built for display
            can_change, cannot_change, no_change_needed, unique_no_change_needed, send_to_err = \
                self._populate_restricted( trans, user, histories, send_to_users, None, send_to_err, unique=True )
            send_to_err += err_msg
            if cannot_change and not no_change_needed and not can_change:
                send_to_err = "The histories you are sharing do not contain any datasets that can be accessed by the users with which you are sharing."
                return trans.fill_template( "/history/share.mako", histories=histories, email=email, send_to_err=send_to_err )
            if can_change or cannot_change:
                return trans.fill_template( "/history/share.mako", 
                                            histories=histories, 
                                            email=email, 
                                            send_to_err=send_to_err, 
                                            can_change=can_change, 
                                            cannot_change=cannot_change,
                                            no_change_needed=unique_no_change_needed )
            if no_change_needed:
                return self._share_histories( trans, user, send_to_err, histories=no_change_needed )
            elif not send_to_err:
                # User seems to be sharing an empty history
                send_to_err = "You cannot share an empty history.  "
        return trans.fill_template( "/history/share.mako", histories=histories, email=email, send_to_err=send_to_err )
    @web.expose
    @web.require_login( "share restricted histories with other users" )
    def share_restricted( self, trans, id=None, email="", **kwd ):
        if 'action' in kwd: 
            action = kwd[ 'action' ]
        else:
            err_msg = "Select an action.  "
            return trans.response.send_redirect( url_for( controller='history',
                                                          action='share',
                                                          id=id,
                                                          email=email,
                                                          err_msg=err_msg,
                                                          share_button=True ) )
        user = trans.get_user()
        user_roles = user.all_roles()
        histories, send_to_users, send_to_err = self._get_histories_and_users( trans, user, id, email )
        send_to_err = ''
        # The user has made a choice, so dictionaries will be built for sharing
        can_change, cannot_change, no_change_needed, unique_no_change_needed, send_to_err = \
            self._populate_restricted( trans, user, histories, send_to_users, action, send_to_err )
        # Now that we've populated the can_change, cannot_change, and no_change_needed dictionaries,
        # we'll populate the histories_for_sharing dictionary from each of them.
        histories_for_sharing = {}
        if no_change_needed:
            # Don't need to change anything in cannot_change, so populate as is
            histories_for_sharing, send_to_err = \
                self._populate( trans, histories_for_sharing, no_change_needed, send_to_err )
        if cannot_change:
            # Can't change anything in cannot_change, so populate as is
            histories_for_sharing, send_to_err = \
                self._populate( trans, histories_for_sharing, cannot_change, send_to_err )
        # The action here is either 'public' or 'private', so we'll continue to populate the
        # histories_for_sharing dictionary from the can_change dictionary.
        for send_to_user, history_dict in can_change.items():
            for history in history_dict:                  
                # Make sure the current history has not already been shared with the current send_to_user
                if trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ) \
                                   .filter( and_( trans.app.model.HistoryUserShareAssociation.table.c.user_id == send_to_user.id, 
                                                  trans.app.model.HistoryUserShareAssociation.table.c.history_id == history.id ) ) \
                                   .count() > 0:
                    send_to_err += "History (%s) already shared with user (%s)" % ( history.name, send_to_user.email )
                else:
                    # Only deal with datasets that have not been purged
                    for hda in history.activatable_datasets:
                        # If the current dataset is not public, we may need to perform an action on it to
                        # make it accessible by the other user.
                        if not trans.app.security_agent.can_access_dataset( send_to_user.all_roles(), hda.dataset ):
                            # The user with which we are sharing the history does not have access permission on the current dataset
                            if trans.app.security_agent.can_manage_dataset( user_roles, hda.dataset ) and not hda.dataset.library_associations:
                                # The current user has authority to change permissions on the current dataset because
                                # they have permission to manage permissions on the dataset and the dataset is not associated 
                                # with a library.
                                if action == "private":
                                    trans.app.security_agent.privately_share_dataset( hda.dataset, users=[ user, send_to_user ] )
                                elif action == "public":
                                    trans.app.security_agent.make_dataset_public( hda.dataset )
                    # Populate histories_for_sharing with the history after performing any requested actions on
                    # it's datasets to make them accessible by the other user.
                    if send_to_user not in histories_for_sharing:
                        histories_for_sharing[ send_to_user ] = [ history ]
                    elif history not in histories_for_sharing[ send_to_user ]:
                        histories_for_sharing[ send_to_user ].append( history )
        return self._share_histories( trans, user, send_to_err, histories=histories_for_sharing )
    def _get_histories_and_users( self, trans, user, id, email ):
        if not id:
            # Default to the current history
            id = trans.security.encode_id( trans.history.id )
        id = util.listify( id )
        send_to_err = ""
        histories = []
        for history_id in id:
            histories.append( get_history( trans, history_id ) )
        send_to_users = []
        for email_address in util.listify( email ):
            email_address = email_address.strip()
            if email_address:
                if email_address == user.email:
                    send_to_err += "You cannot send histories to yourself.  "
                else:
                    send_to_user = trans.sa_session.query( trans.app.model.User ) \
                                                   .filter( and_( trans.app.model.User.table.c.email==email_address,
                                                                  trans.app.model.User.table.c.deleted==False ) ) \
                                                   .first()                                                                      
                    if send_to_user:
                        send_to_users.append( send_to_user )
                    else:
                        send_to_err += "%s is not a valid Galaxy user.  " % email_address
        return histories, send_to_users, send_to_err
    def _populate( self, trans, histories_for_sharing, other, send_to_err ):
        # This method will populate the histories_for_sharing dictionary with the users and
        # histories in other, eliminating histories that have already been shared with the
        # associated user.  No security checking on datasets is performed.
        # If not empty, the histories_for_sharing dictionary looks like:
        # { userA: [ historyX, historyY ], userB: [ historyY ] }
        # other looks like:
        # { userA: {historyX : [hda, hda], historyY : [hda]}, userB: {historyY : [hda]} }
        for send_to_user, history_dict in other.items():
            for history in history_dict:
                # Make sure the current history has not already been shared with the current send_to_user
                if trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ) \
                                   .filter( and_( trans.app.model.HistoryUserShareAssociation.table.c.user_id == send_to_user.id, 
                                                  trans.app.model.HistoryUserShareAssociation.table.c.history_id == history.id ) ) \
                                   .count() > 0:
                    send_to_err += "History (%s) already shared with user (%s)" % ( history.name, send_to_user.email )
                else:
                    # Build the dict that will be used for sharing
                    if send_to_user not in histories_for_sharing:
                        histories_for_sharing[ send_to_user ] = [ history ]
                    elif history not in histories_for_sharing[ send_to_user ]:
                        histories_for_sharing[ send_to_user ].append( history )
        return histories_for_sharing, send_to_err
    def _populate_restricted( self, trans, user, histories, send_to_users, action, send_to_err, unique=False ):
        # The user may be attempting to share histories whose datasets cannot all be accessed by other users.
        # If this is the case, the user sharing the histories can:
        # 1) action=='public': choose to make the datasets public if he is permitted to do so
        # 2) action=='private': automatically create a new "sharing role" allowing protected 
        #    datasets to be accessed only by the desired users
        # This method will populate the can_change, cannot_change and no_change_needed dictionaries, which
        # are used for either displaying to the user, letting them make 1 of the choices above, or sharing
        # after the user has made a choice.  They will be used for display if 'unique' is True, and will look
        # like: {historyX : [hda, hda], historyY : [hda] }
        # For sharing, they will look like:
        # { userA: {historyX : [hda, hda], historyY : [hda]}, userB: {historyY : [hda]} }
        can_change = {}
        cannot_change = {}
        no_change_needed = {}
        unique_no_change_needed = {}
        user_roles = user.all_roles()
        for history in histories:
            for send_to_user in send_to_users:
                # Make sure the current history has not already been shared with the current send_to_user
                if trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ) \
                                   .filter( and_( trans.app.model.HistoryUserShareAssociation.table.c.user_id == send_to_user.id, 
                                                  trans.app.model.HistoryUserShareAssociation.table.c.history_id == history.id ) ) \
                                   .count() > 0:
                    send_to_err += "History (%s) already shared with user (%s)" % ( history.name, send_to_user.email )
                else:
                    # Only deal with datasets that have not been purged
                    for hda in history.activatable_datasets:
                        if trans.app.security_agent.dataset_is_public( hda.dataset ):
                            # The no_change_needed dictionary is a special case.  If both of can_change
                            # and cannot_change are empty, no_change_needed will used for sharing.  Otherwise
                            # unique_no_change_needed will be used for displaying, so we need to populate both.
                            # Build the dictionaries for display, containing unique histories only
                            if history not in unique_no_change_needed:
                                unique_no_change_needed[ history ] = [ hda ]
                            else:
                                unique_no_change_needed[ history ].append( hda )
                            # Build the dictionaries for sharing
                            if send_to_user not in no_change_needed:
                                no_change_needed[ send_to_user ] = {}
                            if history not in no_change_needed[ send_to_user ]:
                                no_change_needed[ send_to_user ][ history ] = [ hda ]
                            else:
                                no_change_needed[ send_to_user ][ history ].append( hda )
                        elif not trans.app.security_agent.can_access_dataset( send_to_user.all_roles(), hda.dataset ):
                            # The user with which we are sharing the history does not have access permission on the current dataset
                            if trans.app.security_agent.can_manage_dataset( user_roles, hda.dataset ) and not hda.dataset.library_associations:
                                # The current user has authority to change permissions on the current dataset because
                                # they have permission to manage permissions on the dataset and the dataset is not associated 
                                # with a library.
                                if unique:
                                    # Build the dictionaries for display, containing unique histories only
                                    if history not in can_change:
                                        can_change[ history ] = [ hda ]
                                    else:
                                        can_change[ history ].append( hda )
                                else:
                                    # Build the dictionaries for sharing
                                    if send_to_user not in can_change:
                                        can_change[ send_to_user ] = {}
                                    if history not in can_change[ send_to_user ]:
                                        can_change[ send_to_user ][ history ] = [ hda ]
                                    else:
                                        can_change[ send_to_user ][ history ].append( hda )
                            else:
                                if action in [ "private", "public" ]:
                                    # The user has made a choice, so 'unique' doesn't apply.  Don't change stuff
                                    # that the user doesn't have permission to change
                                    continue
                                if unique:
                                    # Build the dictionaries for display, containing unique histories only
                                    if history not in cannot_change:
                                        cannot_change[ history ] = [ hda ]
                                    else:
                                        cannot_change[ history ].append( hda )
                                else:
                                    # Build the dictionaries for sharing
                                    if send_to_user not in cannot_change:
                                        cannot_change[ send_to_user ] = {}
                                    if history not in cannot_change[ send_to_user ]:
                                        cannot_change[ send_to_user ][ history ] = [ hda ]
                                    else:
                                        cannot_change[ send_to_user ][ history ].append( hda )
        return can_change, cannot_change, no_change_needed, unique_no_change_needed, send_to_err
    def _share_histories( self, trans, user, send_to_err, histories={} ):
        # histories looks like: { userA: [ historyX, historyY ], userB: [ historyY ] }
        msg = ""
        sent_to_emails = []
        for send_to_user in histories.keys():
            sent_to_emails.append( send_to_user.email )
        emails = ",".join( e for e in sent_to_emails )
        if not histories:
            send_to_err += "No users have been specified or no histories can be sent without changing permissions or associating a sharing role.  "
        else:
            for send_to_user, send_to_user_histories in histories.items():
                shared_histories = []
                for history in send_to_user_histories:
                    share = trans.app.model.HistoryUserShareAssociation()
                    share.history = history
                    share.user = send_to_user
                    trans.sa_session.add( share )
                    trans.sa_session.flush()
                    if history not in shared_histories:
                        shared_histories.append( history )
        if send_to_err:
            msg += send_to_err
        return self.sharing( trans, histories=shared_histories, msg=msg )
        
    @web.expose
    @web.require_login( "share histories with other users" )
    def sharing( self, trans, histories=[], id=None, **kwd ):
        """Performs sharing of histories among users."""
        # histories looks like: [ historyX, historyY ]
        params = util.Params( kwd )
        msg = util.restore_text ( params.get( 'msg', '' ) )
        if id:
            ids = util.listify( id )
            if ids:
                histories = [ get_history( trans, history_id ) for history_id in ids ]
        for history in histories:
            trans.sa_session.add( history )
            if params.get( 'enable_import_via_link', False ):
                history.importable = True
                trans.sa_session.flush()
            elif params.get( 'disable_import_via_link', False ):
                history.importable = False
                trans.sa_session.flush()
            elif params.get( 'unshare_user', False ):
                user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( kwd[ 'unshare_user' ] ) )
                if not user:
                    msg = 'History (%s) does not seem to be shared with user (%s)' % ( history.name, user.email )
                    return trans.fill_template( 'history/sharing.mako', histories=histories, msg=msg, messagetype='error' )
                husas = trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ).filter_by( user=user, history=history ).all()
                if husas:
                    for husa in husas:
                        trans.sa_session.delete( husa )
                        trans.sa_session.flush()
        histories = []
        # Get all histories that have been shared with others
        husas = trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ) \
                                .join( "history" ) \
                                .filter( and_( trans.app.model.History.user == trans.user,
                                               trans.app.model.History.deleted == False ) ) \
                                .order_by( trans.app.model.History.table.c.name )
        for husa in husas:
            history = husa.history
            if history not in histories:
                histories.append( history )
        # Get all histories that are importable
        importables = trans.sa_session.query( trans.app.model.History ) \
                                      .filter_by( user=trans.user, importable=True, deleted=False ) \
                                      .order_by( trans.app.model.History.table.c.name )
        for importable in importables:
            if importable not in histories:
                histories.append( importable )
        # Sort the list of histories by history.name
        histories.sort( key=operator.attrgetter( 'name') )
        return trans.fill_template( 'history/sharing.mako', histories=histories, msg=msg, messagetype='done' )
    @web.expose
    @web.require_login( "rename histories" )
    def rename( self, trans, id=None, name=None, **kwd ):
        user = trans.get_user()
        if not id:
            # Default to the current history
            history = trans.get_history()
            if not history.user:
                return trans.show_error_message( "You must save your history before renaming it." )
            id = trans.security.encode_id( history.id )
        id = util.listify( id )
        name = util.listify( name )
        histories = []
        cur_names = []
        for history_id in id:
            history = get_history( trans, history_id )
            if history and history.user_id == user.id:
                histories.append( history )
                cur_names.append( history.get_display_name() )
        if not name or len( histories ) != len( name ):
            return trans.fill_template( "/history/rename.mako", histories=histories )
        change_msg = ""
        for i in range(len(histories)):
            if histories[i].user_id == user.id:
                if name[i] == histories[i].get_display_name():
                    change_msg = change_msg + "<p>History: "+cur_names[i]+" is already named: "+name[i]+"</p>"
                elif name[i] not in [None,'',' ']:
                    name[i] = escape(name[i])
                    histories[i].name = name[i]
                    trans.sa_session.add( histories[i] )
                    trans.sa_session.flush()
                    change_msg = change_msg + "<p>History: "+cur_names[i]+" renamed to: "+name[i]+"</p>"
                    trans.log_event( "History renamed: id: %s, renamed to: '%s'" % (str(histories[i].id), name[i] ) )
                else:
                    change_msg = change_msg + "<p>You must specify a valid name for History: "+cur_names[i]+"</p>"
            else:
                change_msg = change_msg + "<p>History: "+cur_names[i]+" does not appear to belong to you.</p>"
        return trans.show_message( "<p>%s" % change_msg, refresh_frames=['history'] )
        
    @web.expose
    @web.require_login( "clone shared Galaxy history" )
    def clone( self, trans, id=None, **kwd ):
        """Clone a list of histories"""
        params = util.Params( kwd )
        # If clone_choice was not specified, display form passing along id
        # argument
        clone_choice = params.get( 'clone_choice', None )
        if not clone_choice:
            return trans.fill_template( "/history/clone.mako", id_argument=id )
        # Extract histories for id argument, defaulting to current
        if id is None:
            histories = [ trans.history ]
        else:
            ids = util.listify( id )
            histories = []
            for history_id in ids:
                history = get_history( trans, history_id, check_ownership=False )
                histories.append( history )
        user = trans.get_user()
        for history in histories:
            if history.user == user:
                owner = True
            else:
                if trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ) \
                                   .filter_by( user=user, history=history ) \
                                   .count() == 0:
                    return trans.show_error_message( "The history you are attempting to clone is not owned by you or shared with you.  " )
                owner = False
            name = "Clone of '%s'" % history.name
            if not owner:
                name += " shared by '%s'" % history.user.email
            if clone_choice == 'activatable':
                new_history = history.copy( name=name, target_user=user, activatable=True )
            elif clone_choice == 'active':
                name += " (active items only)"
                new_history = history.copy( name=name, target_user=user )
        if len( histories ) == 1:
            msg = 'Clone with name "%s" is now included in your previously stored histories.' % new_history.name
        else:
            msg = '%d cloned histories are now included in your previously stored histories.' % len( histories )
        return trans.show_ok_message( msg )

## ---- Utility methods -------------------------------------------------------
        
def get_history( trans, id, check_ownership=True ):
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
