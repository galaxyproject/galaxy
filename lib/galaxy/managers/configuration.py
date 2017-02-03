"""
Serializers for Galaxy config file data: ConfigSerializer for all users
and a more expanded set of data for admin in AdminConfigSerializer.

Used by both the API and bootstrapped data.
"""
# TODO: this is a bit of an odd duck. It uses the serializer structure from managers
#   but doesn't have a model like them. It might be better in config.py or a
#   totally new area, but I'm leaving it in managers for now for class consistency.

from galaxy.web.framework.base import server_starttime
from galaxy.managers import base

import logging
log = logging.getLogger( __name__ )


class ConfigSerializer( base.ModelSerializer ):
    """Configuration (galaxy.ini) settings viewable by all users"""

    def __init__( self, app ):
        super( ConfigSerializer, self ).__init__( app )

        self.default_view = 'all'
        self.add_view( 'all', self.serializers.keys() )

    def default_serializer( self, config, key ):
        return getattr( config, key, None )

    def add_serializers( self ):
        def _defaults_to( default ):
            return lambda i, k, **c: getattr( i, k, default )

        self.serializers = {
            # TODO: this is available from user data, remove
            'is_admin_user'                     : lambda *a, **c: False,

            'brand'                             : _defaults_to( '' ),
            # TODO: this doesn't seem right
            'logo_url'                          : lambda i, k, **c: self.url_for( i.get( k, '/' ) ),
            'logo_src'                          : lambda i, k, **c: self.url_for( '/static/images/galaxyIcon_noText.png' ),
            'terms_url'                         : _defaults_to( '' ),

            # TODO: don't hardcode here - hardcode defaults once in config.py
            'wiki_url'                          : _defaults_to( "http://galaxyproject.org/" ),
            'search_url'                        : _defaults_to( "http://galaxyproject.org/search/usegalaxy/" ),
            'mailing_lists'                     : _defaults_to( "https://wiki.galaxyproject.org/MailingLists" ),
            'screencasts_url'                   : _defaults_to( "https://vimeo.com/galaxyproject" ),
            'citation_url'                      : _defaults_to( "https://wiki.galaxyproject.org/CitingGalaxy" ),
            'support_url'                       : _defaults_to( "https://wiki.galaxyproject.org/Support" ),
            'lims_doc_url'                      : _defaults_to( "https://usegalaxy.org/u/rkchak/p/sts" ),
            'biostar_url'                       : _defaults_to( '' ),
            'biostar_url_redirect'              : lambda *a, **c: self.url_for( controller='biostar', action='biostar_redirect', qualified=True ),

            'enable_communication_server'       : _defaults_to( False ),
            'communication_server_port'         : _defaults_to( None ),
            'communication_server_host'         : _defaults_to( None ),
            'persistent_communication_rooms'    : _defaults_to( None ),
            'allow_user_creation'               : _defaults_to( False ),
            'use_remote_user'                   : _defaults_to( None ),
            'enable_openid'                     : _defaults_to( False ),
            'enable_quotas'                     : _defaults_to( False ),
            'remote_user_logout_href'           : _defaults_to( '' ),
            'datatypes_disable_auto'            : _defaults_to( False ),
            'allow_user_dataset_purge'          : _defaults_to( False ),
            'ga_code'                           : _defaults_to( None ),
            'enable_unique_workflow_defaults'   : _defaults_to( False ),
            'has_user_tool_filters'             : _defaults_to( False ),

            # TODO: is there no 'correct' way to get an api url? controller='api', action='tools' is a hack
            # at any rate: the following works with path_prefix but is still brittle
            # TODO: change this to (more generic) upload_path and incorporate config.nginx_upload_path into building it
            'nginx_upload_path'                 : lambda i, k, **c: getattr( i, k, False ) or self.url_for( '/api/tools' ),
            'ftp_upload_dir'                    : _defaults_to( None ),
            'ftp_upload_site'                   : _defaults_to( None ),
            'version_major'                     : _defaults_to( None ),
            'require_login'                     : _defaults_to( None ),
            'inactivity_box_content'            : _defaults_to( None ),
            'message_box_content'               : _defaults_to( None ),
            'message_box_visible'               : _defaults_to( False ),
            'message_box_class'                 : _defaults_to( 'info' ),
            'server_startttime'                 : lambda i, k, **c: server_starttime,
        }


class AdminConfigSerializer( ConfigSerializer ):
    """Configuration attributes viewable only by admin users"""

    def add_serializers( self ):
        super( AdminConfigSerializer, self ).add_serializers()

        def _defaults_to( default ):
            return lambda i, k, **c: getattr( i, k, default )

        self.serializers.update({
            # TODO: this is available from user serialization: remove
            'is_admin_user'                     : lambda *a: True,

            'library_import_dir'                : _defaults_to( None ),
            'user_library_import_dir'           : _defaults_to( None ),
            'allow_library_path_paste'          : _defaults_to( False ),
            'allow_user_deletion'               : _defaults_to( False ),
        })
