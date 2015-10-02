"""
Determine what optional dependencies are needed.
"""

try:
    import configparser
except:
    import ConfigParser as configparser

import pkg_resources

from os.path import dirname, join
from xml.etree import ElementTree

from galaxy.util import asbool


class ConditionalDependencies( object ):
    def __init__( self, config_file ):
        self.config_file = config_file
        self.config = None
        self.job_runners = []
        self.conditional_reqs = []
        self.parse_configs()
        self.get_conditional_requirements()

    def parse_configs( self ):
        self.config = configparser.ConfigParser()
        if not self.config.read( self.config_file ):
            raise Exception( "Unable to read Galaxy config from %s" % self.config_file )
        try:
            job_conf_xml = self.config.get( "app:main", "job_config_file" )
        except configparser.NoOptionError:
            job_conf_xml = join( dirname( self.config_file ), 'job_conf.xml')
        try:
            for plugin in ElementTree.parse( job_conf_xml ).find( 'plugins' ):
                self.job_runners.append( plugin.attrib['load'] )
        except (OSError, IOError):
            pass

    def get_conditional_requirements( self ):
        crfile = join( dirname( __file__ ), 'conditional_requirements.txt' )
        for req in pkg_resources.parse_requirements( open( crfile ).readlines() ):
            self.conditional_reqs.append( req )

    def check( self, name ):
        try:
            name = name.replace('-', '_').replace('.', '_')
            return getattr( self, 'check_' + name )()
        except:
            return False

    def check_psycopg2( self ):
        return self.config.get( "app:main", "database_connection" ).startswith( "postgres" )

    def check_mysql_python( self ):
        return self.config.get( "app:main", "database_connection" ).startswith( "mysql" )

    def check_drmaa( self ):
        return ("galaxy.jobs.runners.drmaa:DRMAAJobRunner" in self.job_runners or
                "galaxy.jobs.runners.slurm:SlurmJobRunner" in self.job_runners)

    def check_pbs_python( self ):
        return "galaxy.jobs.runners.pbs:PBSJobRunner" in self.job_runners

    def check_python_openid( self ):
        return asbool( self.config.get( "app:main", "enable_openid" ) )

    def check_fluent_logger( self ):
        return asbool( self.config.get( "app:main", "fluent_log" ) )

    def check_raven( self ):
        return asbool( self.config.get( "app:main", "sentry_dsn" ) )

    def check_weberror( self ):
        return ( asbool( self.config.get( "app:main", "debug" ) ) and
                 asbool( self.config_get( "app:main", "use_interactive" ) ) )


def optional( config_file ):
    rval = []
    conditional = ConditionalDependencies( config_file )
    for opt in conditional.conditional_reqs:
        if conditional.check( opt.key ):
            rval.append( str( opt ) )
    return rval
