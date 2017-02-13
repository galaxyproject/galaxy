import logging

import tool_shed.repository_types.util as rt_util
from tool_shed.repository_types.metadata import Metadata

log = logging.getLogger( __name__ )


class Unrestricted( Metadata ):

    def __init__( self ):
        self.type = rt_util.UNRESTRICTED
        self.label = 'Unrestricted'

    def is_valid_for_type( self, app, repository, revisions_to_check=None ):
        """A repository's type can only be changed to the unrestricted type if it is new or has never been installed."""
        if repository.is_new( app ):
            return True
        if repository.times_downloaded == 0:
            return True
        return False
