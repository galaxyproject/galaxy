"""
Manager and Serializer for Repositories.
"""

from galaxy import exceptions
from galaxy.util import pretty_print_time_interval
from galaxy.model import tool_shed_install
from galaxy.managers import base

import logging
log = logging.getLogger( __name__ )


class RepoManager( base.ModelManager ):
    model_class = tool_shed_install.ToolShedRepository

    def __init__( self, app, *args, **kwargs ):
        super( RepoManager, self ).__init__( app, *args, **kwargs )

    def list( self, trans, view='all' ):
        if not trans.user_is_admin():
            raise exceptions.ItemAccessibilityException( 'Only administrators can see repos.' )
        # TODO respect `view` that is requested
        repos = trans.sa_session.query( self.model_class ).all()
        return repos


class RepositorySerializer( base.ModelSerializer ):
    model_manager_class = RepoManager

    def __init__( self, app ):
        """
        Convert a Repository and associated data to a dictionary representation.
        """
        super( RepositorySerializer, self ).__init__( app )
        self.user_manager = self.manager

        self.default_view = 'summary'
        self.add_view( 'summary', [
            'id',
            'name',
            'owner',
            'status',
            'create_time',
            'tool_shed',
            'tool_shed_status',

        ])
        self.add_view( 'detailed', [
            'uninstalled',
            'changeset_revision',
            'ctx_rev',
            'deleted',
            'error_message',
            'installed_changeset_revision',
            'update_time',
            'includes_datatypes',
            'dist_to_shed',
        ], include_keys_from='summary' )

    def add_serializers( self ):
        super( RepositorySerializer, self ).add_serializers()

        self.serializers.update({
            'id': self.serialize_id,
            'create_time': self.serialize_interval,
            'update_time': self.serialize_date,
        })

    def serialize_interval( self, item, key, **context ):
        date = getattr( item, key )
        return { 'interval': pretty_print_time_interval( date, precise=True ), 'date': self.serialize_date( item, key ) }
