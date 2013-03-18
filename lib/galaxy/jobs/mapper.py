import logging
import inspect
import os 

log = logging.getLogger( __name__ )

import galaxy.jobs.rules

DYNAMIC_RUNNER_NAME = "dynamic"
DYNAMIC_DESTINATION_ID = "dynamic_legacy_from_url"

class JobMappingException( Exception ):

    def __init__( self, failure_message ):
        self.failure_message = failure_message


class JobRunnerMapper( object ):
    """
    This class is responsible to managing the mapping of jobs
    (in the form of job_wrappers) to job runner url strings.
    """

    def __init__( self, job_wrapper, url_to_destination ):
        self.job_wrapper = job_wrapper
        self.url_to_destination = url_to_destination
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

    def __convert_url_to_destination( self, url ):
        """
        Job runner URLs are deprecated, but dynamic mapper functions may still
        be returning them.  Runners are expected to be able to convert these to
        destinations.

        This method calls
        JobHandlerQueue.DefaultJobDispatcher.url_to_destination, which in turn
        calls the url_to_destination method for the appropriate runner.
        """
        dest = self.url_to_destination( url )
        dest['id'] = DYNAMIC_DESTINATION_ID
        return dest

    def __determine_expand_function_name( self, destination ):
        # default look for function with same name as tool, unless one specified
        expand_function_name = destination.params.get('function', self.job_wrapper.tool.id)
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
                
    def __handle_dynamic_job_destination( self, destination ):
        expand_type = destination.params.get('type', None)
        if expand_type == "python":
            expand_function_name = self.__determine_expand_function_name( destination )
            expand_function = self.__get_expand_function( expand_function_name )
            rval = self.__invoke_expand_function( expand_function )
            # TODO: test me extensively
            if isinstance(rval, basestring):
                # If the function returned a string, check if it's a URL, convert if necessary
                if '://' in rval:
                    return self.__convert_url_to_destination(rval)
                else:
                    return self.app.job_config.get_destination(rval)
            elif isinstance(rval, galaxy.jobs.JobDestination):
                # If the function generated a JobDestination, we'll use that
                # destination directly.  However, for advanced job limiting, a
                # function may want to set the JobDestination's 'tags'
                # attribute so that limiting can be done on a destination tag.
                #id_or_tag = rval.get('id')
                #if rval.get('tags', None):
                #    # functions that are generating destinations should only define one tag
                #    id_or_tag = rval.get('tags')[0]
                #return id_or_tag, rval
                return rval
            else:
                raise Exception( 'Dynamic function returned a value that could not be understood: %s' % rval )
        elif expand_type is None:
            raise Exception( 'Dynamic function type not specified (hint: add <param id="type">python</param> to your <destination>)' )
        else:
            raise Exception( "Unhandled dynamic job runner type specified - %s" % expand_type )

    def __cache_job_destination( self, params ):
        raw_job_destination = self.job_wrapper.tool.get_job_destination( params )
        #raw_job_destination_id_or_tag = self.job_wrapper.tool.get_job_destination_id_or_tag( params )
        if raw_job_destination.runner == DYNAMIC_RUNNER_NAME:
            job_destination = self.__handle_dynamic_job_destination( raw_job_destination )
        else:
            job_destination = raw_job_destination
            #job_destination_id_or_tag = raw_job_destination_id_or_tag
        self.cached_job_destination = job_destination
        #self.cached_job_destination_id_or_tag = job_destination_id_or_tag

    def get_job_destination( self, params ):
        """
        Cache the job_destination to avoid recalculation.
        """
        if not hasattr( self, 'cached_job_destination' ):
            self.__cache_job_destination( params )
        return self.cached_job_destination

    #def get_job_destination_id_or_tag( self, params ):
    #    if not hasattr( self, 'cached_job_destination_id_or_tag' ):
    #        self.__cache_job_destination( params )
    #    return self.cached_job_destination_id_or_tag
