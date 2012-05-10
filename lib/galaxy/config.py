"""
Universe configuration builder.
"""

import sys, os, tempfile
import logging, logging.config
import ConfigParser
from galaxy.util import string_as_bool, listify, parse_xml

from galaxy import eggs
import pkg_resources

log = logging.getLogger( __name__ )

def resolve_path( path, root ):
    """If 'path' is relative make absolute by prepending 'root'"""
    if not( os.path.isabs( path ) ):
        path = os.path.join( root, path )
    return path

class ConfigurationError( Exception ):
    pass

class Configuration( object ):
    deprecated_options = ( 'database_file', )
    def __init__( self, **kwargs ):
        self.config_dict = kwargs
        self.root = kwargs.get( 'root_dir', '.' )
        # Collect the umask and primary gid from the environment
        self.umask = os.umask( 077 ) # get the current umask
        os.umask( self.umask ) # can't get w/o set, so set it back
        self.gid = os.getgid() # if running under newgrp(1) we'll need to fix the group of data created on the cluster
        # Database related configuration
        self.database = resolve_path( kwargs.get( "database_file", "database/universe.sqlite" ), self.root )
        self.database_connection =  kwargs.get( "database_connection", False )
        self.database_engine_options = get_database_engine_options( kwargs )
        self.database_create_tables = string_as_bool( kwargs.get( "database_create_tables", "True" ) )
        self.database_query_profiling_proxy = string_as_bool( kwargs.get( "database_query_profiling_proxy", "False" ) )
        # Where dataset files are stored
        self.file_path = resolve_path( kwargs.get( "file_path", "database/files" ), self.root )
        self.new_file_path = resolve_path( kwargs.get( "new_file_path", "database/tmp" ), self.root )
        tempfile.tempdir = self.new_file_path
        self.openid_consumer_cache_path = resolve_path( kwargs.get( "openid_consumer_cache_path", "database/openid_consumer_cache" ), self.root )
        self.cookie_path = kwargs.get( "cookie_path", "/" )
        self.genome_data_path = kwargs.get( "genome_data_path", "tool-data/genome" )
        # Galaxy OpenID settings
        self.enable_openid = string_as_bool( kwargs.get( 'enable_openid', False ) )
        self.openid_config = kwargs.get( 'openid_config_file', 'openid_conf.xml' )
        self.enable_quotas = string_as_bool( kwargs.get( 'enable_quotas', False ) )
        self.tool_sheds_config = kwargs.get( 'tool_sheds_config_file', 'tool_sheds_conf.xml' )
        self.enable_unique_workflow_defaults = string_as_bool( kwargs.get( 'enable_unique_workflow_defaults', False ) )
        self.tool_path = resolve_path( kwargs.get( "tool_path", "tools" ), self.root )
        self.tool_data_path = resolve_path( kwargs.get( "tool_data_path", "tool-data" ), os.getcwd() )
        self.len_file_path = kwargs.get( "len_file_path", resolve_path(os.path.join(self.tool_data_path, 'shared','ucsc','chrom'), self.root) )
        self.test_conf = resolve_path( kwargs.get( "test_conf", "" ), self.root )
        # The value of migrated_tools_config is the file reserved for containing only those tools that have been eliminated from the distribution
        # and moved to the tool shed.
        self.migrated_tools_config = resolve_path( "migrated_tools_conf.xml", self.root )
        if 'tool_config_file' in kwargs:
            tcf = kwargs[ 'tool_config_file' ]
        elif 'tool_config_files' in kwargs:
            tcf = kwargs[ 'tool_config_files' ]
        else:
            tcf = 'tool_conf.xml'
        self.tool_configs = [ resolve_path( p, self.root ) for p in listify( tcf ) ]
        self.tool_data_table_config_path = resolve_path( kwargs.get( 'tool_data_table_config_path', 'tool_data_table_conf.xml' ), self.root )
        self.enable_tool_shed_check = string_as_bool( kwargs.get( 'enable_tool_shed_check', False ) )
        try:
            self.hours_between_check = int( kwargs.get( 'hours_between_check', 12 ) )
            if self.hours_between_check < 1 or self.hours_between_check > 24:
                self.hours_between_check = 12
        except:
            self.hours_between_check = 12
        self.update_integrated_tool_panel = kwargs.get( "update_integrated_tool_panel", True )
        self.tool_secret = kwargs.get( "tool_secret", "" )
        self.id_secret = kwargs.get( "id_secret", "USING THE DEFAULT IS NOT SECURE!" )
        self.set_metadata_externally = string_as_bool( kwargs.get( "set_metadata_externally", "False" ) )
        self.retry_metadata_internally = string_as_bool( kwargs.get( "retry_metadata_internally", "True" ) )
        self.use_remote_user = string_as_bool( kwargs.get( "use_remote_user", "False" ) )
        self.remote_user_maildomain = kwargs.get( "remote_user_maildomain", None )
        self.remote_user_logout_href = kwargs.get( "remote_user_logout_href", None )
        self.require_login = string_as_bool( kwargs.get( "require_login", "False" ) )
        self.allow_user_creation = string_as_bool( kwargs.get( "allow_user_creation", "True" ) )
        self.allow_user_deletion = string_as_bool( kwargs.get( "allow_user_deletion", "False" ) )
        self.allow_user_dataset_purge = string_as_bool( kwargs.get( "allow_user_dataset_purge", "False" ) )
        self.allow_user_impersonation = string_as_bool( kwargs.get( "allow_user_impersonation", "False" ) )
        self.new_user_dataset_access_role_default_private = string_as_bool( kwargs.get( "new_user_dataset_access_role_default_private", "False" ) )
        self.collect_outputs_from = [ x.strip() for x in kwargs.get( 'collect_outputs_from', 'new_file_path,job_working_directory' ).lower().split(',') ]
        self.template_path = resolve_path( kwargs.get( "template_path", "templates" ), self.root )
        self.template_cache = resolve_path( kwargs.get( "template_cache_path", "database/compiled_templates" ), self.root )
        self.local_job_queue_workers = int( kwargs.get( "local_job_queue_workers", "5" ) )
        self.cluster_job_queue_workers = int( kwargs.get( "cluster_job_queue_workers", "3" ) )
        self.job_queue_cleanup_interval = int( kwargs.get("job_queue_cleanup_interval", "5") )
        self.cluster_files_directory = os.path.abspath( kwargs.get( "cluster_files_directory", "database/pbs" ) )
        self.job_working_directory = resolve_path( kwargs.get( "job_working_directory", "database/job_working_directory" ), self.root )
        self.cleanup_job = kwargs.get( "cleanup_job", "always" )
        self.outputs_to_working_directory = string_as_bool( kwargs.get( 'outputs_to_working_directory', False ) )
        self.output_size_limit = int( kwargs.get( 'output_size_limit', 0 ) )
        self.retry_job_output_collection = int( kwargs.get( 'retry_job_output_collection', 0 ) )
        self.job_walltime = kwargs.get( 'job_walltime', None )
        self.admin_users = kwargs.get( "admin_users", "" )
        self.mailing_join_addr = kwargs.get('mailing_join_addr',"galaxy-announce-join@bx.psu.edu")
        self.error_email_to = kwargs.get( 'error_email_to', None )
        self.smtp_server = kwargs.get( 'smtp_server', None )
        self.smtp_username = kwargs.get( 'smtp_username', None )
        self.smtp_password = kwargs.get( 'smtp_password', None )
        self.start_job_runners = kwargs.get( 'start_job_runners', None )
        self.expose_dataset_path = string_as_bool( kwargs.get( 'expose_dataset_path', 'False' ) )
        # External Service types used in sample tracking
        self.external_service_type_config_file = resolve_path( kwargs.get( 'external_service_type_config_file', 'external_service_types_conf.xml' ), self.root )
        self.external_service_type_path = resolve_path( kwargs.get( 'external_service_type_path', 'external_service_types' ), self.root )
        # Tasked job runner.
        self.use_tasked_jobs = string_as_bool( kwargs.get( 'use_tasked_jobs', False ) )
        self.local_task_queue_workers = int(kwargs.get("local_task_queue_workers", 2))
        # The transfer manager and deferred job queue
        self.enable_beta_job_managers = string_as_bool( kwargs.get( 'enable_beta_job_managers', 'False' ) )
        # Per-user Job concurrency limitations
        self.user_job_limit = int( kwargs.get( 'user_job_limit', 0 ) )
        self.default_cluster_job_runner = kwargs.get( 'default_cluster_job_runner', 'local:///' )
        self.pbs_application_server = kwargs.get('pbs_application_server', "" )
        self.pbs_dataset_server = kwargs.get('pbs_dataset_server', "" )
        self.pbs_dataset_path = kwargs.get('pbs_dataset_path', "" )
        self.pbs_stage_path = kwargs.get('pbs_stage_path', "" )
        self.drmaa_external_runjob_script = kwargs.get('drmaa_external_runjob_script', None )
        self.drmaa_external_killjob_script = kwargs.get('drmaa_external_killjob_script', None)
        self.external_chown_script = kwargs.get('external_chown_script', None)
        self.environment_setup_file = kwargs.get( 'environment_setup_file', None )
        self.use_heartbeat = string_as_bool( kwargs.get( 'use_heartbeat', 'False' ) )
        self.use_memdump = string_as_bool( kwargs.get( 'use_memdump', 'False' ) )
        self.log_actions = string_as_bool( kwargs.get( 'log_actions', 'False' ) )
        self.log_events = string_as_bool( kwargs.get( 'log_events', 'False' ) )
        self.sanitize_all_html = string_as_bool( kwargs.get( 'sanitize_all_html', True ) )
        self.ucsc_display_sites = kwargs.get( 'ucsc_display_sites', "main,test,archaea,ucla" ).lower().split(",")
        self.gbrowse_display_sites = kwargs.get( 'gbrowse_display_sites', "wormbase,tair,modencode_worm,modencode_fly,sgd_yeast" ).lower().split(",")
        self.genetrack_display_sites = kwargs.get( 'genetrack_display_sites', "main,test" ).lower().split(",")
        self.brand = kwargs.get( 'brand', None )
        self.support_url = kwargs.get( 'support_url', 'http://wiki.g2.bx.psu.edu/Support' )
        self.wiki_url = kwargs.get( 'wiki_url', 'http://g2.trac.bx.psu.edu/' )
        self.blog_url = kwargs.get( 'blog_url', None )
        self.screencasts_url = kwargs.get( 'screencasts_url', None )
        self.library_import_dir = kwargs.get( 'library_import_dir', None )
        self.user_library_import_dir = kwargs.get( 'user_library_import_dir', None )
        # Searching data libraries
        self.enable_lucene_library_search = string_as_bool( kwargs.get( 'enable_lucene_library_search', False ) )
        self.enable_whoosh_library_search = string_as_bool( kwargs.get( 'enable_whoosh_library_search', False ) )
        self.whoosh_index_dir = resolve_path( kwargs.get( "whoosh_index_dir", "database/whoosh_indexes" ), self.root )
        self.ftp_upload_dir = kwargs.get( 'ftp_upload_dir', None )
        self.ftp_upload_site = kwargs.get( 'ftp_upload_site', None )
        self.allow_library_path_paste = kwargs.get( 'allow_library_path_paste', False )
        self.disable_library_comptypes = kwargs.get( 'disable_library_comptypes', '' ).lower().split( ',' )
        # Location for tool dependencies.
        if 'tool_dependency_dir' in kwargs:
            self.tool_dependency_dir = resolve_path( kwargs.get( "tool_dependency_dir" ), self.root )
            # Setting the following flag to true will ultimately cause tool dependencies
            # to be located in the shell environment and used by the job that is executing
            # the tool.
            self.use_tool_dependencies = True
        else:
            self.tool_dependency_dir = None
            self.use_tool_dependencies = False
        # Configuration options for taking advantage of nginx features
        self.upstream_gzip = string_as_bool( kwargs.get( 'upstream_gzip', False ) )
        self.apache_xsendfile = string_as_bool( kwargs.get( 'apache_xsendfile', False ) )
        self.nginx_x_accel_redirect_base = kwargs.get( 'nginx_x_accel_redirect_base', False )
        self.nginx_x_archive_files_base = kwargs.get( 'nginx_x_archive_files_base', False )
        self.nginx_upload_store = kwargs.get( 'nginx_upload_store', False )
        self.nginx_upload_path = kwargs.get( 'nginx_upload_path', False )
        if self.nginx_upload_store:
            self.nginx_upload_store = os.path.abspath( self.nginx_upload_store )
        self.object_store = kwargs.get( 'object_store', 'disk' )
        self.aws_access_key = kwargs.get( 'aws_access_key', None )
        self.aws_secret_key = kwargs.get( 'aws_secret_key', None )
        self.s3_bucket = kwargs.get( 's3_bucket', None)
        self.use_reduced_redundancy = kwargs.get( 'use_reduced_redundancy', False )
        self.object_store_cache_size = float(kwargs.get( 'object_store_cache_size', -1 ))
        self.distributed_object_store_config_file = kwargs.get( 'distributed_object_store_config_file', None )
        # Parse global_conf and save the parser
        global_conf = kwargs.get( 'global_conf', None )
        global_conf_parser = ConfigParser.ConfigParser()
        self.config_file = None
        self.global_conf_parser = global_conf_parser
        if global_conf and "__file__" in global_conf:
            self.config_file = global_conf['__file__']
            global_conf_parser.read(global_conf['__file__'])
        # Heartbeat log file name override
        if global_conf is not None:
            self.heartbeat_log = global_conf.get( 'heartbeat_log', 'heartbeat.log' )
        # Determine which 'server:' this is
        self.server_name = 'main'
        for arg in sys.argv:
            # Crummy, but PasteScript does not give you a way to determine this
            if arg.lower().startswith('--server-name='):
                self.server_name = arg.split('=', 1)[-1]
        # Store advanced job management config
        self.job_manager = kwargs.get('job_manager', self.server_name).strip()
        self.job_handlers = [ x.strip() for x in kwargs.get('job_handlers', self.server_name).split(',') ]
        self.default_job_handlers = [ x.strip() for x in kwargs.get('default_job_handlers', ','.join( self.job_handlers ) ).split(',') ]
        # Use database for IPC unless this is a standalone server (or multiple servers doing self dispatching in memory)
        self.track_jobs_in_database = True
        if ( len( self.job_handlers ) == 1 ) and ( self.job_handlers[0] == self.server_name ) and ( self.job_manager == self.server_name ):
            self.track_jobs_in_database = False
        # Store per-tool runner configs
        self.tool_handlers = self.__read_tool_job_config( global_conf_parser, 'galaxy:tool_handlers', 'name' )
        self.tool_runners = self.__read_tool_job_config( global_conf_parser, 'galaxy:tool_runners', 'url' )
        self.datatypes_config = kwargs.get( 'datatypes_config_file', 'datatypes_conf.xml' )
        # Cloud configuration options
        self.enable_cloud_launch = string_as_bool( kwargs.get( 'enable_cloud_launch', False ) )
        # Galaxy messaging (AMQP) configuration options
        self.amqp = {}
        try:
            amqp_config = global_conf_parser.items("galaxy_amqp")
        except ConfigParser.NoSectionError:
            amqp_config = {}
        for k, v in amqp_config:
            self.amqp[k] = v
        self.running_functional_tests = string_as_bool( kwargs.get( 'running_functional_tests', False ) )
    def __read_tool_job_config( self, global_conf_parser, section, key ):
        try:
            tool_runners_config = global_conf_parser.items( section )

            # Process config to group multiple configs for the same tool.
            rval = {}
            for entry in tool_runners_config:
                tool_config, val = entry
                tool = None
                runner_dict = {}
                if tool_config.find("[") != -1:
                    # Found tool with additional params; put params in dict.
                    tool, params = tool_config[:-1].split( "[" )
                    param_dict = {}
                    for param in params.split( "," ):
                        name, value = param.split( "@" )
                        param_dict[ name ] = value
                    runner_dict[ 'params' ] = param_dict
                else:
                    tool = tool_config

                # Add runner URL.
                runner_dict[ key ] = val

                # Create tool entry if necessary.
                if tool not in rval:
                    rval[ tool ] = []

                # Add entry to runners.
                rval[ tool ].append( runner_dict )

            return rval
        except ConfigParser.NoSectionError:
            return []
    def get( self, key, default ):
        return self.config_dict.get( key, default )
    def get_bool( self, key, default ):
        if key in self.config_dict:
            return string_as_bool( self.config_dict[key] )
        else:
            return default
    def check( self ):
        paths_to_check = [ self.root, self.tool_path, self.tool_data_path, self.template_path ]
        # Check that required directories exist
        for path in paths_to_check:
            if path not in [ None, False ] and not os.path.isdir( path ):
                try:
                    os.makedirs( path )
                except Exception, e:
                    raise ConfigurationError( "Unable to create missing directory: %s\n%s" % ( path, e ) )
        # Create the directories that it makes sense to create
        for path in self.file_path, \
                    self.new_file_path, \
                    self.job_working_directory, \
                    self.cluster_files_directory, \
                    self.template_cache, \
                    self.ftp_upload_dir, \
                    self.library_import_dir, \
                    self.user_library_import_dir, \
                    self.nginx_upload_store, \
                    './static/genetrack/plots', \
                    self.whoosh_index_dir, \
                    os.path.join( self.tool_data_path, 'shared', 'jars' ):
            if path not in [ None, False ] and not os.path.isdir( path ):
                try:
                    os.makedirs( path )
                except Exception, e:
                    raise ConfigurationError( "Unable to create missing directory: %s\n%s" % ( path, e ) )
        # Check that required files exist
        tool_configs = self.tool_configs
        if self.migrated_tools_config not in tool_configs:
            tool_configs.append( self.migrated_tools_config )
        for path in tool_configs:
            if not os.path.isfile( path ):
                raise ConfigurationError("File not found: %s" % path )
        if not os.path.isfile( self.datatypes_config ):
            raise ConfigurationError("File not found: %s" % self.datatypes_config )
        # Check for deprecated options.
        for key in self.config_dict.keys():
            if key in self.deprecated_options:
                log.warning( "Config option '%s' is deprecated and will be removed in a future release.  Please consult the latest version of the sample configuration file." % key )

    def is_admin_user( self,user ):
        """
        Determine if the provided user is listed in `admin_users`.

        NOTE: This is temporary, admin users will likely be specified in the
              database in the future.
        """
        admin_users = [ x.strip() for x in self.get( "admin_users", "" ).split( "," ) ]
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
