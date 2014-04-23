from ..instrumenters import InstrumentPlugin
from ...metrics import formatting

import logging
log = logging.getLogger( __name__ )


class EnvFormatter( formatting.JobMetricFormatter ):

    def format( self, key, value ):
        return ( "%s (runtime environment variable)" % key, value )


class EnvPlugin( InstrumentPlugin ):
    """ Instrumentation plugin capable of recording all or specific environment
    variables for a job at runtime.
    """
    plugin_type = "env"
    formatter = EnvFormatter()

    def __init__( self, **kwargs ):
        variables_str = kwargs.get( "variables", None )
        if variables_str:
            variables = [ v.strip() for v in variables_str.split(",") ]
        else:
            variables = None
        self.variables = variables

    def pre_execute_instrument( self, job_directory ):
        """ Use env to dump all environment variables to a file.
        """
        return "env > '%s'" % self.__env_file( job_directory )

    def post_execute_instrument( self, job_directory ):
        return None

    def job_properties( self, job_id, job_directory ):
        """ Recover environment variables dumped out on compute server and filter
        out specific variables if needed.
        """
        variables = self.variables

        properties = {}
        for line in open( self.__env_file( job_directory ) ).readlines():
            var, value = line.split( "=", 1 )
            if not variables or var in variables:
                properties[ var ] = value

        return properties

    def __env_file( self, job_directory ):
        return self._instrument_file_path( job_directory, "vars" )

__all__ = [ EnvPlugin ]
