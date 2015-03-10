"""
Serializers for Galaxy config file data: ConfigSerializer for all users
and a more expanded set of data for admin in AdminConfigSerializer.

Used by both the API and bootstrapped data.
"""
#TODO: this is a bit of an odd duck. It uses the serializer structure from managers
#   but doesn't have a model like them. It might be better in config.py or a
#   totally new area, but I'm leaving it in managers for now for class consistency.

from galaxy.managers import base

import logging
log = logging.getLogger( __name__ )


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
            'logo_url'                  : lambda t, i, k: web.url_for( i.get( k, '/') ),
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
            'biostar_url_redirect'      : lambda *a: web.url_for( controller='biostar', action='biostar_redirect',
                                                                qualified=True ),

            'allow_user_creation'       : lambda t, i, k: i.allow_user_creation,
            'use_remote_user'           : lambda t, i, k: i.use_remote_user,
            'remote_user_logout_href'   : lambda t, i, k: i.remote_user_logout_href,
            'enable_cloud_launch'       : self._defaults_to( False ),
            'datatypes_disable_auto'    : self._defaults_to( False ),
            'allow_user_dataset_purge'  : self._defaults_to( False ),
            'enable_unique_workflow_defaults' : self._defaults_to( False ),

            'nginx_upload_path'         : self._defaults_to( web.url_for( controller='api', action='tools' ) ),
            'ftp_upload_dir'            : self._defaults_to( None ),
            'ftp_upload_site'           : self._defaults_to( None ),
        }


class AdminConfigSerializer( ConfigSerializer ):
    """Config attributes viewable by admin users"""

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
