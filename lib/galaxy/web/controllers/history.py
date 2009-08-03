from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy import util
from galaxy.model.mapping import desc
from galaxy.model.orm import *
from galaxy.util.json import *
import webhelpers, logging
from datetime import datetime
from cgi import escape

log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"


class HistoryListGrid( grids.Grid ):
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
    class StatusColumn( grids.GridColumn ):
        def get_value( self, trans, grid, history ):
            if history.deleted:
                return "deleted"
            elif history.users_shared_with:
                return "shared"
            return ""
        def get_link( self, trans, grid, item ):
            if item.users_shared_with:
                return dict( operation="sharing", id=item.id )
            return None
    # Grid definition
    title = "Stored histories"
    model_class = model.History
    default_sort_key = "-create_time"
    columns = [
        grids.GridColumn( "Name", key="name",
                          link=( lambda item: iff( item.deleted, None, dict( operation="switch", id=item.id ) ) ),
                          attach_popup=True ),
        DatasetsByStateColumn( "Datasets (by state)", ncells=4 ),
        StatusColumn( "Status", attach_popup=False ),
        grids.GridColumn( "Age", key="create_time", format=time_ago ),
        grids.GridColumn( "Last update", key="update_time", format=time_ago ),
        # Valid for filtering but invisible
        grids.GridColumn( "Deleted", key="deleted", visible=False )
    ]
    operations = [
        grids.GridOperation( "Switch", allow_multiple=False, condition=( lambda item: not item.deleted ) ),
        grids.GridOperation( "Share", condition=( lambda item: not item.deleted )  ),
        grids.GridOperation( "Rename", condition=( lambda item: not item.deleted )  ),
        grids.GridOperation( "Delete", condition=( lambda item: not item.deleted ) ),
        grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) )
    ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    default_filter = dict( deleted=False )
    def get_current_item( self, trans ):
        return trans.get_history()
    def apply_default_filter( self, trans, query ):
        return query.filter_by( user=trans.user, purged=False )

