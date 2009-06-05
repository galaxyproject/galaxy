from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy import util
import webhelpers, logging
from datetime import datetime
from cgi import escape

log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

class HistoryListGrid( grids.Grid ):
    
    title = "Stored histories"
    model_class = model.History
    default_sort_key = "-create_time"
    columns = [
        grids.GridColumn( "Name", key="name",
                    link=( lambda item: iff( item.deleted, None, dict( operation="switch", id=item.id ) ) ),
                    attach_popup=True ),
        grids.GridColumn( "Datasets (by state)", method='_build_datasets_by_state', ncells=4 ),
        grids.GridColumn( "Status", method='_build_status' ),
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
        return trans.history
    
    def apply_default_filter( self, trans, query ):
        return query.filter_by( user=trans.user, purged=False )
                
    def _build_datasets_by_state( self, trans, history ):
        rval = []
        for state in ( 'ok', 'running', 'queued', 'error' ):
            total = sum( 1 for d in history.active_datasets if d.state == state )
            if total:
                rval.append( '<div class="count-box state-color-%s">%s</div>' % ( state, total ) )
            else:
                rval.append( '' )
        return rval
        
    def _build_status( self, trans, history ):
        if history.deleted:
            return "deleted"
        return ""

class HistoryController( BaseController ):
    
    @web.expose
    def index( self, trans ):
        return ""
    @web.expose
    def list_as_xml( self, trans ):
        """
        XML history list for functional tests
        """
        return trans.fill_template( "/history/list_as_xml.mako" )
    
    list_grid = HistoryListGrid()
    
    @web.expose
    @web.require_login( "work with multiple histories" )
    def list( self, trans, **kwargs ):
        """List all available histories"""
        status = message = None
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "share":
                return self.share( trans, **kwargs )
            elif operation == "rename":
                return self.rename( trans, **kwargs )
            # Display no message by default
            status, message = None, None
            refresh_history = False
            # Load the histories and ensure they all belong to the current user
            history_ids = util.listify( kwargs.get( 'id', [] ) )
            histories = []
            for hid in history_ids:            
                history = model.History.get( hid )
                if history:
                    # Ensure history is owned by current user
                    if history.user_id != None and trans.user:
                        assert trans.user.id == history.user_id, "History does not belong to current user"
                    histories.append( history )
                else:
                    log.warn( "Invalid history id '%r' passed to list", hid )
            if histories:            
                if operation == "switch":
                    status, message = self._list_switch( trans, histories )
                    # Current history changed, refresh history frame
                    trans.template_context['refresh_frames'] = ['history']
                elif operation == "delete":
                    status, message = self._list_delete( trans, histories )
                elif operation == "undelete":
                    status, message = self._list_undelete( trans, histories )
                trans.sa_session.flush()
        # Render the list view
        return self.list_grid( trans, status=status, message=message, **kwargs )
    def _list_delete( self, trans, histories ):
        """Delete histories"""
        n_deleted = 0
        deleted_current = False
        for history in histories:
            if not history.deleted:
                # We'll not eliminate any DefaultHistoryPermissions in case we undelete the history later
                # Mark history as deleted in db
                history.deleted = True
                # If deleting the current history, make a new current.
                if history == trans.history:
                    deleted_current = True
                    trans.new_history()
                trans.log_event( "History id %d marked as deleted" % history.id )
                n_deleted += 1
        status = SUCCESS
        message_parts = []
        if n_deleted:
            message_parts.append( "Deleted %d histories." % n_deleted )
        if deleted_current:
            message_parts.append( "Your active history was deleted, a new empty history is now active.")
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
                    # Need to add default DefaultHistoryPermissions since they were deleted when the history was deleted
                    default_action = trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS
                    private_user_role = trans.app.security_agent.get_private_user_role( history.user )
                    default_permissions = {}
                    default_permissions[ default_action ] = [ private_user_role ]
                    trans.app.security_agent.history_set_default_permissions( history, default_permissions )
                n_undeleted += 1
                trans.log_event( "History id %d marked as undeleted" % history.id )
        status = SUCCESS
        message_parts = []
        if n_undeleted:
            message_parts.append( "Undeleted %d histories." % n_undeleted )
        if n_already_purged:
            message_parts.append( "%d have already been purged and cannot be undeleted." % n_already_purged )
            status = WARNING
        return status, "".join( message_parts )
    def _list_switch( self, trans, histories ):
        """Switch to a new different history"""
        new_history = histories[0]
        galaxy_session = trans.get_galaxy_session()
        try:
            association = trans.app.model.GalaxySessionToHistoryAssociation.filter_by( session_id=galaxy_session.id, history_id=new_history.id ).first()
        except:
            association = None
        new_history.add_galaxy_session( galaxy_session, association=association )
        new_history.flush()
        trans.set_history( new_history )
        trans.log_event( "History switched to id: %s, name: '%s'" % (str(new_history.id), new_history.name ) )
        # No message
        return None, None
    @web.expose
    def delete_current( self, trans ):
        """Delete just the active history -- this does not require a logged in user."""
        history = trans.get_history()
        if not history.deleted:
            history.deleted = True
            history.flush()
            trans.log_event( "History id %d marked as deleted" % history.id )
        # Regardless of whether it was previously deleted, we make a new
        # history active 
        trans.new_history()
        return trans.show_ok_message( "History deleted, a new history is active" )
    @web.expose
    def rename_async( self, trans, id=None, new_name=None ):
        history = model.History.get( id )
        # Check that the history exists, and is either owned by the current
        # user (if logged in) or the current history
        assert history is not None
        if history.user is None:
            assert history == trans.history
        else:
            assert history.user == trans.user
        # Rename
        history.name = new_name
        trans.sa_session.flush()
    @web.expose
    def imp( self, trans, id=None, confirm=False, **kwd ):
        # TODO clean this up and make sure functionally correct
        msg = ""
        user = trans.get_user()
        user_history = trans.get_history()
        if not id:
            return trans.show_error_message( "You must specify a history you want to import.")
        id = trans.security.decode_id( id )
        import_history = trans.app.model.History.get( id )
        if not import_history:
            return trans.show_error_message( "The specified history does not exist.")
        if user:
            if import_history.user_id == user.id:
                return trans.show_error_message( "You cannot import your own history.")
            new_history = import_history.copy( target_user=trans.user )
            new_history.name = "imported: "+new_history.name
            new_history.user_id = user.id
            galaxy_session = trans.get_galaxy_session()
            try:
                association = trans.app.model.GalaxySessionToHistoryAssociation.filter_by( session_id=galaxy_session.id, history_id=new_history.id ).first()
            except:
                association = None
            new_history.add_galaxy_session( galaxy_session, association=association )
            new_history.flush()
            if not user_history.datasets:
                trans.set_history( new_history )
            trans.log_event( "History imported, id: %s, name: '%s': " % (str(new_history.id) , new_history.name ) )
            return trans.show_ok_message( """
                History "%s" has been imported. Click <a href="%s">here</a>
                to begin.""" % ( new_history.name, web.url_for( '/' ) ) )
        elif not user_history.datasets or confirm:
            new_history = import_history.copy()
            new_history.name = "imported: "+new_history.name
            new_history.user_id = None
            galaxy_session = trans.get_galaxy_session()
            try:
                association = trans.app.model.GalaxySessionToHistoryAssociation.filter_by( session_id=galaxy_session.id, history_id=new_history.id ).first()
            except:
                association = None
            new_history.add_galaxy_session( galaxy_session, association=association )
            new_history.flush()
            trans.set_history( new_history )
            trans.log_event( "History imported, id: %s, name: '%s': " % (str(new_history.id) , new_history.name ) )
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
        # in the shared history
        params = util.Params( kwd )
        action = params.get( 'action', None )
        if action == "no_share":
            trans.response.send_redirect( url_for( controller='root', action='history_options' ) )
        if not id:
            id = trans.get_history().id
        id = util.listify( id )
        send_to_err = ""
        histories = []
        for hid in id:
            histories.append( trans.app.model.History.get( hid ) )
        if not email:
            return trans.fill_template( "/history/share.mako", histories=histories, email=email, send_to_err=send_to_err )
        user = trans.get_user()
        send_to_users = []
        for email_address in util.listify( email ):
            email_address = email_address.strip()
            if email_address:
                if email_address == user.email:
                    send_to_err += "You can't send histories to yourself.  "
                else:
                    send_to_user = trans.app.model.User.filter( trans.app.model.User.table.c.email==email_address ).first()
                    if send_to_user:
                        send_to_users.append( send_to_user )
                    else:
                        send_to_err += "%s is not a valid Galaxy user.  " % email_address
        if not send_to_users:
            if not send_to_err:
                send_to_err += "%s is not a valid Galaxy user.  " % email
            return trans.fill_template( "/history/share.mako", histories=histories, email=email, send_to_err=send_to_err )
        if params.get( 'share_proceed_button', False ) and action == 'share':
            # We need to filter out all histories that cannot be shared
            filtered_histories = {}
            for history in histories:
                for send_to_user in send_to_users:
                    # Only deal with datasets that have not been purged
                    for hda in history.activatable_datasets:
                        # The history can be shared if it contains at least 1 public dataset or 1 dataset that the
                        # other user can access.  Inaccessible datasets contained in the history will be displayed
                        # in the shared history, but "greyed out", so they cannot be viewed or used.
                        if trans.app.security_agent.dataset_is_public( hda.dataset ) or \
                            trans.app.security_agent.allow_action( send_to_user, 
                                                                    trans.app.security_agent.permitted_actions.DATASET_ACCESS, 
                                                                    dataset=hda ):
                            if send_to_user in filtered_histories:
                                filtered_histories[ send_to_user ].append( history )
                            else:
                                filtered_histories[ send_to_user ] = [ history ]
                            break
            return self._share_histories( trans, user, send_to_users, send_to_err, filtered_histories=filtered_histories )
        elif params.get( 'history_share_btn', False ) or action != 'share':
            # The user is attempting to share histories whose datasets cannot all be accessed by other users.  In this case,
            # the user sharing the histories can:
            # 1) action=='public': chose to make the datasets public if he is permitted to do so
            # 2) action=='private': automatically create a new "sharing role" allowing protected 
            #    datasets to be accessed only by the desired users
            # 3) action=='share': share only what can be shared when no permissions are changed - this case is handled above
            # 4) action=='no_share': Do not share anything - this case is handled above.
            can_change = {}
            cannot_change = {}
            no_change_needed = {}
            for history in histories:
                # Only deal with datasets that have not been purged
                for hda in history.activatable_datasets:
                    if trans.app.security_agent.dataset_is_public( hda.dataset ):
                        if history not in no_change_needed:
                            no_change_needed[ history ] = [ hda ]
                        else:
                            no_change_needed[ history ].append( hda )
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
                            if action == "private":
                                trans.app.security_agent.privately_share_dataset( hda.dataset, users=[ user, send_to_user ] )
                            elif action == "public":
                                trans.app.security_agent.make_dataset_public( hda.dataset )
                            elif history not in can_change:
                                # Build the set of histories / datasets on which the current user has authority
                                # to "manage permissions".  This is used in /history/share.mako
                                can_change[ history ] = [ hda ]
                            else:
                                can_change[ history ].append( hda )
                        else:
                            if action in [ "private", "public" ]:
                                # Don't change stuff that the user doesn't have permission to change
                                continue
                            elif history not in cannot_change:
                                # Build the set of histories / datasets on which the current user does
                                # not have authority to "manage permissions".  This is used in /history/share.mako
                                cannot_change[ history ] = [ hda ]
                            else:
                                cannot_change[ history ].append( hda )
            if can_change or cannot_change:
                return trans.fill_template( "/history/share.mako", 
                                            histories=histories, 
                                            email=email, 
                                            send_to_err=send_to_err, 
                                            can_change=can_change, 
                                            cannot_change=cannot_change,
                                            no_change_needed=no_change_needed )
            return self._share_histories( trans, user, send_to_users, send_to_err, histories=histories )
        return trans.fill_template( "/history/share.mako", histories=histories, email=email, send_to_err=send_to_err )
    def _share_histories( self, trans, user, send_to_users, send_to_err, histories=[], filtered_histories={} ):
        msg = ""
        if not send_to_users:
            msg = "No users have been specified with which to share histories"
        sent_to_emails = []
        for sent_to_user in send_to_users:
            sent_to_emails.append( sent_to_user.email )
        emails = ",".join( e for e in sent_to_emails )
        if not histories and not filtered_histories:
            msg = "No histories can be sent to (%s) without changing dataset permissions associating a sharing role with them" % emails
        elif histories:
            history_names = []
            for history in histories:
                history_names.append( history.name )
                for send_to_user in send_to_users:
                    new_history = history.copy( target_user=send_to_user )
                    new_history.name = history.name + " from " + user.email
                    new_history.user_id = send_to_user.id
                    self.app.model.flush()
            msg = "Histories (%s) have been shared with: %s.  " % ( ",".join( history_names ), emails )
        elif filtered_histories:
            # filtered_histories is a dictionary like: { user: [ history, history ], user: [ history ] }
            for send_to_user, histories in filtered_histories.items():
                history_names = []
                for history in histories:
                    history_names.append( history.name )
                    new_history = history.copy( target_user=send_to_user )
                    new_history.name = history.name + " from " + user.email
                    new_history.user_id = send_to_user.id
                    self.app.model.flush()
                msg += "Histories (%s) have been shared with: %s.  " % ( ",".join( history_names ), send_to_user.email )
        if send_to_err:
            msg += send_to_err
        return trans.show_message( msg )
    @web.expose
    @web.require_login( "rename histories" )
    def rename( self, trans, id=None, name=None, **kwd ):
        user = trans.get_user()
        if not isinstance( id, list ):
            if id != None:
                id = [ id ]
        if not isinstance( name, list ):
            if name != None:
                name = [ name ]
        histories = []
        cur_names = []
        if not id:
            if not trans.get_history().user:
                return trans.show_error_message( "You must save your history before renaming it." )
            id = [trans.get_history().id]
        for history_id in id:
            history = trans.app.model.History.get( history_id )
            if history and history.user_id == user.id:
                histories.append(history)
                cur_names.append(history.name)
        if not name or len(histories)!=len(name):
            return trans.fill_template( "/history/rename.mako",histories=histories )
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
