"""
Determine if installed tool shed repositories have updates available in their respective tool sheds.
"""
import logging
import threading
from galaxy.util import string_as_bool
import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_util
from galaxy.model.orm import and_

log = logging.getLogger( __name__ )


class UpdateManager( object ):

    def __init__( self, app ):
        self.app = app
        self.context = self.app.install_model.context
        # Ideally only one Galaxy server process should be able to check for repository updates.
        self.running = True
        self.sleeper = Sleeper()
        self.restarter = threading.Thread( target=self.__restarter )
        self.restarter.start()
        self.seconds_to_sleep = int( app.config.hours_between_check * 3600 )

    def __restarter( self ):
        log.info( 'Update manager restarter starting up...' )
        while self.running:
            # Make a call to the tool shed for each installed repository to get the latest status information in the tool shed for the
            # repository.  This information includes items like newer installable repository revisions, current revision updates, whether
            # the repository revision is the latest installable revision, and whether the repository has been deprecated in the tool shed.
            for repository in self.context.query( self.app.install_model.ToolShedRepository ) \
                                          .filter( self.app.install_model.ToolShedRepository.table.c.deleted == False ):
                tool_shed_status_dict = suc.get_tool_shed_status_for_installed_repository( self.app, repository )
                if tool_shed_status_dict:
                    if tool_shed_status_dict != repository.tool_shed_status:
                        repository.tool_shed_status = tool_shed_status_dict
                        self.context.flush()
                else:
                    # The received tool_shed_status_dict is an empty dictionary, so coerce to None.
                    tool_shed_status_dict = None
                    if tool_shed_status_dict != repository.tool_shed_status:
                        repository.tool_shed_status = tool_shed_status_dict
                        self.context.flush()
            self.sleeper.sleep( self.seconds_to_sleep )
        log.info( 'Update manager restarter shutting down...' )

    def shutdown( self ):
        self.running = False
        self.sleeper.wake()


class Sleeper( object ):
    """Provides a 'sleep' method that sleeps for a number of seconds *unless* the notify method is called (from a different thread)."""

    def __init__( self ):
        self.condition = threading.Condition()

    def sleep( self, seconds ):
        self.condition.acquire()
        self.condition.wait( seconds )
        self.condition.release()

    def wake( self ):
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()
