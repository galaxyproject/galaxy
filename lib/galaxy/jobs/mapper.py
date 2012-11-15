import logging
import inspect
import os 

log = logging.getLogger( __name__ )

import galaxy.jobs.rules

DYNAMIC_RUNNER_PREFIX = "dynamic:///"

class JobMappingException( Exception ):

    def __init__( self, failure_message ):
        self.failure_message = failure_message


class JobRunnerMapper( object ):
    """
    This class is responsible to managing the mapping of jobs
    (in the form of job_wrappers) to job runner url strings.
    """

    def __init__( self, job_wrapper, job_runner_name=None ):
        self.job_wrapper = job_wrapper
        self.job_runner_name = job_runner_name
        self.rule_modules = self.__get_rule_modules( )

    def __get_rule_modules( self ):
        unsorted_module_names = self.__get_rule_module_names( )
        ## Load modules in reverse order to allow hierarchical overrides
        ## i.e. 000_galaxy_rules.py, 100_site_rules.py, 200_instance_rules.py
        module_names = sorted( unsorted_module_names, reverse=True )
        modules = []
        for rule_module_name in module_names:
            try:
                module = __import__( rule_module_name )
                for comp in rule_module_name.split( "." )[1:]:
                    module = getattr( module, comp )
                modules.append( module )
            except BaseException, exception:
                exception_str = str( exception )
                message = "%s rule module could not be loaded: %s" % ( rule_module_name, exception_str )
                log.debug( message )
                continue
        return modules

    def __get_rule_module_names( self ):
        rules_dir = galaxy.jobs.rules.__path__[0]
        names = []
        for fname in os.listdir( rules_dir ):
            if not( fname.startswith( "_" ) ) and fname.endswith( ".py" ):
                rule_module_name = "galaxy.jobs.rules.%s" % fname[:-len(".py")]
                names.append( rule_module_name )
        return names
    
    def __invoke_expand_function( self, expand_function ):
        function_arg_names = inspect.getargspec( expand_function ).args

        possible_args = { "job_id" : self.job_wrapper.job_id, 
                          "tool" : self.job_wrapper.tool,
                          "tool_id" : self.job_wrapper.tool.id,
                          "job_wrapper" : self.job_wrapper,
                          "app" : self.job_wrapper.app }
        
        actual_args = {}

        # Populate needed args
        for possible_arg_name in possible_args:
            if possible_arg_name in function_arg_names:
                actual_args[ possible_arg_name ] = possible_args[ possible_arg_name ]

        # Don't hit the DB to load the job object if not needed
        if "job" in function_arg_names or "user" in function_arg_names or "user_email" in function_arg_names:
            job = self.job_wrapper.get_job()
            history = job.history
            user = history and history.user
            user_email = user and str(user.email)

            if "job" in function_arg_names:
                actual_args[ "job" ] = job

            if "user" in function_arg_names:
                actual_args[ "user" ] = user
                
            if "user_email" in function_arg_names:
                actual_args[ "user_email" ] = user_email

        return expand_function( **actual_args )

    def __determine_expand_function_name( self, option_parts ):
        # default look for function with same name as tool, unless one specified
        expand_function_name = self.job_wrapper.tool.id
        if len( option_parts ) > 1:
            expand_function_name = option_parts[ 1 ]
        return expand_function_name

    def __get_expand_function( self, expand_function_name ):
        matching_rule_module = self.__last_rule_module_with_function( expand_function_name )
        if matching_rule_module:
            expand_function = getattr( matching_rule_module, expand_function_name )
            return expand_function
        else:
            raise Exception( "Dynamic job runner cannot find function to expand job runner type - %s" % expand_function_name )

    def __last_rule_module_with_function( self, function_name ):
        # self.rule_modules is sorted in reverse order, so find first
        # wiht function
        for rule_module in self.rule_modules:
            if hasattr( rule_module, function_name ):
                return rule_module
        return None
                
    def __expand_dynamic_job_runner_url( self, options_str ):
        option_parts = options_str.split( '/' )
        expand_type = option_parts[ 0 ]
        if expand_type == "python":
            expand_function_name = self.__determine_expand_function_name( option_parts )
            expand_function = self.__get_expand_function( expand_function_name )
            return self.__invoke_expand_function( expand_function )
        else:
            raise Exception( "Unhandled dynamic job runner type specified - %s" % expand_type )

    def __cache_job_runner_url( self, params ):
        # If there's already a runner set in the Job object, don't overwrite from the tool
        if self.job_runner_name is not None:
            raw_job_runner_url = self.job_runner_name
        else:
            raw_job_runner_url = self.job_wrapper.tool.get_job_runner_url( params )
        if raw_job_runner_url.startswith( DYNAMIC_RUNNER_PREFIX ):
            job_runner_url = self.__expand_dynamic_job_runner_url( raw_job_runner_url[ len( DYNAMIC_RUNNER_PREFIX ) : ] )
        else:
            job_runner_url = raw_job_runner_url
        self.cached_job_runner_url = job_runner_url

    def get_job_runner_url( self, params ):
        """
        Cache the job_runner_url string to avoid recalculation.
        """
        if not hasattr( self, 'cached_job_runner_url' ):
            self.__cache_job_runner_url( params )
        return self.cached_job_runner_url