class HistoryController( BaseController ):
    
    @web.expose
    def index( self, trans ):
        return ""
    @web.expose
    def list_as_xml( self, trans ):
        """XML history list for functional tests"""
        return trans.fill_template( "/history/list_as_xml.mako" )
    
    list_grid = HistoryListGrid()
    
    @web.expose
    @web.require_login( "work with multiple histories" )
    def list( self, trans, **kwargs ):
        """List all available histories"""
        current_history = trans.get_history()
        status = message = None
        if 'operation' in kwargs:
            history_ids = util.listify( kwargs.get( 'id', [] ) )
            histories = []
            shared_by_others = []
            operation = kwargs['operation'].lower()
            if operation == "share":
                return self.share( trans, **kwargs )
            elif operation == "rename":
                return self.rename( trans, **kwargs )
            elif operation == 'sharing':
                return self.sharing( trans, id=kwargs['id'] )
            # Display no message by default
            status, message = None, None
            refresh_history = False
            # Load the histories and ensure they all belong to the current user
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
                trans.sa_session.flush()
        # Render the list view
        return self.list_grid( trans, status=status, message=message, template='/history/grid.mako', **kwargs )
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
            association = trans.app.model.GalaxySessionToHistoryAssociation \
                .filter_by( session_id=galaxy_session.id, history_id=trans.security.decode_id( new_history.id ) ).first()
        except:
            association = None
        new_history.add_galaxy_session( galaxy_session, association=association )
        new_history.flush()
        trans.set_history( new_history )
        # No message
        return None, None
    @web.expose
    def list_shared( self, trans, **kwd ):
        """List histories shared with current user by others"""
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', '' ) )
        shared_by_others = trans.sa_session \
            .query( model.HistoryUserShareAssociation ) \
            .filter_by( user=trans.user ) \
            .join( 'history' ) \
            .filter( model.History.deleted == False ) \
            .order_by( desc( model.History.update_time ) ) \
            .all()
        return trans.fill_template( "/history/list_shared.mako", shared_by_others=shared_by_others, msg=msg, messagetype='done' )
    @web.expose
    def delete_current( self, trans ):
        """Delete just the active history -- this does not require a logged in user."""
        history = trans.get_history()
        if history.users_shared_with:
            return trans.show_error_message( "History (%s) has been shared with others, unshare it before deleting it.  " % history.name )
        if not history.deleted:
            history.deleted = True
            history.flush()
            trans.log_event( "History id %d marked as deleted" % history.id )
        # Regardless of whether it was previously deleted, we make a new history active 
        trans.new_history()
        return trans.show_ok_message( "History deleted, a new history is active", refresh_frames=['history'] )
    @web.expose
    def rename_async( self, trans, id=None, new_name=None ):
        history = model.History.get( id )
        # Check that the history exists, and is either owned by the current
        # user (if logged in) or the current history
        assert history is not None
        if history.user is None:
            assert history == trans.get_history()
        else:
            assert history.user == trans.user
        # Rename
        history.name = new_name
        trans.sa_session.flush()
    @web.expose
    def imp( self, trans, id=None, confirm=False, **kwd ):
        """Import another user's history via a shared URL"""
        msg = ""
        user = trans.get_user()
        user_history = trans.get_history()
        if not id:
            return trans.show_error_message( "You must specify a history you want to import." )
        import_history = get_history( trans, id )
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
                association = trans.app.model.GalaxySessionToHistoryAssociation \
                    .filter_by( session_id=galaxy_session.id, history_id=new_history.id ).first()
            except:
                association = None
            new_history.add_galaxy_session( galaxy_session, association=association )
            new_history.flush()
            if not user_history.datasets:
                trans.set_history( new_history )
            return trans.show_ok_message( """
                History "%s" has been imported. Click <a href="%s">here</a>
                to begin.""" % ( new_history.name, web.url_for( '/' ) ) )
        elif not user_history.datasets or confirm:
            new_history = import_history.copy()
            new_history.name = "imported: " + new_history.name
            new_history.user_id = None
            galaxy_session = trans.get_galaxy_session()
            try:
                association = trans.app.model.GalaxySessionToHistoryAssociation \
                    .filter_by( session_id=galaxy_session.id, history_id=new_history.id ).first()
            except:
                association = None
            new_history.add_galaxy_session( galaxy_session, association=association )
            new_history.flush()
            trans.set_history( new_history )
            return trans.show_ok_message( """
                History "%s" has been imported. Click <a href="%s">here</a>
                to begin.""" % ( new_history.name, web.url_for( '/' ) ) )
        return trans.show_warn_message( """
            Warning! If you import this history, you will lose your current
            history. Click <a href="%s">here</a> to confirm.
            """ % web.url_for( id=id, confirm=True ) )
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
        if action == "no_share":
            trans.response.send_redirect( url_for( controller='root', action='history_options' ) )
        user = trans.get_user()
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
                if trans.app.model.HistoryUserShareAssociation \
                    .filter( and_( trans.app.model.HistoryUserShareAssociation.table.c.user_id == send_to_user.id, 
                                  trans.app.model.HistoryUserShareAssociation.table.c.history_id == history.id ) ) \
                    .count() > 0:
                    send_to_err += "History (%s) already shared with user (%s)" % ( history.name, send_to_user.email )
                else:
                    # Only deal with datasets that have not been purged
                    for hda in history.activatable_datasets:
                        # If the current dataset is not public, we may need to perform an action on it to
                        # make it accessible by the other user.
                        if not trans.app.security_agent.allow_action( send_to_user, 
                                                                      trans.app.security_agent.permitted_actions.DATASET_ACCESS, 
                                                                      dataset=hda ):
                            # The user with which we are sharing the history does not have access permission on the current dataset
                            if trans.app.security_agent.allow_action( user, 
                                                                      trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS, 
                                                                      dataset=hda ) and not hda.dataset.library_associations:
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
                    send_to_user = trans.app.model.User.filter( and_( trans.app.model.User.table.c.email==email_address,
                                                                      trans.app.model.User.table.c.deleted==False ) ).first()                                                                      
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
                if trans.app.model.HistoryUserShareAssociation \
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
        for history in histories:
            for send_to_user in send_to_users:
                # Make sure the current history has not already been shared with the current send_to_user
                if trans.app.model.HistoryUserShareAssociation \
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
                        elif not trans.app.security_agent.allow_action( send_to_user, 
                                                                        trans.app.security_agent.permitted_actions.DATASET_ACCESS, 
                                                                        dataset=hda ):
                            # The user with which we are sharing the history does not have access permission on the current dataset
                            if trans.app.security_agent.allow_action( user, 
                                                                      trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS, 
                                                                      dataset=hda ) and not hda.dataset.library_associations:
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
                    session = trans.sa_session
                    session.save_or_update( share )
                    session.flush()
                    if history not in shared_histories:
                        shared_histories.append( history )
        if send_to_err:
            msg += send_to_err
        return self.sharing( trans, histories=shared_histories, msg=msg )
    @web.expose
    @web.require_login( "share histories with other users" )
    def sharing( self, trans, histories=[], id=None, **kwd ):
        # histories looks like: [ historyX, historyY ]
        params = util.Params( kwd )
        msg = util.restore_text ( params.get( 'msg', '' ) )
        if id:
            histories = [ get_history( trans, id ) ]
        for history in histories:
            if params.get( 'enable_import_via_link', False ):
                history.importable = True
                history.flush()
            elif params.get( 'disable_import_via_link', False ):
                history.importable = False
                history.flush()
            elif params.get( 'unshare_user', False ):
                user = trans.app.model.User.get( trans.security.decode_id( kwd[ 'unshare_user' ] ) )
                if not user:
                    msg = 'History (%s) does not seem to be shared with user (%s)' % ( history.name, user.email )
                    return trans.fill_template( 'history/sharing.mako', histories=histories, msg=msg, messagetype='error' )
                association = trans.app.model.HistoryUserShareAssociation.filter_by( user=user, history=history ).one()
                association.delete()
                association.flush()
            if not id:
                shared_msg = "History (%s) now shared with: %d users.  " % ( history.name, len( history.users_shared_with ) )
                msg = '%s%s' % ( shared_msg, msg )
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
                cur_names.append( history.name )
        if not name or len( histories ) != len( name ):
            return trans.fill_template( "/history/rename.mako", histories=histories )
        change_msg = ""
        for i in range(len(histories)):
            if histories[i].user_id == user.id:
                if name[i] == histories[i].name:
                    change_msg = change_msg + "<p>History: "+cur_names[i]+" is already named: "+name[i]+"</p>"
                elif name[i] not in [None,'',' ']:
                    name[i] = escape(name[i])
                    histories[i].name = name[i]
                    histories[i].flush()
                    change_msg = change_msg + "<p>History: "+cur_names[i]+" renamed to: "+name[i]+"</p>"
                    trans.log_event( "History renamed: id: %s, renamed to: '%s'" % (str(histories[i].id), name[i] ) )
                else:
                    change_msg = change_msg + "<p>You must specify a valid name for History: "+cur_names[i]+"</p>"
            else:
                change_msg = change_msg + "<p>History: "+cur_names[i]+" does not appear to belong to you.</p>"
        return trans.show_message( "<p>%s" % change_msg, refresh_frames=['history'] )
    @web.expose
    @web.require_login( "clone shared Galaxy history" )
    def clone( self, trans, id, **kwd ):
        history = get_history( trans, id, check_ownership=False )
        params = util.Params( kwd )
        clone_choice = params.get( 'clone_choice', None )
        if not clone_choice:
            return trans.fill_template( "/history/clone.mako", history=history )
        user = trans.get_user()
        if history.user == user:
            owner = True
        else:
            if trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ) \
                    .filter_by( user=user, history=history ).count() == 0:
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
        # Render the list view
        return trans.show_ok_message( 'Clone with name "%s" is now included in your list of stored histories.' % new_history.name )

## ---- Utility methods -------------------------------------------------------
        
def get_history( trans, id, check_ownership=True ):
    """Get a History from the database by id, verifying ownership."""
    # Load history from database
    id = trans.security.decode_id( id )
    history = trans.sa_session.query( model.History ).get( id )
    if not history:
        err+msg( "History not found" )
    # Verify ownership
    user = trans.get_user()
    if not user:
        error( "Must be logged in to manage histories" )
    if check_ownership and not( history.user == user ):
        error( "History is not owned by current user" )
    return history
