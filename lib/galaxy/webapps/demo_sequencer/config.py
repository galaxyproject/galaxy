"""
Universe configuration builder.
"""

import sys, os
import logging, logging.config
from optparse import OptionParser
import ConfigParser
from galaxy.util import string_as_bool

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
    def __init__( self, **kwargs ):
        self.config_dict = kwargs
        self.root = kwargs.get( 'root_dir', '.' )
        # Collect the umask and primary gid from the environment
        self.umask = os.umask( 077 ) # get the current umask
        os.umask( self.umask ) # can't get w/o set, so set it back
        # Where dataset files are stored
        self.file_path = resolve_path( kwargs.get( "file_path", "database/files" ), self.root )
        self.new_file_path = resolve_path( kwargs.get( "new_file_path", "database/tmp" ), self.root )
        self.cookie_path = kwargs.get( "cookie_path", "/" )
        self.test_conf = resolve_path( kwargs.get( "test_conf", "" ), self.root )
        self.id_secret = kwargs.get( "id_secret", "USING THE DEFAULT IS NOT SECURE!" )
        self.use_remote_user = string_as_bool( kwargs.get( "use_remote_user", "False" ) )
        self.remote_user_maildomain = kwargs.get( "remote_user_maildomain", None )
        self.remote_user_logout_href = kwargs.get( "remote_user_logout_href", None )
        self.require_login = string_as_bool( kwargs.get( "require_login", "False" ) )
        self.allow_user_creation = string_as_bool( kwargs.get( "allow_user_creation", "True" ) )
        self.allow_user_deletion = string_as_bool( kwargs.get( "allow_user_deletion", "False" ) )
        self.template_path = resolve_path( kwargs.get( "template_path", "templates" ), self.root )
        self.template_cache = resolve_path( kwargs.get( "template_cache_path", "database/compiled_templates/demo_sequencer" ), self.root )
        self.admin_users = kwargs.get( "admin_users", "" )
        self.sendmail_path = kwargs.get('sendmail_path',"/usr/sbin/sendmail")
        self.mailing_join_addr = kwargs.get('mailing_join_addr',"galaxy-announce-join@bx.psu.edu")
        self.error_email_to = kwargs.get( 'error_email_to', None )
        self.smtp_server = kwargs.get( 'smtp_server', None )
        self.log_actions = string_as_bool( kwargs.get( 'log_actions', 'False' ) )
        self.brand = kwargs.get( 'brand', None )
        self.wiki_url = kwargs.get( 'wiki_url', 'http://wiki.g2.bx.psu.edu/FrontPage' )
        self.blog_url = kwargs.get( 'blog_url', None )
        self.screencasts_url = kwargs.get( 'screencasts_url', None )
        self.log_events = False
        self.cloud_controller_instance = False
        # Proxy features
        self.apache_xsendfile = kwargs.get( 'apache_xsendfile', False )
        self.nginx_x_accel_redirect_base = kwargs.get( 'nginx_x_accel_redirect_base', False )
        self.sequencer_actions_config = kwargs.get( 'sequencer_actions_config_file', 'galaxy/webapps/demo_sequencer/sequencer_actions.xml' )
        # Parse global_conf and save the parser
        global_conf = kwargs.get( 'global_conf', None )
        global_conf_parser = ConfigParser.ConfigParser()
        self.global_conf_parser = global_conf_parser
        if global_conf and "__file__" in global_conf:
            global_conf_parser.read(global_conf['__file__'])
    def get( self, key, default ):
        return self.config_dict.get( key, default )
    def get_bool( self, key, default ):
        if key in self.config_dict:
            return string_as_bool( self.config_dict[key] )
        else:
            return default
    def check( self ):
        # Check that required directories exist
        for path in self.root, self.file_path, self.template_path:
            if not os.path.isdir( path ):
                raise ConfigurationError("Directory does not exist: %s" % path )
    def is_admin_user( self, user ):
        """
        Determine if the provided user is listed in `admin_users`.
        """
        admin_users = self.get( "admin_users", "" ).split( "," )
        return user is not None and user.email in admin_users

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
