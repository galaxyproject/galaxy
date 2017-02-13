import logging
import inspect
import os
import sys

import galaxy.jobs.rules
from galaxy.jobs import stock_rules
from galaxy.jobs.dynamic_tool_destination import map_tool_to_destination
from .rule_helper import RuleHelper

log = logging.getLogger( __name__ )

DYNAMIC_RUNNER_NAME = "dynamic"
DYNAMIC_DESTINATION_ID = "dynamic_legacy_from_url"

ERROR_MESSAGE_NO_RULE_FUNCTION = "Galaxy misconfigured - cannot find dynamic rule function name for destination %s."
ERROR_MESSAGE_RULE_FUNCTION_NOT_FOUND = "Galaxy misconfigured - no rule function named %s found in dynamic rule modules."


class JobMappingException( Exception ):

    def __init__( self, failure_message ):
        self.failure_message = failure_message


class JobNotReadyException( Exception ):

    def __init__( self, job_state=None, message=None ):
        self.job_state = job_state
        self.message = message


STOCK_RULES = dict(
    choose_one=stock_rules.choose_one,
    burst=stock_rules.burst,
    docker_dispatch=stock_rules.docker_dispatch,
    dtd=map_tool_to_destination,
)


class JobRunnerMapper( object ):
    """
    This class is responsible to managing the mapping of jobs
    (in the form of job_wrappers) to job runner url strings.
    """

    def __init__( self, job_wrapper, url_to_destination, job_config ):
        self.job_wrapper = job_wrapper
        self.url_to_destination = url_to_destination
        self.job_config = job_config

        self.rules_module = galaxy.jobs.rules

        if job_config.dynamic_params is not None:
            rules_module_name = job_config.dynamic_params['rules_module']
            __import__(rules_module_name)
            self.rules_module = sys.modules[rules_module_name]

    def __get_rule_modules( self ):
        unsorted_module_names = self.__get_rule_module_names( )
        # Load modules in reverse order to allow hierarchical overrides
        # i.e. 000_galaxy_rules.py, 100_site_rules.py, 200_instance_rules.py
        module_names = sorted( unsorted_module_names, reverse=True )
        modules = []
        for rule_module_name in module_names:
            try:
                module = __import__( rule_module_name )
                for comp in rule_module_name.split( "." )[1:]:
                    module = getattr( module, comp )
                modules.append( module )
            except BaseException as exception:
                exception_str = str( exception )
                message = "%s rule module could not be loaded: %s" % ( rule_module_name, exception_str )
                log.debug( message )
                continue
        return modules

    def __get_rule_module_names( self ):
        rules_dir = self.rules_module.__path__[0]
        names = []
        for fname in os.listdir( rules_dir ):
            if not( fname.startswith( "_" ) ) and fname.endswith( ".py" ):
                base_name = self.rules_module.__name__
                rule_module_name = "%s.%s" % (base_name, fname[:-len(".py")])
                names.append( rule_module_name )
        return names

    def __invoke_expand_function( self, expand_function, destination_params ):
        function_arg_names = inspect.getargspec( expand_function ).args
        app = self.job_wrapper.app
        possible_args = {
            "job_id": self.job_wrapper.job_id,
            "tool": self.job_wrapper.tool,
            "tool_id": self.job_wrapper.tool.id,
            "job_wrapper": self.job_wrapper,
            "rule_helper": RuleHelper( app ),
            "app": app
        }

        actual_args = {}

        # Send through any job_conf.xml defined args to function
        for destination_param in destination_params.keys():
            if destination_param in function_arg_names:
                actual_args[ destination_param ] = destination_params[ destination_param ]

        # Populate needed args
        for possible_arg_name in possible_args:
            if possible_arg_name in function_arg_names:
                actual_args[ possible_arg_name ] = possible_args[ possible_arg_name ]

        # Don't hit the DB to load the job object if not needed
        require_db = False
        for param in ["job", "user", "user_email", "resource_params", "workflow_invocation_uuid"]:
            if param in function_arg_names:
                require_db = True
                break
        if require_db:
            job = self.job_wrapper.get_job()
            user = job.user
            user_email = user and str(user.email)

            if "job" in function_arg_names:
                actual_args[ "job" ] = job

            if "user" in function_arg_names:
                actual_args[ "user" ] = user

            if "user_email" in function_arg_names:
                actual_args[ "user_email" ] = user_email

            if "resource_params" in function_arg_names:
                actual_args[ "resource_params" ] = self.job_wrapper.get_resource_parameters( job )

            if "workflow_invocation_uuid" in function_arg_names:
                param_values = job.raw_param_dict( )
                workflow_invocation_uuid = param_values.get( "__workflow_invocation_uuid__", None )
                actual_args[ "workflow_invocation_uuid" ] = workflow_invocation_uuid

        return expand_function( **actual_args )

    def __job_params( self, job ):
        app = self.job_wrapper.app
        param_values = job.get_param_values( app, ignore_errors=True )
        return param_values

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
        # default look for function with name matching an id of tool, unless one specified
        expand_function_name = destination.params.get('function', None)
        if not expand_function_name:
            for tool_id in self.job_wrapper.tool.all_ids:
                if self.__last_rule_module_with_function( tool_id ):
                    expand_function_name = tool_id
                    break
        return expand_function_name

    def __get_expand_function( self, expand_function_name ):
        matching_rule_module = self.__last_rule_module_with_function( expand_function_name )
        if matching_rule_module:
            expand_function = getattr( matching_rule_module, expand_function_name )
            return expand_function
        else:
            message = ERROR_MESSAGE_RULE_FUNCTION_NOT_FOUND % ( expand_function_name )
            raise Exception( message )

    def __last_rule_module_with_function( self, function_name ):
        # self.rule_modules is sorted in reverse order, so find first
        # wiht function
        for rule_module in self.__get_rule_modules( ):
            if hasattr( rule_module, function_name ):
                return rule_module
        return None

    def __handle_dynamic_job_destination( self, destination ):
        expand_type = destination.params.get('type', "python")
        expand_function = None
        if expand_type == "python":
            expand_function_name = self.__determine_expand_function_name( destination )
            if not expand_function_name:
                message = ERROR_MESSAGE_NO_RULE_FUNCTION % destination
                raise Exception( message )

            expand_function = self.__get_expand_function( expand_function_name )
        elif expand_type in STOCK_RULES:
            expand_function = STOCK_RULES[ expand_type ]
        else:
            raise Exception( "Unhandled dynamic job runner type specified - %s" % expand_type )

        return self.__handle_rule( expand_function, destination )

    def __handle_rule( self, rule_function, destination ):
        job_destination = self.__invoke_expand_function( rule_function, destination.params )
        if not isinstance(job_destination, galaxy.jobs.JobDestination):
            job_destination_rep = str(job_destination)  # Should be either id or url
            if '://' in job_destination_rep:
                job_destination = self.__convert_url_to_destination(job_destination_rep)
            else:
                job_destination = self.job_config.get_destination(job_destination_rep)
        return job_destination

    def __cache_job_destination( self, params, raw_job_destination=None ):
        if raw_job_destination is None:
            raw_job_destination = self.job_wrapper.tool.get_job_destination( params )
        if raw_job_destination.runner == DYNAMIC_RUNNER_NAME:
            job_destination = self.__handle_dynamic_job_destination( raw_job_destination )
        else:
            job_destination = raw_job_destination
        self.cached_job_destination = job_destination

    def get_job_destination( self, params ):
        """
        Cache the job_destination to avoid recalculation.
        """
        if not hasattr( self, 'cached_job_destination' ):
            self.__cache_job_destination( params )
        return self.cached_job_destination

    def cache_job_destination( self, raw_job_destination ):
        self.__cache_job_destination( None, raw_job_destination=raw_job_destination )
        return self.cached_job_destination
