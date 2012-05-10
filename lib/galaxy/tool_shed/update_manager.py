"""
Determine if installed tool shed repositories have updates available in their respective tool sheds.
"""
import threading, urllib2, logging
from galaxy.util import string_as_bool
from galaxy.util.shed_util import *

log = logging.getLogger( __name__ )

class UpdateManager( object ):
    def __init__( self, app ):
        self.app = app
        self.sa_session = self.app.model.context.current
        # Ideally only one Galaxy server process should be able to check for repository updates.
        self.running = True
        self.sleeper = Sleeper()
        self.restarter = threading.Thread( target=self.__restarter )
        self.restarter.start()
        self.seconds_to_sleep = app.config.hours_between_check * 3600
    def __restarter( self ):
        log.info( 'Update manager restarter starting up...' )
        while self.running:
            flush_needed = False
            for repository in self.sa_session.query( self.app.model.ToolShedRepository ) \
                                             .filter( and_( self.app.model.ToolShedRepository.table.c.update_available == False,
                                                            self.app.model.ToolShedRepository.table.c.deleted == False ) ):
                if self.check_for_update( repository ):
                    repository.update_available = True
                    self.sa_session.add( repository )
                    flush_needed = True
            if flush_needed:
                self.sa_session.flush()
            self.sleeper.sleep( self.seconds_to_sleep )
        log.info( 'Transfer job restarter shutting down...' )
    def check_for_update( self, repository ):
        tool_shed_url = get_url_from_repository_tool_shed( self.app, repository )
        url = '%s/repository/check_for_updates?name=%s&owner=%s&changeset_revision=%s&webapp=update_manager&no_reset=true' % \
            ( tool_shed_url, repository.name, repository.owner, repository.changeset_revision )
        response = urllib2.urlopen( url )
        text = response.read()
        response.close()
        return string_as_bool( text )
    def shutdown( self ):
        self.running = False
        self.sleeper.wake()

class Sleeper( object ):
    """
    Provides a 'sleep' method that sleeps for a number of seconds *unless*
    the notify method is called (from a different thread).
    """
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
