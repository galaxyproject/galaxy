from galaxy.managers.context import (
    ProvidesAppContext,
    ProvidesUserContext,
    ProvidesHistoryContext
)


class WorkRequestContext( ProvidesAppContext, ProvidesUserContext, ProvidesHistoryContext ):
    """ Stripped down implementation of Galaxy web transaction god object for
    work request handling outside of web threads - uses mix-ins shared with
    GalaxyWebTransaction to provide app, user, and history context convience
    methods - but nothing related to HTTP handling, mako views, etc....

    Things that only need app shouldn't be consuming trans - but there is a
    need for actions potentially tied to users and histories and  hopefully
    this can define that stripped down interface providing access to user and
    history information - but not dealing with web request and response
    objects.
    """

    def __init__( self, app, user=None, history=None, workflow_building_mode=False ):
        self.app = app
        self.security = app.security
        self.__user = user
        self.__history = history
        self.api_inherit_admin = False
        self.workflow_building_mode = workflow_building_mode

    def get_history( self, create=False ):
        if create:
            raise NotImplementedError( "Cannot create histories from a work request context." )
        return self.__history

    def set_history( self ):
        raise NotImplementedError( "Cannot change histories from a work request context." )

    history = property( get_history, set_history )

    def get_user( self ):
        """Return the current user if logged in or None."""
        return self.__user

    def set_user( self, user ):
        """Set the current user."""
        raise NotImplementedError( "Cannot change users from a work request context." )

    user = property( get_user, set_user )
