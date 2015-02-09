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

    def get_config_dict( self, trans, return_admin=False, view=None, keys=None, default_view='all' ):
        """
        Return a dictionary with (a subset of) current Galaxy settings.

        If `return_admin` also include a subset of more sensitive keys.
        Pass in `view` (String) and comma seperated list of keys to control which
        configuration settings are returned.
        """
        serializer = self.config_serializer
        if return_admin:
            #TODO: this should probably just be under a different route: 'admin/configuration'
            serializer = self.admin_config_serializer

        serialized = serializer.serialize_to_view( trans, self.app.config,
                                                   view=view, keys=keys, default_view=default_view )
        return serialized


#TODO: for lack of a manager file for the config. May well be better in config.py? Circ imports?
class ConfigSerializer( base.ModelSerializer ):

    def __init__( self, app ):
        super( ConfigSerializer, self ).__init__( app )

        self.default_view = 'all'
        self.add_view( 'all', self.serializers.keys() )

    def default_serializer( self, trans, config, key ):
        return config.get( key, None )

    def add_serializers( self ):
        def _defaults_to( default ):
            return lambda t, i, k: i.get( k, default )

        self.serializers = {
            #TODO: this is available from user data, remove
            'is_admin_user'             : lambda *a: False,

            'brand'                     : _defaults_to( '' ),
            #TODO: this doesn't seem right
            'logo_url'                  : lambda t, i, k: self.url_for( i.get( k, '/' ) ),
            'terms_url'                 : _defaults_to( '' ),

            #TODO: don't hardcode here - hardcode defaults once in config.py
            'wiki_url'                  : _defaults_to( "http://galaxyproject.org/" ),
            'search_url'                : _defaults_to( "http://galaxyproject.org/search/usegalaxy/" ),
            'mailing_lists'             : _defaults_to( "http://wiki.galaxyproject.org/MailingLists" ),
            'screencasts_url'           : _defaults_to( "http://vimeo.com/galaxyproject" ),
            'citation_url'              : _defaults_to( "http://wiki.galaxyproject.org/CitingGalaxy" ),
            'support_url'               : _defaults_to( "http://wiki.galaxyproject.org/Support" ),
            'lims_doc_url'              : _defaults_to( "http://main.g2.bx.psu.edu/u/rkchak/p/sts" ),
            'biostar_url'               : _defaults_to( '' ),
            'biostar_url_redirect'      : lambda *a: self.url_for( controller='biostar', action='biostar_redirect',
                                                                   qualified=True ),

            'allow_user_creation'       : _defaults_to( False ),
            'use_remote_user'           : _defaults_to( None ),
            'remote_user_logout_href'   : _defaults_to( '' ),
            'enable_cloud_launch'       : _defaults_to( False ),
            'datatypes_disable_auto'    : _defaults_to( False ),
            'allow_user_dataset_purge'  : _defaults_to( False ),
            'enable_unique_workflow_defaults' : _defaults_to( False ),

            'nginx_upload_path'         : _defaults_to( self.url_for( controller='api', action='tools' ) ),
            'ftp_upload_dir'            : _defaults_to( None ),
            'ftp_upload_site'           : _defaults_to( None ),
        }


class AdminConfigSerializer( ConfigSerializer ):
    # config attributes viewable by admin users

    def add_serializers( self ):
        super( AdminConfigSerializer, self ).add_serializers()
        def _defaults_to( default ):
            return lambda t, i, k: i.get( k, default )

        self.serializers.update({
            #TODO: this is available from user data, remove
            'is_admin_user'             : lambda *a: True,

            'library_import_dir'        : _defaults_to( None ),
            'user_library_import_dir'   : _defaults_to( None ),
            'allow_library_path_paste'  : _defaults_to( False ),
            'allow_user_creation'       : _defaults_to( False ),
            'allow_user_deletion'       : _defaults_to( False ),
        })
