"""
Determine what optional dependencies are needed.
"""
import pkg_resources

from os.path import dirname, join
from xml.etree import ElementTree

from galaxy.util import asbool
from galaxy.util.properties import load_app_properties


class ConditionalDependencies( object ):
    def __init__( self, config_file ):
        self.config_file = config_file
        self.config = None
        self.job_runners = []
        self.authenticators = []
        self.object_stores = []
        self.conditional_reqs = []
        self.parse_configs()
        self.get_conditional_requirements()

    def parse_configs( self ):
        self.config = load_app_properties( ini_file=self.config_file )
        job_conf_xml = self.config.get(
            "job_config_file",
            join( dirname( self.config_file ), 'job_conf.xml' ) )
        try:
            for plugin in ElementTree.parse( job_conf_xml ).find( 'plugins' ).findall( 'plugin' ):
                if 'load' in plugin.attrib:
                    self.job_runners.append( plugin.attrib['load'] )
        except (OSError, IOError):
            pass
        object_store_conf_xml = self.config.get(
            "object_store_config_file",
            join( dirname( self.config_file ), 'object_store_conf.xml' ) )
        try:
            for store in ElementTree.parse( object_store_conf_xml ).iter( 'object_store' ):
                if 'type' in store.attrib:
                    self.object_stores.append( store.attrib['type'] )
        except (OSError, IOError):
            pass

        # Parse auth conf
        auth_conf_xml = self.config.get(
            "auth_config_file",
            join( dirname( self.config_file ), 'auth_conf.xml' ) )
        try:
            for auth in ElementTree.parse( auth_conf_xml ).findall( 'authenticator' ):
                auth_type = auth.find('type')
                if auth_type is not None:
                    self.authenticators.append( auth_type.text )
        except (OSError, IOError):
            pass

    def get_conditional_requirements( self ):
        crfile = join( dirname( __file__ ), 'conditional-requirements.txt' )
        for req in pkg_resources.parse_requirements( open( crfile ).readlines() ):
            self.conditional_reqs.append( req )

    def check( self, name ):
        try:
            name = name.replace('-', '_').replace('.', '_')
            return getattr( self, 'check_' + name )()
        except:
            return False

    def check_psycopg2( self ):
        return self.config["database_connection"].startswith( "postgres" )

    def check_mysql_python( self ):
        return self.config["database_connection"].startswith( "mysql" )

    def check_drmaa( self ):
        return ("galaxy.jobs.runners.drmaa:DRMAAJobRunner" in self.job_runners or
                "galaxy.jobs.runners.slurm:SlurmJobRunner" in self.job_runners)

    def check_pbs_python( self ):
        return "galaxy.jobs.runners.pbs:PBSJobRunner" in self.job_runners

    def check_python_openid( self ):
        return asbool( self.config["enable_openid"] )

    def check_fluent_logger( self ):
        return asbool( self.config["fluent_log"] )

    def check_raven( self ):
        return self.config.get("sentry_dsn", None) is not None

    def check_statsd( self ):
        return self.config.get("statsd_host", None) is not None

    def check_weberror( self ):
        return ( asbool( self.config["debug"] ) and
                 asbool( self.config["use_interactive"] ) )

    def check_pygments( self ):
        # pygments is a dependency of weberror and only weberror
        return self.check_weberror()

    def check_python_ldap( self ):
        return ('ldap' in self.authenticators or
                'activedirectory' in self.authenticators)

    def check_azure_storage( self ):
        return 'azure_blob' in self.object_stores


def optional( config_file ):
    rval = []
    conditional = ConditionalDependencies( config_file )
    for opt in conditional.conditional_reqs:
        if conditional.check( opt.key ):
            rval.append( str( opt ) )
    return rval
