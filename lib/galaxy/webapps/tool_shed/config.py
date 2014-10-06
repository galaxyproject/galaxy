"""
Universe configuration builder.
"""
import os
import sys
import logging
import logging.config
from optparse import OptionParser
import ConfigParser
from galaxy.util import string_as_bool, listify

log = logging.getLogger( __name__ )

def resolve_path( path, root ):
    """If 'path' is relative make absolute by prepending 'root'"""
    if not( os.path.isabs( path ) ):
        path = os.path.join( root, path )
    return path


class ConfigurationError( Exception ):
    pass


class Configuration( object ):

    def __init__( self, **kwargs ):
        self.config_dict = kwargs
        self.root = kwargs.get( 'root_dir', '.' )

        # Resolve paths of other config files
        self.__parse_config_file_options( kwargs )

        # Collect the umask and primary gid from the environment
        self.umask = os.umask( 077 ) # get the current umask
        os.umask( self.umask ) # can't get w/o set, so set it back
        self.gid = os.getgid() # if running under newgrp(1) we'll need to fix the group of data created on the cluster
        # Database related configuration
        self.database = resolve_path( kwargs.get( "database_file", "database/community.sqlite" ), self.root )
        self.database_connection = kwargs.get( "database_connection", False )
        self.database_engine_options = get_database_engine_options( kwargs )
        self.database_create_tables = string_as_bool( kwargs.get( "database_create_tables", "True" ) )
        # Where dataset files are stored
        self.file_path = resolve_path( kwargs.get( "file_path", "database/community_files" ), self.root )
        self.new_file_path = resolve_path( kwargs.get( "new_file_path", "database/tmp" ), self.root )
        self.cookie_path = kwargs.get( "cookie_path", "/" )
        self.enable_quotas = string_as_bool( kwargs.get( 'enable_quotas', False ) )
        self.test_conf = resolve_path( kwargs.get( "test_conf", "" ), self.root )
        self.id_secret = kwargs.get( "id_secret", "USING THE DEFAULT IS NOT SECURE!" )
        # Tool stuff
        self.tool_filters = listify( kwargs.get( "tool_filters", [] ) )
        self.tool_label_filters = listify( kwargs.get( "tool_label_filters", [] ) )
        self.tool_section_filters = listify( kwargs.get( "tool_section_filters", [] ) )
        self.tool_path = resolve_path( kwargs.get( "tool_path", "tools" ), self.root )
        self.tool_secret = kwargs.get( "tool_secret", "" )
        self.tool_data_path = resolve_path( kwargs.get( "tool_data_path", "shed-tool-data" ), os.getcwd() )
        self.integrated_tool_panel_config = resolve_path( kwargs.get( 'integrated_tool_panel_config', 'integrated_tool_panel.xml' ), self.root )
        self.builds_file_path = resolve_path( kwargs.get( "builds_file_path", os.path.join( self.tool_data_path, 'shared', 'ucsc', 'builds.txt') ), self.root )
        self.len_file_path = resolve_path( kwargs.get( "len_file_path", os.path.join( self.tool_data_path, 'shared','ucsc','chrom') ), self.root )
        self.ftp_upload_dir = kwargs.get( 'ftp_upload_dir', None )
        # Install and test framework for testing tools contained in repositories.
        self.num_tool_test_results_saved = kwargs.get( 'num_tool_test_results_saved', 5 )
        # Location for dependencies
        if 'tool_dependency_dir' in kwargs:
            self.tool_dependency_dir = resolve_path( kwargs.get( "tool_dependency_dir" ), self.root )
            self.use_tool_dependencies = True
        else:
            self.tool_dependency_dir = None
            self.use_tool_dependencies = False
        self.update_integrated_tool_panel = False
        # Galaxy flavor Docker Image
        self.enable_galaxy_flavor_docker_image = string_as_bool( kwargs.get( "enable_galaxy_flavor_docker_image", "False" ) )
        self.use_remote_user = string_as_bool( kwargs.get( "use_remote_user", "False" ) )
        self.user_activation_on = kwargs.get( 'user_activation_on', None )
        self.activation_grace_period = kwargs.get( 'activation_grace_period', None )
        self.inactivity_box_content = kwargs.get( 'inactivity_box_content', None )
        self.registration_warning_message = kwargs.get( 'registration_warning_message', None )
        self.terms_url = kwargs.get( 'terms_url', None )
        self.blacklist_location = kwargs.get( 'blacklist_file', None )
        self.blacklist_content = None
        self.remote_user_maildomain = kwargs.get( "remote_user_maildomain", None )
        self.remote_user_header = kwargs.get( "remote_user_header", 'HTTP_REMOTE_USER' )
        self.remote_user_logout_href = kwargs.get( "remote_user_logout_href", None )
        self.require_login = string_as_bool( kwargs.get( "require_login", "False" ) )
        self.allow_user_creation = string_as_bool( kwargs.get( "allow_user_creation", "True" ) )
        self.allow_user_deletion = string_as_bool( kwargs.get( "allow_user_deletion", "False" ) )
        self.enable_openid = string_as_bool( kwargs.get( 'enable_openid', False ) )
        self.template_path = resolve_path( kwargs.get( "template_path", "templates" ), self.root )
        self.template_cache = resolve_path( kwargs.get( "template_cache_path", "database/compiled_templates/community" ), self.root )
        self.admin_users = kwargs.get( "admin_users", "" )
        self.admin_users_list = [u.strip() for u in self.admin_users.split(',') if u]
        self.sendmail_path = kwargs.get('sendmail_path',"/usr/sbin/sendmail")
        self.mailing_join_addr = kwargs.get('mailing_join_addr',"galaxy-announce-join@bx.psu.edu")
        self.error_email_to = kwargs.get( 'error_email_to', None )
        self.smtp_server = kwargs.get( 'smtp_server', None )
        self.smtp_username = kwargs.get( 'smtp_username', None )
        self.smtp_password = kwargs.get( 'smtp_password', None )
        self.start_job_runners = kwargs.get( 'start_job_runners', None )
        self.email_from = kwargs.get( 'email_from', None )
        self.nginx_upload_path = kwargs.get( 'nginx_upload_path', False )
        self.log_actions = string_as_bool( kwargs.get( 'log_actions', 'False' ) )
        self.brand = kwargs.get( 'brand', None )
        # Configuration for the message box directly below the masthead.
        self.message_box_visible = kwargs.get( 'message_box_visible', False )
        self.message_box_content = kwargs.get( 'message_box_content', None )
        self.message_box_class = kwargs.get( 'message_box_class', 'info' )
        self.support_url = kwargs.get( 'support_url', 'https://wiki.galaxyproject.org/Support' )
        self.wiki_url = kwargs.get( 'wiki_url', 'https://wiki.galaxyproject.org/' )
        self.blog_url = kwargs.get( 'blog_url', None )
        self.biostar_url = kwargs.get( 'biostar_url', None )
        self.screencasts_url = kwargs.get( 'screencasts_url', None )
        self.log_events = False
        self.cloud_controller_instance = False
        self.server_name = ''
        self.job_manager = ''
        self.default_job_handlers = []
        self.default_cluster_job_runner = 'local:///'
        self.job_handlers = []
        self.tool_handlers = []
        self.tool_runners = []
        # Error logging with sentry
        self.sentry_dsn = kwargs.get( 'sentry_dsn', None )
        # Where the tool shed hgweb.config file is stored - the default is the Galaxy installation directory.
        self.hgweb_config_dir = resolve_path( kwargs.get( 'hgweb_config_dir', '' ), self.root )
        # Proxy features
        self.apache_xsendfile = kwargs.get( 'apache_xsendfile', False )
        self.nginx_x_accel_redirect_base = kwargs.get( 'nginx_x_accel_redirect_base', False )
        self.drmaa_external_runjob_script = kwargs.get('drmaa_external_runjob_script', None )
        # Parse global_conf and save the parser
        global_conf = kwargs.get( 'global_conf', None )
        global_conf_parser = ConfigParser.ConfigParser()
        self.global_conf_parser = global_conf_parser
        if global_conf and "__file__" in global_conf:
            global_conf_parser.read(global_conf['__file__'])
        self.running_functional_tests = string_as_bool( kwargs.get( 'running_functional_tests', False ) )
        self.citation_cache_type = kwargs.get( "citation_cache_type", "file" )
        self.citation_cache_data_dir = resolve_path( kwargs.get( "citation_cache_data_dir", "database/tool_shed_citations/data" ), self.root )
        self.citation_cache_lock_dir = resolve_path( kwargs.get( "citation_cache_lock_dir", "database/tool_shed_citations/locks" ), self.root )

    def __parse_config_file_options( self, kwargs ):
        defaults = dict(
            datatypes_config_file = [ 'config/datatypes_conf.xml', 'datatypes_conf.xml', 'config/datatypes_conf.xml.sample' ],
            shed_tool_data_table_config = [ 'shed_tool_data_table_conf.xml', 'config/shed_tool_data_table_conf.xml' ],
        )

        listify_defaults = dict(
            tool_data_table_config_path = [ 'config/tool_data_table_conf.xml', 'tool_data_table_conf.xml', 'config/tool_data_table_conf.xml.sample' ],
        )

        for var, defaults in defaults.items():
            if kwargs.get( var, None ) is not None:
                path = kwargs.get( var )
            else:
                for default in defaults:
                    if os.path.exists( resolve_path( default, self.root ) ):
                        path = default
                        break
                else:
                    path = defaults[-1]
            setattr( self, var, resolve_path( path, self.root ) )

        for var, defaults in listify_defaults.items():
            paths = []
            if kwargs.get( var, None ) is not None:
                paths = listify( kwargs.get( var ) )
            else:
                for default in defaults:
                    for path in listify( default ):
                        if not os.path.exists( resolve_path( path, self.root ) ):
                            break
                    else:
                        paths = listify( default )
                        break
                else:
                    paths = listify( defaults[-1] )
            setattr( self, var, [ resolve_path( x, self.root ) for x in paths ] )

        # Backwards compatibility for names used in too many places to fix
        self.datatypes_config = self.datatypes_config_file

    def get( self, key, default ):
        return self.config_dict.get( key, default )

    def get_bool( self, key, default ):
        if key in self.config_dict:
            return string_as_bool( self.config_dict[key] )
        else:
            return default

    def check( self ):
        # Check that required directories exist.
        paths_to_check = [ self.root, self.file_path, self.hgweb_config_dir, self.tool_data_path, self.template_path ]
        for path in paths_to_check:
            if path not in [ None, False ] and not os.path.isdir( path ):
                try:
                    os.makedirs( path )
                except Exception, e:
                    raise ConfigurationError( "Unable to create missing directory: %s\n%s" % ( path, e ) )
        # Create the directories that it makes sense to create.
        for path in self.file_path, \
                    self.template_cache, \
                    os.path.join( self.tool_data_path, 'shared', 'jars' ):
            if path not in [ None, False ] and not os.path.isdir( path ):
                try:
                    os.makedirs( path )
                except Exception, e:
                    raise ConfigurationError( "Unable to create missing directory: %s\n%s" % ( path, e ) )
        # Check that required files exist.
        if not os.path.isfile( self.datatypes_config ):
            raise ConfigurationError( "File not found: %s" % self.datatypes_config )

    def is_admin_user( self, user ):
        """
        Determine if the provided user is listed in `admin_users`.
        """
        admin_users = self.get( "admin_users", "" ).split( "," )
        return user is not None and user.email in admin_users

