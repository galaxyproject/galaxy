"""
API operations allowing clients to determine Galaxy instance's capabilities
and configuration settings.
"""

from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController

from galaxy.managers import base

import logging
log = logging.getLogger( __name__ )


class ConfigurationController( BaseAPIController ):

    def __init__( self, app ):
        super( ConfigurationController, self ).__init__( app )
        self.config_serializer = ConfigSerializer( app )
        self.admin_config_serializer = AdminConfigSerializer( app )

    @expose_api_anonymous
    def index( self, trans, **kwd ):
        """
        GET /api/configuration
        Return an object containing exposable configuration settings.

        Note: a more complete list is returned if the user is an admin.
        """
        is_admin = self.user_manager.is_admin( trans, trans.user )
        serialization_params = self._parse_serialization_params( kwd, 'all' )
        return self.get_config_dict( trans, is_admin, **serialization_params )

    def get_config_dict( self, trans, return_admin=False, **kwargs ):
        serializer = self.config_serializer
        if return_admin:
            #TODO: this should probably just be under a different route: 'admin/configuration'
            serializer = self.admin_config_serializer

        if 'default_view' not in kwargs:
            kwargs[ 'default_view' ] = serializer.default_view
        serialized = serializer.serialize_to_view( trans, self.app.config, **kwargs )
        return serialized


class ConfigSerializer( base.ModelSerializer ):

    def __init__( self, app ):
        super( ConfigSerializer, self ).__init__( app )

        self.default_view = 'all'
        self.add_view( 'all', self.serializers.keys() )

    def default_serializer( self, trans, config, key ):
        return config.get( key, None )

    def _defaults_to( self, default ):
        return lambda t, i, k: i.get( k, default )

    def add_serializers( self ):
        self.serializers = {
            #TODO: this is available from user data, remove
            'is_admin_user'             : lambda *a: False,

            'brand'                     : lambda t, i, k: i.get( k, "" ),
            #TODO: this doesn't seem right
            'logo_url'                  : lambda t, i, k: self.url_for( i.get( k, '/') ),
            'terms_url'                 : lambda t, i, k: i.get( k, "" ),

            #TODO: don't hardcode here - hardcode defaults once in config.py
            'wiki_url'                  : self._defaults_to( "http://galaxyproject.org/" ),
            'search_url'                : self._defaults_to( "http://galaxyproject.org/search/usegalaxy/" ),
            'mailing_lists'             : self._defaults_to( "http://wiki.galaxyproject.org/MailingLists" ),
            'screencasts_url'           : self._defaults_to( "http://vimeo.com/galaxyproject" ),
            'citation_url'              : self._defaults_to( "http://wiki.galaxyproject.org/CitingGalaxy" ),
            'support_url'               : self._defaults_to( "http://wiki.galaxyproject.org/Support" ),
            'lims_doc_url'              : self._defaults_to( "http://main.g2.bx.psu.edu/u/rkchak/p/sts" ),
            'biostar_url'               : lambda t, i, k: i.biostar_url,
            'biostar_url_redirect'      : lambda *a: self.url_for( controller='biostar', action='biostar_redirect',
                                                                qualified=True ),

            'allow_user_creation'       : lambda t, i, k: i.allow_user_creation,
            'use_remote_user'           : lambda t, i, k: i.use_remote_user,
            'remote_user_logout_href'   : lambda t, i, k: i.remote_user_logout_href,
            'enable_cloud_launch'       : self._defaults_to( False ),
            'datatypes_disable_auto'    : self._defaults_to( False ),
            'allow_user_dataset_purge'  : self._defaults_to( False ),
            'enable_unique_workflow_defaults' : self._defaults_to( False ),

            'nginx_upload_path'         : self._defaults_to( self.url_for( controller='api', action='tools' ) ),
            'ftp_upload_dir'            : self._defaults_to( None ),
            'ftp_upload_site'           : self._defaults_to( None ),
        }


class AdminConfigSerializer( ConfigSerializer ):
    # config attributes viewable by admin users

    def add_serializers( self ):
        super( AdminConfigSerializer, self ).add_serializers()

        self.serializers.update({
            #TODO: this is available from user data, remove
            'is_admin_user'             : lambda *a: True,

            'library_import_dir'        : self._defaults_to( None ),
            'user_library_import_dir'   : self._defaults_to( None ),
            'allow_library_path_paste'  : self._defaults_to( None ),
            'allow_user_creation'       : self._defaults_to( False ),
            'allow_user_deletion'       : self._defaults_to( False ),
        })
