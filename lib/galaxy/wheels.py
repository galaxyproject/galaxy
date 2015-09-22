"""
"""

import sys

try:
    import configparser
except:
    import ConfigParser as configparser


OPTIONAL_REQUIREMENTS = (
    'pysqlite',
    'psycopg2',
)


class GalaxyConfig( object ):
    def __init__( self, config_file ):
        self.config = configparser.ConfigParser()
        if self.config.read( config_file ) == []:
            raise Exception( "error: unable to read Galaxy config from %s" % config_file )

    def check( self, name ):
        # SQLite is different since it can be specified in two config vars and defaults to True
        if name == "pysqlite":
            try:
                return self.config.get( "app:main", "database_connection" ).startswith( "sqlite://" )
            except:
                return True
        else:
            try:
                return { "psycopg2": lambda: self.config.get( "app:main", "database_connection" ).startswith( "postgres" ),
                         "MySQL_python": lambda: self.config.get( "app:main", "database_connection" ).startswith( "mysql://" ),
                         "DRMAA_python": lambda: "sge" in self.config.get( "app:main", "start_job_runners" ).split(","),
                         "drmaa": lambda: "drmaa" in self.config.get( "app:main", "start_job_runners" ).split(","),
                         "pbs_python": lambda: "pbs" in self.config.get( "app:main", "start_job_runners" ).split(","),
                         "openid": lambda: self.config.get( "app:main", "enable_openid" ),
                         "python_daemon": lambda: sys.version_info[:2] >= ( 2, 5 ),
                         "PyRods": lambda: self.config.get( "app:main", "object_store" ) == "irods"
                         }.get( name, lambda: True )()
            except:
                return False


def optional( config_file ):
    config = GalaxyConfig( config_file )
    return [ opt for opt in OPTIONAL_REQUIREMENTS if config.check( opt ) ]
