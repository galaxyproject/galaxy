import logging

from mercurial import hg
from mercurial import ui

log = logging.getLogger( __name__ )


class Metadata( object ):

    def __init__( self ):
        self.type = None

    def get_changesets_for_setting_metadata( self, app, repository ):
        repo = hg.repository( ui.ui(), repository.repo_path( app ) )
        return repo.changelog

    def is_valid_for_type( self, app, repository, revisions_to_check=None ):
        raise Exception( "Unimplemented Method" )


class TipOnly( Metadata ):

    def __init__( self ):
        self.type = None

    def get_changesets_for_setting_metadata( self, app, repository ):
        repo = hg.repository( ui.ui(), repository.repo_path( app ) )
        return [ repo.changelog.tip() ]
