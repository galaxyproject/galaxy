from galaxy.web.base.controller import *
from galaxy.web.framework.helpers.grids import *
import webhelpers
from datetime import datetime
from cgi import escape

log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

def time_ago( x ):
    return webhelpers.date.distance_of_time_in_words( x, datetime.utcnow() )

def iff( a, b, c ):
    if a:
        return b
    else:
        return c

class HistoryListGrid( Grid ):
    
    title = "Stored histories"
    model_class = model.History
    default_sort_key = "-create_time"
    columns = [
        GridColumn( "Name", key="name",
                    link=( lambda item: iff( item.deleted, None, dict( operation="switch", id=item.id ) ) ),
                    attach_popup=True ),
        GridColumn( "Datasets (by state)", method='_build_datasets_by_state' ),
        GridColumn( "Status", method='_build_status' ),
        GridColumn( "Age", key="create_time", format=time_ago ),
        GridColumn( "Last update", key="update_time", format=time_ago ),
        # Valid for filtering but invisible
        GridColumn( "Deleted", key="deleted", visible=False )
    ]
    operations = [
        GridOperation( "Switch", allow_multiple=False, condition=( lambda item: not item.deleted ) ),
        GridOperation( "Share", condition=( lambda item: not item.deleted )  ),
        GridOperation( "Rename", condition=( lambda item: not item.deleted )  ),
        GridOperation( "Delete", condition=( lambda item: not item.deleted ) ),
        GridOperation( "Undelete", condition=( lambda item: item.deleted ) )
    ]
    standard_filters = [
        GridColumnFilter( "Active", args=dict( deleted=False ) ),
        GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    default_filter = dict( deleted=False )
    
    def get_current_item( self, trans ):
        return trans.history
    
    def apply_default_filter( self, trans, query ):
        return query.filter_by( user=trans.user, purged=False )
            
    def handle_operation( self, trans, operation, history_ids ):
        # Display no message by default
        status, message = None, None
        refresh_history = False
        # Load the histories and ensure they all belong to the current user
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
        operation = operation.lower()
        if operation == "switch":
            status, message = self._list_switch( trans, histories )
            refresh_history = True
        elif operation == "share":
            ## Caught above for now
            pass
        elif operation == "rename":
            ## Caught above for now
            pass
        elif operation == "delete":
            status, message = self._list_delete( trans, histories )
        elif operation == "undelete":
            status, message = self._list_undelete( trans, histories )
        trans.sa_session.flush()
        # Render the list view
        return status, message
    
    def _build_datasets_by_state( self, trans, history ):
        rval = []
        for state in ( 'ok', 'running', 'queued', 'error' ):
            total = sum( 1 for d in history.active_datasets if d.state == state )
            if total:
                rval.append( '<div class="count-box state-color-%s">%s</div>' % ( state, total ) )
            else:
                rval.append( '<div class="count-box-dummy"></div>' )
        return "\n".join( rval )
        
    def _build_status( self, trans, history ):
        if history.deleted:
            return "deleted"
        return ""
    
    def _list_delete( self, trans, histories ):
        """Delete histories"""
        n_deleted = 0
        deleted_current = False
        for history in histories:
            if not history.deleted:
                # Delete DefaultHistoryPermissions
                for dhp in history.default_permissions:
                    dhp.delete()
                    dhp.flush()
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
            
    _list_grid = HistoryListGrid()
    
    @web.expose
    @web.require_login( "work with multiple histories" )
    def list( self, trans, *args, **kwargs ):
        """
        List all available histories
        """
        # TODO: these two operations need to be updates still
        operation = kwargs.get( 'operation', None )
        if operation:
            operation = operation.lower()
        if operation == "share":
            return self.share( trans, **kwargs )
        elif operation == "rename":
            return self.rename( trans, **kwargs )
        return self._list_grid( trans, *args, **kwargs )
    
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
    
    ## These have been moved from 'root' but not cleaned up
    
    @web.expose
    @web.require_login( "share histories with other users" )
    def share( self, trans, id=None, email="", **kwd ):
        send_to_err = ""
        if not id:
            id = trans.get_history().id
        if not isinstance( id, list ):
            id = [ id ]
        histories = []
        history_names = []
        for hid in id:
            histories.append( trans.app.model.History.get( hid ) )
            history_names.append(histories[-1].name) 
        if not email:
            return trans.fill_template("/history/share.mako", histories=histories, email=email, send_to_err=send_to_err)
        user = trans.get_user()  
        send_to_user = trans.app.model.User.filter( trans.app.model.User.table.c.email==email ).first()
        params = util.Params( kwd )
        action = params.get( 'action', None )
        if action == "no_share":
            trans.response.send_redirect( url_for( action='history_options' ) )
        if not send_to_user:
            send_to_err = "No such user"
        elif user.email == email:
            send_to_err = "You can't send histories to yourself"
        else:
            if 'history_share_btn' in kwd or action != 'share':
                # The user is attempting to share a history whose datasets cannot all be accessed by the other user.  In this case,
                # the user sharing the history can chose to make the datasets public ( action == 'public' ) if he has the authority
                # to do so, or automatically create a new "sharing role" that allows the user to share his private datasets only with the 
                # desired user ( action == 'private' ).
                can_change = {}
                cannot_change = {}
                for history in histories:
                    for hda in history.activatable_datasets:
                        # Only deal with datasets that have not been purged
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
                                                cannot_change=cannot_change )
            for history in histories:
                new_history = history.copy( target_user=send_to_user )
                new_history.name = history.name + " from " + user.email
                new_history.user_id = send_to_user.id
                trans.log_event( "History share, id: %s, name: '%s': to new id: %s" % ( str( history.id ), history.name, str( new_history.id ) ) )
            self.app.model.flush()
            return trans.show_message( "History (%s) has been shared with: %s" % ( ",".join( history_names ),email ) )
        return trans.fill_template( "/history/share.mako", histories=histories, email=email, send_to_err=send_to_err )
        
    @web.expose
    @web.require_login( "rename histories" )
    def rename( self, trans, id=None, name=None, **kwd ):
        if trans.app.memory_usage:
            # Keep track of memory usage
            m0 = self.app.memory_usage.memory()
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
        if self.app.memory_usage:
            m1 = trans.app.memory_usage.memory( m0, pretty=True )
            log.info( "End of root/history_rename, memory used increased by %s"  % m1 )
        return trans.show_message( "<p>%s" % change_msg, refresh_frames=['history'] ) 