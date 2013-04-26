"""
API operations allowing clients to determine Galaxy instance's capabilities.
"""

from galaxy import web
from galaxy.web.base.controller import BaseAPIController

import logging
log = logging.getLogger( __name__ )

class ConfigurationController( BaseAPIController ):
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
        """
        config = trans.app.config
        options = self._get_options( config, self.EXPOSED_USER_OPTIONS )
        if trans.user_is_admin():
            options.update( self._get_options( config, self.EXPOSED_ADMIN_OPTIONS ) )
        return options

    def _get_options( self, config, keys ):
        return dict( [ (key, getattr( config, key, None ) ) for key in keys ] )
