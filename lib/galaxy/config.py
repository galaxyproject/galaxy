"""
Universe configuration builder.
"""

import sys, os
import logging, logging.config
from optparse import OptionParser

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
        self.database = resolve_path( kwargs.get( "database_file", "database/universe.d" ), self.root )
        self.database_connection =  kwargs.get( "database_connection", False )
        self.file_path = resolve_path( kwargs.get( "file_path", "database/files" ), self.root )
        self.tool_path = resolve_path( kwargs.get( "tool_path", "tools" ), self.root )
        self.test_conf = resolve_path( kwargs.get( "test_conf", "" ), self.root )
        self.tool_config = resolve_path( kwargs.get( 'tool_config_file', 'tool_conf.xml' ), self.root )
        self.template_path = resolve_path( kwargs.get( "template_path", "templates" ), self.root )
        self.template_cache = resolve_path( kwargs.get( "template_cache_path", "database/compiled_templates" ), self.root )
        self.job_queue_workers = int( kwargs.get( "job_queue_workers", "10" ) )
        self.admin_pass = kwargs.get('admin_pass',"galaxy")
        self.sendmail_path = kwargs.get('sendmail_path',"/usr/sbin/sendmail")
        self.mailing_join_addr = kwargs.get('mailing_join_addr',"galaxy-user-join@bx.psu.edu")
        self.error_email_to = kwargs.get( 'error_email_to', None )
        self.smtp_server = kwargs.get( 'smtp_server', None )
        self.use_pbs = kwargs.get('use_pbs', False )
        self.pbs_server = kwargs.get('pbs_server', "" )
        self.pbs_instance_path = kwargs.get('pbs_instance_path', os.getcwd() )
        self.pbs_application_server = kwargs.get('pbs_application_server', "" )
        self.pbs_dataset_server = kwargs.get('pbs_dataset_server', "" )
        self.pbs_dataset_path = kwargs.get('pbs_dataset_path', "" )
        self.use_heartbeat = kwargs.get( 'use_heartbeat', False )
    def get( self, key, default ):
        return self.config_dict.get( key, default )
    def check( self ):
        # Check that required directories exist
        for path in self.root, self.file_path, self.tool_path, self.template_path:
            if not os.path.isdir( path ):
                raise ConfigurationError("Directory does not exist: %s" % path )
        # Check that required files exist
        for path in self.tool_config,:
            if not os.path.isfile(path):
                raise ConfigurationError("File not found: %s" % path )

def configure_logging( config ):
    """
    Allow some basic logging configuration to be read from the cherrpy
    config.
    """
    format = config.get( "log_format", "%(name)s %(levelname)s %(asctime)s %(message)s" )
    level = logging._levelNames[ config.get( "log_level", "DEBUG" ) ]
    destination = config.get( "log_destination", "stdout" )
    log.info( "Logging at '%s' level to '%s'" % ( level, destination ) )
    # Get root logger
    root = logging.getLogger()
    # Set level
    root.setLevel( level )
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
    
    
