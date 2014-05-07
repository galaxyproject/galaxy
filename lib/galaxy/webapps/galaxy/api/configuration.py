"""
API operations allowing clients to determine Galaxy instance's capabilities
and configuration settings.
"""

from galaxy.web import _future_expose_api as expose_api
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
        'use_remote_user'
    ]
    # config attributes viewable by admin users
    EXPOSED_ADMIN_OPTIONS = [
        'library_import_dir',
        'user_library_import_dir',
        'allow_library_path_paste',
        'allow_user_creation',
        'allow_user_deletion',
    ]

    @expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/configuration
        Return an object containing exposable configuration settings.

        Note: a more complete list is returned if the user is an admin.
        """
        return self.get_config_dict( trans.app.config, is_admin=trans.user_is_admin() )

    def get_config_dict( self, config, is_admin=False ):
        options = self.EXPOSED_USER_OPTIONS
        if is_admin:
            options.extend( self.EXPOSED_ADMIN_OPTIONS )
        config_dict = dict( [ ( key, getattr( config, key, None ) ) for key in options ] )
        return config_dict
