"""
Universe configuration builder.
"""

import sys, os
import logging, logging.config
from optparse import OptionParser
import ConfigParser
from galaxy.util import string_as_bool

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
        # Database related configuration
        self.database = resolve_path( kwargs.get( "database_file", "database/universe.d" ), self.root )
        self.database_connection =  kwargs.get( "database_connection", False )
        self.database_engine_options = get_database_engine_options( kwargs )                        
        self.database_create_tables = string_as_bool( kwargs.get( "database_create_tables", "True" ) )
        # Where dataset files are stored
        self.file_path = resolve_path( kwargs.get( "file_path", "database/files" ), self.root )
        self.new_file_path = resolve_path( kwargs.get( "new_file_path", "database/tmp" ), self.root )
        # dataset Track files
        self.track_store_path = kwargs.get( "track_store_path", "${extra_files_path}/tracks")
        self.tool_path = resolve_path( kwargs.get( "tool_path", "tools" ), self.root )
        self.tool_data_path = resolve_path( kwargs.get( "tool_data_path", "tool-data" ), os.getcwd() )
        self.test_conf = resolve_path( kwargs.get( "test_conf", "" ), self.root )
        self.tool_config = resolve_path( kwargs.get( 'tool_config_file', 'tool_conf.xml' ), self.root )
        self.tool_secret = kwargs.get( "tool_secret", "" )
        self.id_secret = kwargs.get( "id_secret", "USING THE DEFAULT IS NOT SECURE!" )
        self.set_metadata_externally = string_as_bool( kwargs.get( "set_metadata_externally", "False" ) )
        self.use_remote_user = string_as_bool( kwargs.get( "use_remote_user", "False" ) )
        self.remote_user_maildomain = kwargs.get( "remote_user_maildomain", None )
        self.remote_user_logout_href = kwargs.get( "remote_user_logout_href", None )
        self.require_login = string_as_bool( kwargs.get( "require_login", "False" ) )
        self.allow_user_creation = string_as_bool( kwargs.get( "allow_user_creation", "True" ) )
        self.allow_user_deletion = string_as_bool( kwargs.get( "allow_user_deletion", "False" ) )
        self.new_user_dataset_access_role_default_private = string_as_bool( kwargs.get( "new_user_dataset_access_role_default_private", "False" ) )
        self.template_path = resolve_path( kwargs.get( "template_path", "templates" ), self.root )
        self.template_cache = resolve_path( kwargs.get( "template_cache_path", "database/compiled_templates" ), self.root )
        self.local_job_queue_workers = int( kwargs.get( "local_job_queue_workers", "5" ) )
        self.cluster_job_queue_workers = int( kwargs.get( "cluster_job_queue_workers", "3" ) )
        self.job_scheduler_policy = kwargs.get("job_scheduler_policy", "FIFO")
        self.job_queue_cleanup_interval = int( kwargs.get("job_queue_cleanup_interval", "5") )
        self.cluster_files_directory = os.path.abspath( kwargs.get( "cluster_files_directory", "database/pbs" ) )
        self.job_working_directory = resolve_path( kwargs.get( "job_working_directory", "database/job_working_directory" ), self.root )
        self.outputs_to_working_directory = string_as_bool( kwargs.get( 'outputs_to_working_directory', False ) )
        self.output_size_limit = int( kwargs.get( 'output_size_limit', 0 ) )
        self.job_walltime = kwargs.get( 'job_walltime', None )
        self.admin_users = kwargs.get( "admin_users", "" )
        self.sendmail_path = kwargs.get('sendmail_path',"/usr/sbin/sendmail")
        self.mailing_join_addr = kwargs.get('mailing_join_addr',"galaxy-user-join@bx.psu.edu")
        self.error_email_to = kwargs.get( 'error_email_to', None )
        self.smtp_server = kwargs.get( 'smtp_server', None )
        self.start_job_runners = kwargs.get( 'start_job_runners', None )
        self.default_cluster_job_runner = kwargs.get( 'default_cluster_job_runner', 'local:///' )
        self.pbs_application_server = kwargs.get('pbs_application_server', "" )
        self.pbs_dataset_server = kwargs.get('pbs_dataset_server', "" )
        self.pbs_dataset_path = kwargs.get('pbs_dataset_path', "" )
        self.pbs_stage_path = kwargs.get('pbs_stage_path', "" )
        self.use_heartbeat = string_as_bool( kwargs.get( 'use_heartbeat', 'False' ) )
        self.use_memdump = string_as_bool( kwargs.get( 'use_memdump', 'False' ) )
        self.log_memory_usage = string_as_bool( kwargs.get( 'log_memory_usage', 'False' ) )
        self.log_events = string_as_bool( kwargs.get( 'log_events', 'False' ) )
        self.ucsc_display_sites = kwargs.get( 'ucsc_display_sites', "main,test,archaea" ).lower().split(",")
        self.gbrowse_display_sites = kwargs.get( 'gbrowse_display_sites', "wormbase,flybase,elegans" ).lower().split(",")
        self.brand = kwargs.get( 'brand', None )
        self.wiki_url = kwargs.get( 'wiki_url', 'http://g2.trac.bx.psu.edu/' )
        self.bugs_email = kwargs.get( 'bugs_email', None )
        self.blog_url = kwargs.get( 'blog_url', None )
        self.screencasts_url = kwargs.get( 'screencasts_url', None )
        self.library_import_dir = kwargs.get( 'library_import_dir', None )
        if self.library_import_dir is not None and not os.path.exists( self.library_import_dir ):
            raise ConfigurationError( "library_import_dir specified in config (%s) does not exist" % self.library_import_dir )
        self.user_library_import_dir = kwargs.get( 'user_library_import_dir', None )
        if self.user_library_import_dir is not None and not os.path.exists( self.user_library_import_dir ):
            raise ConfigurationError( "user_library_import_dir specified in config (%s) does not exist" % self.user_library_import_dir )
        # Configuration options for taking advantage of nginx features
        self.nginx_x_accel_redirect_base = kwargs.get( 'nginx_x_accel_redirect_base', False )
        self.nginx_upload_location = kwargs.get( 'nginx_upload_store', False )
        if self.nginx_upload_location:
            self.nginx_upload_location = os.path.abspath( self.nginx_upload_location )
        # Parse global_conf and save the parser
        global_conf = kwargs.get( 'global_conf', None )
        global_conf_parser = ConfigParser.ConfigParser()
        self.global_conf_parser = global_conf_parser
        if global_conf and "__file__" in global_conf:
            global_conf_parser.read(global_conf['__file__'])
        #Store per-tool runner config
        try:
            self.tool_runners = global_conf_parser.items("galaxy:tool_runners")
        except ConfigParser.NoSectionError:
            self.tool_runners = []
        self.datatypes_config = kwargs.get( 'datatypes_config_file', 'datatypes_conf.xml' )
        # Cloud configuration options
        self.cloud_controller_instance = string_as_bool( kwargs.get( 'cloud_controller_instance', 'False' ) )
    def get( self, key, default ):
        return self.config_dict.get( key, default )
    def get_bool( self, key, default ):
        if key in self.config_dict:
            return string_as_bool( self.config_dict[key] )
        else:
            return default
    def check( self ):
        # Check that required directories exist
        for path in self.root, self.file_path, self.tool_path, self.tool_data_path, self.template_path, self.job_working_directory, self.cluster_files_directory:
            if not os.path.isdir( path ):
                raise ConfigurationError("Directory does not exist: %s" % path )
        # Check that required files exist
        for path in self.tool_config, self.datatypes_config:
            if not os.path.isfile(path):
                raise ConfigurationError("File not found: %s" % path )
                
    def is_admin_user( self,user ):
        """
        Determine if the provided user is listed in `admin_users`.
        
        NOTE: This is temporary, admin users will likely be specified in the
              database in the future.
        """
        admin_users = self.get( "admin_users", "" ).split( "," )
        return ( user is not None and user.email in admin_users )

def get_database_engine_options( kwargs ):
    """
    Allow options for the SQLAlchemy database engine to be passed by using
    the prefix "database_engine_option_".
    """
    conversions =  {
        'convert_unicode': string_as_bool,
        'pool_timeout': int,
        'echo': string_as_bool,
        'echo_pool': string_as_bool,
        'pool_recycle': int,
        'pool_size': int,
        'max_overflow': int,
        'pool_threadlocal': string_as_bool
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
