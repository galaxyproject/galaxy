"""
API operations allowing clients to determine Galaxy instance's capabilities
and configuration settings.
"""

from galaxy import web
from galaxy.web.base.controller import BaseAPIController

import logging
log = logging.getLogger( __name__ )

class ConfigurationController( BaseAPIController ):
    # config attributes viewable by non-admin users
    EXPOSED_USER_OPTIONS = [
        'enable_unique_workflow_defaults',
        'ftp_upload_site',
        'ftp_upload_dir',
        'wiki_url',
        'support_url',
        'logo_url',
        'terms_url',
        'allow_user_dataset_purge',
    ]
    # config attributes viewable by admin users
    EXPOSED_ADMIN_OPTIONS = [
        'library_import_dir',
        'user_library_import_dir',
        'allow_library_path_paste',
        'allow_user_creation',
        'allow_user_deletion',
    ]

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/configuration
        Return an object containing exposable configuration settings.

        Note: a more complete list is returned if the user is an admin.
        """
        try:
            config = trans.app.config
            options = self._get_options( config, self.EXPOSED_USER_OPTIONS )
            if trans.user_is_admin():
                options.update( self._get_options( config, self.EXPOSED_ADMIN_OPTIONS ) )
            return options

        except Exception, exception:
            log.error( 'could not get configuration: %s', str( exception ), exc_info=True )
            trans.response.status = 500
            return { 'error': str( exception ) }

    def _get_options( self, config, keys ):
        """
        Build and return a subset of the config dictionary restricted to the
        list `keys`.

        The attribute value will default to None if not available.
        """
        return dict( [ (key, getattr( config, key, None ) ) for key in keys ] )
