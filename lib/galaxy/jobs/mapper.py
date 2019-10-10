import importlib
import inspect
import logging

import galaxy.jobs.rules
from galaxy.jobs import stock_rules
from galaxy.jobs.dynamic_tool_destination import map_tool_to_destination
from galaxy.util.submodules import import_submodules
from .rule_helper import RuleHelper

log = logging.getLogger(__name__)

DYNAMIC_RUNNER_NAME = "dynamic"
DYNAMIC_DESTINATION_ID = "dynamic_legacy_from_url"

ERROR_MESSAGE_NO_RULE_FUNCTION = "Galaxy misconfigured - cannot find dynamic rule function name for destination %s."
ERROR_MESSAGE_RULE_FUNCTION_NOT_FOUND = "Galaxy misconfigured - no rule function named %s found in dynamic rule modules."


class JobMappingException(Exception):

    def __init__(self, failure_message):
        self.failure_message = failure_message


class JobNotReadyException(Exception):

    def __init__(self, job_state=None, message=None):
        self.job_state = job_state
        self.message = message


STOCK_RULES = dict(
    choose_one=stock_rules.choose_one,
    burst=stock_rules.burst,
    docker_dispatch=stock_rules.docker_dispatch,
    dtd=map_tool_to_destination,
)


class JobRunnerMapper(object):
    """
    This class is responsible to managing the mapping of jobs
    (in the form of job_wrappers) to job runner url strings.
    """

    def __init__(self, job_wrapper, url_to_destination, job_config):
        self.job_wrapper = job_wrapper
        self.url_to_destination = url_to_destination
        self.job_config = job_config

        self.rules_module = galaxy.jobs.rules

        if job_config.dynamic_params is not None:
            module_name = job_config.dynamic_params['rules_module']
            self.rules_module = importlib.import_module(module_name)

    def __invoke_expand_function(self, expand_function, destination):
        function_arg_names = inspect.getargspec(expand_function).args
        app = self.job_wrapper.app
        possible_args = {
            "job_id": self.job_wrapper.job_id,
            "tool": self.job_wrapper.tool,
            "tool_id": self.job_wrapper.tool.id,
            "job_wrapper": self.job_wrapper,
            "rule_helper": RuleHelper(app),
            "app": app,
            "referrer": destination
        }

        actual_args = {}

        # Send through any job_conf.xml defined args to function
        for destination_param in destination.params.keys():
            if destination_param in function_arg_names:
                actual_args[destination_param] = destination.params[destination_param]

        # Populate needed args
        for possible_arg_name in possible_args:
            if possible_arg_name in function_arg_names:
                actual_args[possible_arg_name] = possible_args[possible_arg_name]

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
                actual_args["job"] = job

            if "user" in function_arg_names:
                actual_args["user"] = user

            if "user_email" in function_arg_names:
                actual_args["user_email"] = user_email

            if "resource_params" in function_arg_names:
                actual_args["resource_params"] = self.job_wrapper.get_resource_parameters(job)

            if "workflow_invocation_uuid" in function_arg_names:
                param_values = job.raw_param_dict()
                workflow_invocation_uuid = param_values.get("__workflow_invocation_uuid__", None)
                actual_args["workflow_invocation_uuid"] = workflow_invocation_uuid

            if "workflow_resource_params" in function_arg_names:
                param_values = job.raw_param_dict()
                workflow_resource_params = param_values.get("__workflow_resource_params__", None)
                actual_args["workflow_resource_params"] = workflow_resource_params

        return expand_function(**actual_args)

    def __job_params(self, job):
        app = self.job_wrapper.app
        param_values = job.get_param_values(app, ignore_errors=True)
        return param_values

    def __convert_url_to_destination(self, url):
        """
        Job runner URLs are deprecated, but dynamic mapper functions may still
        be returning them.  Runners are expected to be able to convert these to
        destinations.

        This method calls
        JobHandlerQueue.DefaultJobDispatcher.url_to_destination, which in turn
        calls the url_to_destination method for the appropriate runner.
        """
        dest = self.url_to_destination(url)
        dest['id'] = DYNAMIC_DESTINATION_ID
        return dest

    def __find_function_by_tool_id(self, rule_modules):
        # default look for function with name matching an id of tool, unless one specified
        for tool_id in self.job_wrapper.tool.all_ids:
            matching_func = self.__last_matching_function_in_modules(rule_modules, tool_id)
            if matching_func:
                return matching_func
        return None

    def __get_expand_function(self, destination):
        """
        Returns the function that matches the rule. If a rules_module override
        is specified, search within that rules_module, or default to the plugin's
        top level rules_module.
        """
        rules_module_name = destination.params.get('rules_module')
        rule_modules = self.__get_rule_modules_or_defaults(rules_module_name)
        expand_function = None
        expand_function_name = destination.params.get('function')
        if expand_function_name:
            expand_function = self.__last_matching_function_in_modules(
                rule_modules, expand_function_name)
            if not expand_function:
                message = ERROR_MESSAGE_RULE_FUNCTION_NOT_FOUND % expand_function_name
                raise Exception(message)
        else:
            expand_function = self.__find_function_by_tool_id(rule_modules)
            if not expand_function:
                message = ERROR_MESSAGE_NO_RULE_FUNCTION % destination
                raise Exception(message)
        return expand_function

    def __get_rule_modules_or_defaults(self, rules_module_name):
        """
        Returns the rules under the given rules_module_name or default
        to returning the rules of the top-level rules module for the plugin
        """
        if rules_module_name:
            rules_module = importlib.import_module(rules_module_name)
        else:
            rules_module = self.rules_module
        return import_submodules(rules_module, ordered=True)

    def __last_matching_function_in_modules(self, rule_modules, function_name):
        # self.rule_modules is sorted in reverse order, so find first
        # with function
        for rule_module in rule_modules:
            if hasattr(rule_module, function_name):
                return getattr(rule_module, function_name)
        return None

    def __handle_dynamic_job_destination(self, destination):
        expand_type = destination.params.get('type', "python")
        expand_function = None
        if expand_type == "python":
            expand_function = self.__get_expand_function(destination)
        elif expand_type in STOCK_RULES:
            expand_function = STOCK_RULES[expand_type]
        else:
            raise Exception("Unhandled dynamic job runner type specified - %s" % expand_type)

        return self.__handle_rule(expand_function, destination)

    def __handle_rule(self, rule_function, destination):
        job_destination = self.__invoke_expand_function(rule_function, destination)
        if not isinstance(job_destination, galaxy.jobs.JobDestination):
            job_destination_rep = str(job_destination)  # Should be either id or url
            if '://' in job_destination_rep:
                job_destination = self.__convert_url_to_destination(job_destination_rep)
            else:
                job_destination = self.job_config.get_destination(job_destination_rep)
        return job_destination

    def __determine_job_destination(self, params, raw_job_destination=None):
        if raw_job_destination is None:
            raw_job_destination = self.job_wrapper.tool.get_job_destination(params)
        if raw_job_destination.runner == DYNAMIC_RUNNER_NAME:
            job_destination = self.__handle_dynamic_job_destination(raw_job_destination)
            log.debug("(%s) Mapped job to destination id: %s", self.job_wrapper.job_id, job_destination.id)
            # Recursively handle chained dynamic destinations
            if job_destination.runner == DYNAMIC_RUNNER_NAME:
                return self.__determine_job_destination(params, raw_job_destination=job_destination)
        else:
            job_destination = raw_job_destination
            log.debug("(%s) Mapped job to destination id: %s", self.job_wrapper.job_id, job_destination.id)
        return job_destination

    def __cache_job_destination(self, params, raw_job_destination=None):
        self.cached_job_destination = self.__determine_job_destination(
            params, raw_job_destination=raw_job_destination)
        return self.cached_job_destination

    def get_job_destination(self, params):
        """
        cached_job_destination is a public property that is sometimes
        externally set to short-circuit the mapper, such as during resubmits.
        get_job_destination will respect that and not run the mapper if so.
        """
        if not hasattr(self, 'cached_job_destination'):
            return self.__cache_job_destination(params)
        return self.cached_job_destination

    def cache_job_destination(self, raw_job_destination):
        """
        Force update of cached_job_destination to mapper determined job
        destination, overwriting any externally set cached_job_destination
        """
        return self.__cache_job_destination(
            None, raw_job_destination=raw_job_destination)