def get_database_engine_options( kwargs ):
    """
    Allow options for the SQLAlchemy database engine to be passed by using
    the prefix "database_engine_option".
    """
    conversions =  {
        'convert_unicode': string_as_bool,
        'pool_timeout': int,
        'echo': string_as_bool,
        'echo_pool': string_as_bool,
        'pool_recycle': int,
        'pool_size': int,
        'max_overflow': int,
        'pool_threadlocal': string_as_bool,
        'server_side_cursors': string_as_bool
    }
    prefix = "database_engine_option_"
    prefix_len = len( prefix )
    rval = {}
    for key, value in kwargs.iteritems():
        if key.startswith( prefix ):
            key = key[prefix_len:]
            if key in conversions:
                value = conversions[key](value)
            rval[ key  ] = value
    return rval

def configure_logging( config ):
    """
    Allow some basic logging configuration to be read from the cherrpy
    config.
    """
    # PasteScript will have already configured the logger if the appropriate
    # sections were found in the config file, so we do nothing if the
    # config has a loggers section, otherwise we do some simple setup
    # using the 'log_*' values from the config.
    if config.global_conf_parser.has_section( "loggers" ):
        return
    format = config.get( "log_format", "%(name)s %(levelname)s %(asctime)s %(message)s" )
    level = logging._levelNames[ config.get( "log_level", "DEBUG" ) ]
    destination = config.get( "log_destination", "stdout" )
    log.info( "Logging at '%s' level to '%s'" % ( level, destination ) )
    # Get root logger
    root = logging.getLogger()
    # Set level
    root.setLevel( level )
    # Turn down paste httpserver logging
    if level <= logging.DEBUG:
        logging.getLogger( "paste.httpserver.ThreadPool" ).setLevel( logging.WARN )
    # Remove old handlers
    for h in root.handlers[:]:
        root.removeHandler(h)
    # Create handler
    if destination == "stdout":
        handler = logging.StreamHandler( sys.stdout )
    else:
        handler = logging.FileHandler( destination )
    # Create formatter
    formatter = logging.Formatter( format )
    # Hook everything up
    handler.setFormatter( formatter )
    root.addHandler( handler )
