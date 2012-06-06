import inspect, sys

import galaxy.jobs.rules

DYNAMIC_RUNNER_PREFIX = "dynamic:///"

class JobRunnerMapper( object ):
    
    def __init__( self, job_wrapper ):
        self.job_wrapper = job_wrapper
    
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

        # Don't hit the DB to load the job object is not needed
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
        rules_module = sys.modules[ "galaxy.jobs.rules" ]
        if hasattr( rules_module, expand_function_name ):
            expand_function = getattr( rules_module, expand_function_name )
            return expand_function
        else:
            raise Exception( "Dynamic job runner cannot find function to expand job runner type - %s" % expand_function_name )
        
    def __expand_dynamic_job_runner( self, options_str ):
        option_parts = options_str.split( '/' )
        expand_type = option_parts[ 0 ]
        if expand_type == "python":
            expand_function_name = self.__determine_expand_function_name( option_parts )
            expand_function = self.__get_expand_function( expand_function_name )
            return self.__invoke_expand_function( expand_function )
        else:
            raise Exception( "Unhandled dynamic job runner type specified - %s" % calculation_type )

    def __cache_job_runner( self, params ):
        raw_job_runner = self.job_wrapper.tool.get_job_runner( params )
        if raw_job_runner.startswith( DYNAMIC_RUNNER_PREFIX ):
            job_runner = self.__expand_dynamic_job_runner( raw_job_runner[ len( DYNAMIC_RUNNER_PREFIX ) : ] )
        else:
            job_runner = raw_job_runner
        self.cached_job_runner = job_runner

    def get_job_runner( self, params ):
        if not hasattr( self, 'cached_job_runner' ):
            self.__cache_job_runner( params )
        return self.cached_job_runner
