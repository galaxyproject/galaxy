from galaxy.web.base.controller import *
import logging

log = logging.getLogger( __name__ )

class HistoryController( BaseController ):
    @web.expose
    def index( self, trans, **kwd ):
        raise 'Unimplemented'
    
    @web.expose
    def set_default_permissions( self, trans, **kwd ):
        """Sets the user's default permissions for the current history"""
        #TODO: allow changing of default roles associated with history
        if trans.user:
            if 'set_permissions' in kwd:
                """The user clicked the set_permissions button on the set_permissions form"""
                history = trans.get_history()
                group_in = []
                group_out = []
                #collect groups as entered by user
                for name, value in kwd.items():
                    if name.startswith( "group_" ):
                        group = trans.app.model.GalaxyGroup.get( name.replace( "group_", "", 1 ) )
                        if not group:
                            return trans.show_error_message( 'You have specified an invalid group.' )
                        if value == 'in':
                            group_in.append( group )
                        else:
                            group_out.append( group )
                if not group_in:
                    return trans.show_error_message( "You must specify at least one default group." )
                cur_groups = [ assoc.group for assoc in history.default_groups ]
                group_in.sort()
                cur_groups.sort()
                if cur_groups != group_in:
                    history.set_default_access( groups = group_in )
                    return trans.show_ok_message( 'Default history permissions have been changed.' )
                else:
                    return trans.show_error_message( "You did not specify any changes to this history's default permissions." )
            return trans.fill_template( 'history/permissions.mako' )
        else:
            #user not logged in, history group must be only public
            return trans.show_error_message( "You must be logged in to change a history's default permissions." )
