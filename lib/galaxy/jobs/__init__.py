"""
Support for running a tool in Galaxy via an internal job management system
"""
import copy
import datetime
import errno
import logging
import os
import pwd
import shlex
import shutil
import string
import subprocess
import sys
import time
import traceback
from abc import ABCMeta, abstractmethod
from json import loads
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree

import six
from pulsar.client.staging import COMMAND_VERSION_FILENAME

import galaxy
from galaxy import model, util
from galaxy.datatypes import sniff
from galaxy.exceptions import ObjectInvalid, ObjectNotFound
from galaxy.jobs.actions.post import ActionBox
from galaxy.jobs.mapper import JobRunnerMapper
from galaxy.jobs.runners import BaseJobRunner, JobState
from galaxy.metadata import get_metadata_compute_strategy
from galaxy.objectstore import ObjectStorePopulator
from galaxy.util import safe_makedirs, unicodify
from galaxy.util.bunch import Bunch
from galaxy.util.expressions import ExpressionContext
from galaxy.util.xml_macros import load
from galaxy.web.stack.handlers import ConfiguresHandlers
from .datasets import (DatasetPath, NullDatasetPathRewriter,
    OutputsToWorkingDirectoryPathRewriter, TaskPathRewriter)
from .output_checker import check_output, DETECTED_JOB_STATE

log = logging.getLogger(__name__)

# Legacy definition - this is read by certain misbehaving tool wrappers
# that import Galaxy internals - but it shouldn't be used in Galaxy's code
# itself.
TOOL_PROVIDED_JOB_METADATA_FILE = 'galaxy.json'
TOOL_PROVIDED_JOB_METADATA_KEYS = ['name', 'info', 'dbkey']

# Override with config.default_job_shell.
DEFAULT_JOB_SHELL = '/bin/bash'
DEFAULT_LOCAL_WORKERS = 4

DEFAULT_CLEANUP_JOB = "always"


class JobDestination(Bunch):
    """
    Provides details about where a job runs
    """

    def __init__(self, **kwds):
        self['id'] = None
        self['url'] = None
        self['tags'] = None
        self['runner'] = None
        self['legacy'] = False
        self['converted'] = False
        self['shell'] = None
        self['env'] = []
        self['resubmit'] = []
        # dict is appropriate (rather than a bunch) since keys may not be valid as attributes
        self['params'] = dict()

        # Use the values persisted in an existing job
        if 'from_job' in kwds and kwds['from_job'].destination_id is not None:
            self['id'] = kwds['from_job'].destination_id
            self['params'] = kwds['from_job'].destination_params

        super(JobDestination, self).__init__(**kwds)

        # Store tags as a list
        if self.tags is not None:
            self['tags'] = [x.strip() for x in self.tags.split(',')]


class JobToolConfiguration(Bunch):
    """
    Provides details on what handler and destination a tool should use

    A JobToolConfiguration will have the required attribute 'id' and optional
    attributes 'handler', 'destination', and 'params'
    """

    def __init__(self, **kwds):
        self['handler'] = None
        self['destination'] = None
        self['params'] = dict()
        super(JobToolConfiguration, self).__init__(**kwds)

    def get_resource_group(self):
        return self.get("resources", None)


def config_exception(e, file):
    abs_path = os.path.abspath(file)
    message = 'Problem parsing the XML in file %s, ' % abs_path
    message += 'please correct the indicated portion of the file and restart Galaxy. '
    message += unicodify(e)
    log.exception(message)
    return Exception(message)


class JobConfiguration(ConfiguresHandlers):
    """A parser and interface to advanced job management features.

    These features are configured in the job configuration, by default, ``job_conf.xml``
    """
    DEFAULT_BASE_HANDLER_POOLS = ('job-handlers',)

    DEFAULT_NWORKERS = 4

    JOB_RESOURCE_CONDITIONAL_XML = """<conditional name="__job_resource">
        <param name="__job_resource__select" type="select" label="Job Resource Parameters">
            <option value="no">Use default job resource parameters</option>
            <option value="yes">Specify job resource parameters</option>
        </param>
        <when value="no"/>
        <when value="yes"/>
    </conditional>"""

    def __init__(self, app):
        """Parse the job configuration XML.
        """
        self.app = app
        self.runner_plugins = []
        self.dynamic_params = None
        self.handlers = {}
        self.handler_runner_plugins = {}
        self.default_handler_id = None
        self.handler_assignment_methods = None
        self.handler_assignment_methods_configured = False
        self.handler_max_grab = 1
        self.destinations = {}
        self.destination_tags = {}
        self.default_destination_id = None
        self.tools = {}
        self.resource_groups = {}
        self.default_resource_group = None
        self.resource_parameters = {}
        self.limits = Bunch(registered_user_concurrent_jobs=None,
                            anonymous_user_concurrent_jobs=None,
                            walltime=None,
                            walltime_delta=None,
                            total_walltime={},
                            output_size=None,
                            destination_user_concurrent_jobs={},
                            destination_total_concurrent_jobs={})

        default_resubmits = []
        default_resubmit_condition = self.app.config.default_job_resubmission_condition
        if default_resubmit_condition:
            default_resubmits.append(dict(
                destination=None,
                condition=default_resubmit_condition,
                handler=None,
                delay=None,
            ))
        self.default_resubmits = default_resubmits

        self.__parse_resource_parameters()
        # Initialize the config
        job_config_file = self.app.config.job_config_file
        try:
            tree = load(job_config_file)
            self.__parse_job_conf_xml(tree)
        except IOError:
            log.warning('Job configuration "%s" does not exist, using default job configuration',
                        self.app.config.job_config_file)
            self.__set_default_job_conf()
        except Exception as e:
            raise config_exception(e, job_config_file)

    def __parse_job_conf_xml(self, tree):
        """Loads the new-style job configuration from options in the job config file (by default, job_conf.xml).

        :param tree: Object representing the root ``<job_conf>`` object in the job config file.
        :type tree: ``xml.etree.ElementTree.Element``
        """
        root = tree.getroot()
        log.debug('Loading job configuration from %s' % self.app.config.job_config_file)

        # Parse job plugins
        plugins = root.find('plugins')
        if plugins is not None:
            for plugin in self._findall_with_required(plugins, 'plugin', ('id', 'type', 'load')):
                if plugin.get('type') == 'runner':
                    workers = plugin.get('workers', plugins.get('workers', JobConfiguration.DEFAULT_NWORKERS))
                    runner_kwds = self.__get_params(plugin)
                    if not self.__is_enabled(runner_kwds):
                        continue
                    runner_info = dict(id=plugin.get('id'),
                                       load=plugin.get('load'),
                                       workers=int(workers),
                                       kwds=runner_kwds)
                    self.runner_plugins.append(runner_info)
                else:
                    log.error('Unknown plugin type: %s' % plugin.get('type'))
            for plugin in self._findall_with_required(plugins, 'plugin', ('id', 'type')):
                if plugin.get('id') == 'dynamic' and plugin.get('type') == 'runner':
                    self.dynamic_params = self.__get_params(plugin)

        # Load tasks if configured
        if self.app.config.use_tasked_jobs:
            self.runner_plugins.append(dict(id='tasks', load='tasks', workers=self.app.config.local_task_queue_workers))

        # Parse handlers
        handlers_conf = root.find('handlers')
        self._init_handler_assignment_methods(handlers_conf)
        self._init_handlers(handlers_conf)
        if not self.handler_assignment_methods_configured:
            self._set_default_handler_assignment_methods()
        else:
            self.app.application_stack.init_job_handling(self)
        log.info("Job handler assignment methods set to: %s", ', '.join(self.handler_assignment_methods))
        for tag, handlers in [(t, h) for t, h in self.handlers.items() if isinstance(h, list)]:
            log.info("Tag [%s] handlers: %s", tag, ', '.join(handlers))

        # Parse destinations
        destinations = root.find('destinations')
        job_metrics = self.app.job_metrics
        for destination in self._findall_with_required(destinations, 'destination', ('id', 'runner')):
            id = destination.get('id')
            destination_metrics = destination.get("metrics", None)
            if destination_metrics:
                if not util.asbool(destination_metrics):
                    # disable
                    job_metrics.set_destination_instrumenter(id, None)
                else:
                    metrics_conf_path = self.app.config.resolve_path(destination_metrics)
                    job_metrics.set_destination_conf_file(id, metrics_conf_path)
            else:
                metrics_elements = self._findall_with_required(destination, 'job_metrics', ())
                if metrics_elements:
                    job_metrics.set_destination_conf_element(id, metrics_elements[0])
            job_destination = JobDestination(**dict(destination.items()))
            params = self.__get_params(destination)
            if not self.__is_enabled(params):
                continue

            job_destination['params'] = params
            job_destination['env'] = self.__get_envs(destination)
            destination_resubmits = self.__get_resubmits(destination)
            if destination_resubmits:
                resubmits = destination_resubmits
            else:
                resubmits = self.default_resubmits
            job_destination["resubmit"] = resubmits

            self.destinations[id] = (job_destination,)
            if job_destination.tags is not None:
                for tag in job_destination.tags:
                    if tag not in self.destinations:
                        self.destinations[tag] = []
                    self.destinations[tag].append(job_destination)

        # Determine the default destination
        self.default_destination_id = self._get_default(
            self.app.config, destinations, list(self.destinations.keys()), auto=True)

        # Parse resources...
        resources = root.find('resources')
        if resources is not None:
            self.default_resource_group = resources.get("default", None)
            for group in self._findall_with_required(resources, 'group'):
                id = group.get('id')
                fields_str = group.get('fields', None) or group.text or ''
                fields = [f for f in fields_str.split(",") if f]
                self.resource_groups[id] = fields

        # Parse tool mappings
        tools = root.find('tools')
        if tools is not None:
            for tool in self._findall_with_required(tools, 'tool'):
                # There can be multiple definitions with identical ids, but different params
                id = tool.get('id').lower().rstrip('/')
                if id not in self.tools:
                    self.tools[id] = list()
                self.tools[id].append(JobToolConfiguration(**dict(tool.items())))
                self.tools[id][-1]['params'] = self.__get_params(tool)

        types = dict(registered_user_concurrent_jobs=int,
                     anonymous_user_concurrent_jobs=int,
                     walltime=str,
                     total_walltime=str,
                     output_size=util.size_to_bytes)

        # Parse job limits
        limits = root.find('limits')
        if limits is not None:
            for limit in self._findall_with_required(limits, 'limit', ('type',)):
                type = limit.get('type')
                # concurrent_jobs renamed to destination_user_concurrent_jobs in job_conf.xml
                if type in ('destination_user_concurrent_jobs', 'concurrent_jobs', 'destination_total_concurrent_jobs'):
                    id = limit.get('tag', None) or limit.get('id')
                    if type == 'destination_total_concurrent_jobs':
                        self.limits.destination_total_concurrent_jobs[id] = int(limit.text)
                    else:
                        self.limits.destination_user_concurrent_jobs[id] = int(limit.text)
                elif type == 'total_walltime':
                    self.limits.total_walltime["window"] = (
                        int(limit.get('window')) or 30
                    )
                    self.limits.total_walltime["raw"] = (
                        types.get(type, str)(limit.text)
                    )
                elif limit.text:
                    self.limits.__dict__[type] = types.get(type, str)(limit.text)

        if self.limits.walltime is not None:
            h, m, s = [int(v) for v in self.limits.walltime.split(':')]
            self.limits.walltime_delta = datetime.timedelta(0, s, 0, 0, m, h)

        if "raw" in self.limits.total_walltime:
            h, m, s = [int(v) for v in
                       self.limits.total_walltime["raw"].split(':')]
            self.limits.total_walltime["delta"] = datetime.timedelta(
                0, s, 0, 0, m, h
            )

        log.debug('Done loading job configuration')

    def _parse_handler(self, handler_id, handler_element):
        for plugin in handler_element.findall('plugin'):
            if handler_id not in self.handler_runner_plugins:
                self.handler_runner_plugins[handler_id] = []
            self.handler_runner_plugins[handler_id].append(plugin.get('id'))

    def __set_default_job_conf(self):
        # Run jobs locally
        self.runner_plugins = [dict(id='local', load='local', workers=DEFAULT_LOCAL_WORKERS)]
        # Load tasks if configured
        if self.app.config.use_tasked_jobs:
            self.runner_plugins.append(dict(id='tasks', load='tasks', workers=DEFAULT_LOCAL_WORKERS))
        # Set the handlers
        self._init_handler_assignment_methods()
        if not self.handler_assignment_methods_configured:
            self._set_default_handler_assignment_methods()
        else:
            self.app.application_stack.init_job_handling(self)
        # Set the destination
        self.default_destination_id = 'local'
        self.destinations['local'] = [JobDestination(id='local', runner='local')]
        log.debug('Done loading job configuration')

    def get_tool_resource_xml(self, tool_id, tool_type):
        """ Given a tool id, return XML elements describing parameters to
        insert into job resources.

        :tool id: A tool ID (a string)
        :tool type: A tool type (a string)

        :returns: List of parameter elements.
        """
        if tool_id and tool_type in ('default', 'manage_data'):
            # TODO: Only works with exact matches, should handle different kinds of ids
            # the way destination lookup does.
            resource_group = None
            if tool_id in self.tools:
                resource_group = self.tools[tool_id][0].get_resource_group()
            resource_group = resource_group or self.default_resource_group
            if resource_group and resource_group in self.resource_groups:
                fields_names = self.resource_groups[resource_group]
                fields = [self.resource_parameters[n] for n in fields_names]
                if fields:
                    conditional_element = ElementTree.fromstring(self.JOB_RESOURCE_CONDITIONAL_XML)
                    when_yes_elem = conditional_element.findall('when')[1]
                    for parameter in fields:
                        when_yes_elem.append(parameter)
                    return conditional_element

    def __parse_resource_parameters(self):
        self.resource_parameters = util.parse_resource_parameters(self.app.config.job_resource_params_file)

    def __get_params(self, parent):
        """Parses any child <param> tags in to a dictionary suitable for persistence.

        :param parent: Parent element in which to find child <param> tags.
        :type parent: ``xml.etree.ElementTree.Element``

        :returns: dict
        """
        rval = {}
        for param in parent.findall('param'):
            key = param.get('id')
            if key in ["container", "container_override"]:
                from galaxy.tools.deps import requirements
                containers = map(requirements.container_from_element, param.findall('container'))
                param_value = list(map(lambda c: c.to_dict(), containers))
            else:
                param_value = param.text

            if 'from_environ' in param.attrib:
                environ_var = param.attrib['from_environ']
                param_value = os.environ.get(environ_var, param_value)
            elif 'from_config' in param.attrib:
                config_val = param.attrib['from_config']
                param_value = self.app.config.config_dict.get(config_val, param_value)

            rval[key] = param_value
        return rval

    def __get_envs(self, parent):
        """Parses any child <env> tags in to a dictionary suitable for persistence.

        :param parent: Parent element in which to find child <env> tags.
        :type parent: ``xml.etree.ElementTree.Element``

        :returns: dict
        """
        rval = []
        for param in parent.findall('env'):
            rval.append(dict(
                name=param.get('id'),
                file=param.get('file'),
                execute=param.get('exec'),
                value=param.text,
                raw=util.asbool(param.get('raw', 'false'))
            ))
        return rval

    def __get_resubmits(self, parent):
        """Parses any child <resubmit> tags in to a dictionary suitable for persistence.

        :param parent: Parent element in which to find child <resubmit> tags.
        :type parent: ``xml.etree.ElementTree.Element``

        :returns: dict
        """
        rval = []
        for resubmit in parent.findall('resubmit'):
            rval.append(dict(
                condition=resubmit.get('condition'),
                destination=resubmit.get('destination'),
                handler=resubmit.get('handler'),
                delay=resubmit.get('delay'),
            ))
        return rval

    def __is_enabled(self, params):
        """Check for an enabled parameter - pop it out - and return as boolean."""
        enabled = True
        if "enabled" in params:
            raw_enabled = params.pop("enabled")
            enabled = util.asbool(raw_enabled)

        return enabled

    @property
    def default_job_tool_configuration(self):
        """
        The default JobToolConfiguration, used if a tool does not have an
        explicit defintion in the configuration.  It consists of a reference to
        the default handler and default destination.

        :returns: JobToolConfiguration -- a representation of a <tool> element that uses the default handler and destination
        """
        return JobToolConfiguration(id='_default_', handler=self.default_handler_id, destination=self.default_destination_id)

    # Called upon instantiation of a Tool object
    def get_job_tool_configurations(self, ids):
        """
        Get all configured JobToolConfigurations for a tool ID, or, if given
        a list of IDs, the JobToolConfigurations for the first id in ``ids``
        matching a tool definition.

        .. note:: You should not mix tool shed tool IDs, versionless tool shed
             IDs, and tool config tool IDs that refer to the same tool.

        :param ids: Tool ID or IDs to fetch the JobToolConfiguration of.
        :type ids: list or str.
        :returns: list -- JobToolConfiguration Bunches representing <tool> elements matching the specified ID(s).

        Example tool ID strings include:

        * Full tool shed id: ``toolshed.example.org/repos/nate/filter_tool_repo/filter_tool/1.0.0``
        * Tool shed id less version: ``toolshed.example.org/repos/nate/filter_tool_repo/filter_tool``
        * Tool config tool id: ``filter_tool``
        """
        rval = []
        # listify if ids is a single (string) id
        ids = util.listify(ids)
        for id in ids:
            if id in self.tools:
                # If a tool has definitions that include job params but not a
                # definition for jobs without params, include the default
                # config
                for job_tool_configuration in self.tools[id]:
                    if not job_tool_configuration.params:
                        break
                else:
                    rval.append(self.default_job_tool_configuration)
                rval.extend(self.tools[id])
                break
        else:
            rval.append(self.default_job_tool_configuration)
        return rval

    def get_destination(self, id_or_tag):
        """Given a destination ID or tag, return the JobDestination matching the provided ID or tag

        :param id_or_tag: A destination ID or tag.
        :type id_or_tag: str

        :returns: JobDestination -- A valid destination

        Destinations are deepcopied as they are expected to be passed in to job
        runners, which will modify them for persisting params set at runtime.
        """
        if id_or_tag is None:
            id_or_tag = self.default_destination_id
        return copy.deepcopy(self._get_single_item(self.destinations[id_or_tag]))

    def get_destinations(self, id_or_tag):
        """Given a destination ID or tag, return all JobDestinations matching the provided ID or tag

        :param id_or_tag: A destination ID or tag.
        :type id_or_tag: str

        :returns: list or tuple of JobDestinations

        Destinations are not deepcopied, so they should not be passed to
        anything which might modify them.
        """
        return self.destinations.get(id_or_tag, None)

    def get_job_runner_plugins(self, handler_id):
        """Load all configured job runner plugins

        :returns: list of job runner plugins
        """
        rval = {}
        if handler_id in self.handler_runner_plugins:
            plugins_to_load = [rp for rp in self.runner_plugins if rp['id'] in self.handler_runner_plugins[handler_id]]
            log.info("Handler '%s' will load specified runner plugins: %s", handler_id, ', '.join([rp['id'] for rp in plugins_to_load]))
        else:
            plugins_to_load = self.runner_plugins
            log.info("Handler '%s' will load all configured runner plugins", handler_id)
        for runner in plugins_to_load:
            class_names = []
            module = None
            id = runner['id']
            load = runner['load']
            if ':' in load:
                # Name to load was specified as '<module>:<class>'
                module_name, class_name = load.rsplit(':', 1)
                class_names = [class_name]
                module = __import__(module_name)
            else:
                # Name to load was specified as '<module>'
                if '.' not in load:
                    # For legacy reasons, try from galaxy.jobs.runners first if there's no '.' in the name
                    module_name = 'galaxy.jobs.runners.' + load
                    try:
                        module = __import__(module_name)
                    except ImportError:
                        # No such module, we'll retry without prepending galaxy.jobs.runners.
                        # All other exceptions (e.g. something wrong with the module code) will raise
                        pass
                if module is None:
                    # If the name included a '.' or loading from the static runners path failed, try the original name
                    module = __import__(load)
                    module_name = load
            if module is None:
                # Module couldn't be loaded, error should have already been displayed
                continue
            for comp in module_name.split(".")[1:]:
                module = getattr(module, comp)
            if not class_names:
                # If there's not a ':', we check <module>.__all__ for class names
                try:
                    assert module.__all__
                    class_names = module.__all__
                except AssertionError:
                    log.error('Runner "%s" does not contain a list of exported classes in __all__' % load)
                    continue
            for class_name in class_names:
                runner_class = getattr(module, class_name)
                try:
                    assert issubclass(runner_class, BaseJobRunner)
                except TypeError:
                    log.warning("A non-class name was found in __all__, ignoring: %s" % id)
                    continue
                except AssertionError:
                    log.warning("Job runner classes must be subclassed from BaseJobRunner, %s has bases: %s" % (id, runner_class.__bases__))
                    continue
                try:
                    rval[id] = runner_class(self.app, runner['workers'], **runner.get('kwds', {}))
                except TypeError:
                    log.exception("Job runner '%s:%s' has not been converted to a new-style runner or encountered TypeError on load",
                                  module_name, class_name)
                    rval[id] = runner_class(self.app)
                log.debug("Loaded job runner '%s:%s' as '%s'" % (module_name, class_name, id))
        return rval

    def is_id(self, collection):
        """Given a collection of handlers or destinations, indicate whether the collection represents a tag or a real ID

        :param collection: A representation of a destination or handler
        :type collection: tuple or list

        :returns: bool
        """
        return type(collection) == tuple

    def is_tag(self, collection):
        """Given a collection of handlers or destinations, indicate whether the collection represents a tag or a real ID

        :param collection: A representation of a destination or handler
        :type collection: tuple or list

        :returns: bool
        """
        return type(collection) == list

    def convert_legacy_destinations(self, job_runners):
        """Converts legacy (from a URL) destinations to contain the appropriate runner params defined in the URL.

        :param job_runners: All loaded job runner plugins.
        :type job_runners: list of job runner plugins
        """
        for id, destination in [(id, destinations[0]) for id, destinations in self.destinations.items() if self.is_id(destinations)]:
            # Only need to deal with real destinations, not members of tags
            if destination.legacy and not destination.converted:
                if destination.runner in job_runners:
                    destination.params = job_runners[destination.runner].url_to_destination(destination.url).params
                    destination.converted = True
                    if destination.params:
                        log.debug("Legacy destination with id '%s', url '%s' converted, got params:" % (id, destination.url))
                        for k, v in destination.params.items():
                            log.debug("    %s: %s" % (k, v))
                    else:
                        log.debug("Legacy destination with id '%s', url '%s' converted, got params:" % (id, destination.url))
                else:
                    log.warning("Legacy destination with id '%s' could not be converted: Unknown runner plugin: %s" % (id, destination.runner))


class HasResourceParameters(object):

    def get_resource_parameters(self, job=None):
        # Find the dymically inserted resource parameters and give them
        # to rule.

        if job is None:
            job = self.get_job()

        app = self.app
        param_values = job.get_param_values(app, ignore_errors=True)
        resource_params = {}
        try:
            resource_params_raw = param_values["__job_resource"]
            if resource_params_raw["__job_resource__select"].lower() in ["1", "yes", "true"]:
                for key, value in resource_params_raw.items():
                    resource_params[key] = value
        except KeyError:
            pass

        return resource_params


class JobWrapper(HasResourceParameters):
    """
    Wraps a 'model.Job' with convenience methods for running processes and
    state management.
    """

    def __init__(self, job, queue, use_persisted_destination=False):
        self.job_id = job.id
        self.session_id = job.session_id
        self.user_id = job.user_id
        self.tool = queue.app.toolbox.get_tool(job.tool_id, job.tool_version, exact=True)
        self.queue = queue
        self.app = queue.app
        self.sa_session = self.app.model.context
        self.extra_filenames = []
        self.command_line = None
        self.dependencies = []
        self._dependency_shell_commands = None
        # Tool versioning variables
        self.write_version_cmd = None
        self.version_string = ""
        self.__galaxy_lib_dir = None
        # If the job has an object_store_id ensure working directory is setup, otherwise
        # wait for that to be assigned before configuring it. Either way the working
        # directory does not to be configured on this object before prepare() is called.
        if job.object_store_id:
            self._setup_working_directory(job=job)
        # the path rewriter needs destination params, so it cannot be set up until after the destination has been
        # resolved
        self._dataset_path_rewriter = None
        self.output_paths = None
        self.output_hdas_and_paths = None
        self.tool_provided_job_metadata = None
        # Wrapper holding the info required to restore and clean up from files used for setting metadata externally
        self.external_output_metadata = get_metadata_compute_strategy(self.app, job.id)
        self.job_runner_mapper = JobRunnerMapper(self, queue.dispatcher.url_to_destination, self.app.job_config)
        self.params = None
        if job.params:
            self.params = loads(job.params)
        if use_persisted_destination:
            self.job_runner_mapper.cached_job_destination = JobDestination(from_job=job)

        self.__commands_in_new_shell = True
        self.__user_system_pwent = None
        self.__galaxy_system_pwent = None
        self.__working_directory = None

    @property
    def _job_dataset_path_rewriter(self):
        if self._dataset_path_rewriter is None:
            outputs_to_working_directory = util.asbool(self.get_destination_configuration("outputs_to_working_directory", False))
            if outputs_to_working_directory:
                self._dataset_path_rewriter = OutputsToWorkingDirectoryPathRewriter(self.working_directory)
            else:
                self._dataset_path_rewriter = NullDatasetPathRewriter()
        return self._dataset_path_rewriter

    @property
    def dataset_path_rewriter(self):
        return self._job_dataset_path_rewriter

    @property
    def dependency_shell_commands(self):
        """Shell fragment to inject dependencies."""
        if self._dependency_shell_commands is None:
            self._dependency_shell_commands = self.tool.build_dependency_shell_commands(
                job_directory=self.working_directory
            )
        return self._dependency_shell_commands

    @property
    def cleanup_job(self):
        """ Remove the job after it is complete, should return "always", "onsuccess", or "never".
        """
        return self.get_destination_configuration("cleanup_job", DEFAULT_CLEANUP_JOB)

    @property
    def requires_containerization(self):
        return util.asbool(self.get_destination_configuration("require_container", "False"))

    def can_split(self):
        # Should the job handler split this job up?
        return self.app.config.use_tasked_jobs and self.tool.parallelism

    def get_job_runner_url(self):
        log.warning('(%s) Job runner URLs are deprecated, use destinations instead.' % self.job_id)
        return self.job_destination.url

    def get_parallelism(self):
        return self.tool.parallelism

    @property
    def shell(self):
        return self.job_destination.shell or getattr(self.app.config, 'default_job_shell', DEFAULT_JOB_SHELL)

    def disable_commands_in_new_shell(self):
        """Provide an extension point to disable this isolation,
        Pulsar builds its own job script so this is not needed for
        remote jobs."""
        self.__commands_in_new_shell = False

    @property
    def strict_shell(self):
        return self.tool.strict_shell

    @property
    def commands_in_new_shell(self):
        return self.__commands_in_new_shell

    @property
    def galaxy_lib_dir(self):
        if self.__galaxy_lib_dir is None:
            self.__galaxy_lib_dir = os.path.abspath("lib")  # cwd = galaxy root
        return self.__galaxy_lib_dir

    @property
    def galaxy_virtual_env(self):
        return os.environ.get('VIRTUAL_ENV', None)

    # legacy naming
    get_job_runner = get_job_runner_url

    @property
    def job_destination(self):
        """Return the JobDestination that this job will use to run.  This will
        either be a configured destination, a randomly selected destination if
        the configured destination was a tag, or a dynamically generated
        destination from the dynamic runner.

        Calling this method for the first time causes the dynamic runner to do
        its calculation, if any.

        :returns: ``JobDestination``
        """
        return self.job_runner_mapper.get_job_destination(self.params)

    def get_job(self):
        return self.sa_session.query(model.Job).get(self.job_id)

    def get_id_tag(self):
        # For compatibility with drmaa, which uses job_id right now, and TaskWrapper
        return self.get_job().get_id_tag()

    def get_param_dict(self, _job=None):
        """
        Restore the dictionary of parameters from the database.
        """
        job = _job or self.get_job()
        param_dict = dict([(p.name, p.value) for p in job.parameters])
        param_dict = self.tool.params_from_strings(param_dict, self.app)
        return param_dict

    def get_version_string_path(self):
        return os.path.abspath(os.path.join(self.working_directory, COMMAND_VERSION_FILENAME))

    # TODO: Remove in Galaxy 20.XX, for running jobs at GX upgrade
    def get_version_string_path_legacy(self):
        return os.path.abspath(os.path.join(self.app.config.new_file_path, "GALAXY_VERSION_STRING_%s" % self.job_id))

    def __prepare_upload_paramfile(self, tool_evaluator):
        """Special case paramfile handling for the upload tool. Moves the paramfile to the working directory
        """
        new = os.path.join(self.working_directory, 'upload_params.json')
        try:
            shutil.move(tool_evaluator.param_dict['paramfile'], new)
        except (OSError, IOError) as exc:
            # It won't exist at the old path if setup was interrupted and tried again later
            if exc.errno != errno.ENOENT or not os.path.exists(new):
                raise
        tool_evaluator.param_dict['paramfile'] = new

    def prepare(self, compute_environment=None):
        """
        Prepare the job to run by creating the working directory and the
        config files.
        """
        self.sa_session.expunge_all()  # this prevents the metadata reverting that has been seen in conjunction with the PBS job runner

        if not os.path.exists(self.working_directory):
            os.mkdir(self.working_directory)

        job = self._load_job()

        def get_special():
            special = self.sa_session.query(model.JobExportHistoryArchive).filter_by(job=job).first()
            if not special:
                special = self.sa_session.query(model.GenomeIndexToolData).filter_by(job=job).first()
            return special

        tool_evaluator = self._get_tool_evaluator(job)
        compute_environment = compute_environment or self.default_compute_environment(job)
        tool_evaluator.set_compute_environment(compute_environment, get_special=get_special)

        self.sa_session.flush()

        # TODO: The upload tool actions that create the paramfile can probably be turned in to a configfile to remove this special casing
        if job.tool_id == 'upload1':
            self.__prepare_upload_paramfile(tool_evaluator)

        self.command_line, self.extra_filenames, self.environment_variables = tool_evaluator.build()
        # Ensure galaxy_lib_dir is set in case there are any later chdirs
        self.galaxy_lib_dir
        if self.tool.requires_galaxy_python_environment:
            # These tools (upload, metadata, data_source) may need access to the datatypes registry.
            self.app.datatypes_registry.to_xml_file(os.path.join(self.working_directory, 'registry.xml'))
        # We need command_line persisted to the db in order for Galaxy to re-queue the job
        # if the server was stopped and restarted before the job finished
        job.command_line = unicodify(self.command_line)
        job.dependencies = self.tool.dependencies
        self.sa_session.add(job)
        self.sa_session.flush()
        # Return list of all extra files
        self.param_dict = tool_evaluator.param_dict
        version_string_cmd_raw = self.tool.version_string_cmd
        if version_string_cmd_raw:
            version_command_template = string.Template(version_string_cmd_raw)
            version_string_cmd = version_command_template.safe_substitute({"__tool_directory__": compute_environment.tool_directory()})
            self.write_version_cmd = "%s > %s 2>&1" % (version_string_cmd, compute_environment.version_path())
        else:
            self.write_version_cmd = None
        return self.extra_filenames

    def _setup_working_directory(self, job=None):
        if job is None:
            job = self.get_job()
        try:
            working_directory = self._create_working_directory(job)
            self.__working_directory = working_directory
            # The tool execution is given a working directory beneath the
            # "job" working directory.
            safe_makedirs(self.tool_working_directory)
            log.debug('(%s) Working directory for job is: %s',
                      self.job_id, self.working_directory)
        except ObjectInvalid:
            raise Exception('(%s) Unable to create job working directory',
                            job.id)

    @property
    def working_directory(self):
        if self.__working_directory is None:
            job = self.get_job()

            # object_store_id needs to be set before get_filename can be called, this
            # will also create the directory on the worker.
            # It is possible these next two lines are not needed - if a job a cannot be recovered
            # before enqueue is called (seems likely) - this shouldn't be needed.
            if job.object_store_id:
                self._set_object_store_ids(job)

            self.__working_directory = self.app.object_store.get_filename(
                job, base_dir='job_work', dir_only=True, obj_dir=True)
        return self.__working_directory

    @property
    def tool_working_directory(self):
        return os.path.join(self.working_directory, "working")

    def _create_working_directory(self, job):
        self.object_store.create(
            job, base_dir='job_work', dir_only=True, obj_dir=True)
        working_directory = self.object_store.get_filename(
            job, base_dir='job_work', dir_only=True, obj_dir=True)
        return working_directory

    def clear_working_directory(self):
        job = self.get_job()
        if not os.path.exists(self.working_directory):
            log.warning('(%s): Working directory clear requested but %s does '
                        'not exist',
                        self.job_id,
                        self.working_directory)
            return

        self.object_store.create(
            job, base_dir='job_work', dir_only=True, obj_dir=True,
            extra_dir='_cleared_contents', extra_dir_at_root=True)
        base = self.object_store.get_filename(
            job, base_dir='job_work', dir_only=True, obj_dir=True,
            extra_dir='_cleared_contents', extra_dir_at_root=True)
        date_str = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        arc_dir = os.path.join(base, date_str)
        shutil.move(self.working_directory, arc_dir)
        self._setup_working_directory(job=job)
        log.debug('(%s) Previous working directory moved to %s',
                  self.job_id, arc_dir)

    def default_compute_environment(self, job=None):
        if not job:
            job = self.get_job()
        return SharedComputeEnvironment(self, job)

    def _load_job(self):
        # Load job from database and verify it has user or session.
        # Restore parameters from the database
        job = self.get_job()
        if job.user is None and job.galaxy_session is None:
            raise Exception('Job %s has no user and no session.' % job.id)
        return job

    def _get_tool_evaluator(self, job):
        # Hacky way to avoid cirular import for now.
        # Placing ToolEvaluator in either jobs or tools
        # result in ciruclar dependency.
        from galaxy.tools.evaluation import ToolEvaluator

        tool_evaluator = ToolEvaluator(
            app=self.app,
            job=job,
            tool=self.tool,
            local_working_directory=self.working_directory,
        )
        return tool_evaluator

    def _fix_output_permissions(self):
        for path in [dp.real_path for dp in self.get_mutable_output_fnames()]:
            if os.path.exists(path):
                util.umask_fix_perms(path, self.app.config.umask, 0o666, self.app.config.gid)

    def fail(self, message, exception=False, tool_stdout="", tool_stderr="", exit_code=None, job_stdout=None, job_stderr=None):
        """
        Indicate job failure by setting state and message on all output
        datasets.
        """
        job = self.get_job()
        self.sa_session.refresh(job)
        # if the job was deleted, don't fail it
        if not job.state == job.states.DELETED:
            # Check if the failure is due to an exception
            if exception:
                # Save the traceback immediately in case we generate another
                # below
                job.traceback = traceback.format_exc()
                # Get the exception and let the tool attempt to generate
                # a better message
                etype, evalue, tb = sys.exc_info()

            outputs_to_working_directory = util.asbool(self.get_destination_configuration("outputs_to_working_directory", False))
            if outputs_to_working_directory and not self.__link_file_check():
                for dataset_path in self.get_output_fnames():
                    try:
                        shutil.move(dataset_path.false_path, dataset_path.real_path)
                        log.debug("fail(): Moved %s to %s" % (dataset_path.false_path, dataset_path.real_path))
                    except (IOError, OSError) as e:
                        log.error("fail(): Missing output file in working directory: %s" % e)
            for dataset_assoc in job.output_datasets + job.output_library_datasets:
                dataset = dataset_assoc.dataset
                self.sa_session.refresh(dataset)
                dataset.state = dataset.states.ERROR
                dataset.blurb = 'tool error'
                dataset.info = message
                dataset.set_size()
                dataset.dataset.set_total_size()
                dataset.mark_unhidden()
                if dataset.ext == 'auto':
                    dataset.extension = 'data'
                self.__update_output(job, dataset)
                # Pause any dependent jobs (and those jobs' outputs)
                for dep_job_assoc in dataset.dependent_jobs:
                    self.pause(dep_job_assoc.job, "Execution of this dataset's job is paused because its input datasets are in an error state.")
                self.sa_session.add(dataset)
                self.sa_session.flush()
            job.set_final_state(job.states.ERROR)
            job.command_line = unicodify(self.command_line)
            job.info = message
            # TODO: Put setting the stdout, stderr, and exit code in one place
            # (not duplicated with the finish method).
            job.set_streams(tool_stdout, tool_stderr, job_stdout=job_stdout, job_stderr=job_stderr)
            # Let the exit code be Null if one is not provided:
            if (exit_code is not None):
                job.exit_code = exit_code

            self.sa_session.add(job)
            self.sa_session.flush()
        else:
            for dataset_assoc in job.output_datasets:
                dataset = dataset_assoc.dataset
                # Any reason for clean_only here? We should probably be more consistent and transfer
                # the partial files to the object store regardless of whether job.state == DELETED
                self.__update_output(job, dataset, clean_only=True)

        self._fix_output_permissions()
        self._report_error()
        # Perform email action even on failure.
        for pja in [pjaa.post_job_action for pjaa in job.post_job_actions if pjaa.post_job_action.action_type == "EmailAction"]:
            ActionBox.execute(self.app, self.sa_session, pja, job)
        # If the job was deleted, call tool specific fail actions (used for e.g. external metadata) and clean up
        if self.tool:
            self.tool.job_failed(self, message, exception)
        cleanup_job = self.cleanup_job
        delete_files = cleanup_job == 'always' or (cleanup_job == 'onsuccess' and job.state == job.states.DELETED)
        self.cleanup(delete_files=delete_files)

    def pause(self, job=None, message=None):
        if job is None:
            job = self.get_job()
        if message is None:
            message = "Execution of this dataset's job is paused"
        if job.state == job.states.NEW:
            for dataset_assoc in job.output_datasets + job.output_library_datasets:
                dataset_assoc.dataset.dataset.state = dataset_assoc.dataset.dataset.states.PAUSED
                dataset_assoc.dataset.info = message
                self.sa_session.add(dataset_assoc.dataset)
            log.debug("Pausing Job '%d', %s", job.id, message)
            job.set_state(job.states.PAUSED)
            self.sa_session.add(job)

    def is_ready_for_resubmission(self, job=None):
        if job is None:
            job = self.get_job()

        destination_params = job.destination_params
        if "__resubmit_delay_seconds" in destination_params:
            delay = float(destination_params["__resubmit_delay_seconds"])
            if job.seconds_since_updated < delay:
                return False

        return True

    def mark_as_resubmitted(self, info=None):
        job = self.get_job()
        self.sa_session.refresh(job)
        if info is not None:
            job.info = info
        job.set_state(model.Job.states.RESUBMITTED)
        self.sa_session.add(job)
        self.sa_session.flush()

    def change_state(self, state, info=False, flush=True, job=None):
        job_supplied = job is not None
        if not job_supplied:
            job = self.get_job()
            self.sa_session.refresh(job)
        # Else:
        # If this is a new job (e.g. initially queued) - we are in the same
        # thread and no other threads are working on the job yet - so don't refresh.

        if job.state in model.Job.terminal_states:
            log.warning("(%s) Ignoring state change from '%s' to '%s' for job "
                        "that is already terminal", job.id, job.state, state)
            return
        for dataset_assoc in job.output_datasets + job.output_library_datasets:
            dataset = dataset_assoc.dataset
            if not job_supplied:
                self.sa_session.refresh(dataset)
            state_changed = dataset.raw_set_dataset_state(state)
            if state_changed:
                # Arguably a hack to get state changes to appear in the history panel because
                # the history panel polls on hda.update_time and ignores hda.dataset.update_time.
                # For those less pragmatic needing a more theoretically sound reason for the update,
                # perhaps arguments can be made that the entity that is the HDA
                # really should be described as updated since its effective state did change and its
                # RESTful representation in the API does change as a result of the above dataset update.
                dataset.update()
            if info:
                dataset.info = info
            self.sa_session.add(dataset)
        if info:
            job.info = info
        job.set_state(state)
        self.sa_session.add(job)
        if flush:
            self.sa_session.flush()

    def get_state(self):
        job = self.get_job()
        self.sa_session.refresh(job)
        return job.state

    def set_runner(self, runner_url, external_id):
        log.warning('set_runner() is deprecated, use set_job_destination()')
        self.set_job_destination(self.job_destination, external_id)

    def set_job_destination(self, job_destination, external_id=None, flush=True, job=None):
        """
        Persist job destination params in the database for recovery.

        self.job_destination is not used because a runner may choose to rewrite
        parts of the destination (e.g. the params).
        """
        if job is None:
            job = self.get_job()
        log.debug('(%s) Persisting job destination (destination id: %s)' % (job.id, job_destination.id))
        job.destination_id = job_destination.id
        job.destination_params = job_destination.params
        job.job_runner_name = job_destination.runner
        job.job_runner_external_id = external_id
        self.sa_session.add(job)
        if flush:
            self.sa_session.flush()

    @property
    def home_target(self):
        home_target = self.tool.home_target
        return home_target

    @property
    def tmp_target(self):
        return self.tool.tmp_target

    def get_destination_configuration(self, key, default=None):
        """ Get a destination parameter that can be defaulted back
        in app.config if it needs to be applied globally.
        """
        dest_params = self.job_destination.params
        return self.get_job().get_destination_configuration(
            dest_params, self.app.config, key, default
        )

    def enqueue(self):
        job = self.get_job()
        # Change to queued state before handing to worker thread so the runner won't pick it up again
        self.change_state(model.Job.states.QUEUED, flush=False, job=job)
        # Persist the destination so that the job will be included in counts if using concurrency limits
        self.set_job_destination(self.job_destination, None, flush=False, job=job)
        # Set object store after job destination so can leverage parameters...
        self._set_object_store_ids(job)
        self.sa_session.flush()

    def _set_object_store_ids(self, job):
        if job.object_store_id:
            # We aren't setting this during job creation anymore, but some existing
            # jobs may have this set. Skip this following code if that is the case.
            return

        object_store_populator = ObjectStorePopulator(self.app)
        object_store_id = self.get_destination_configuration("object_store_id", None)
        if object_store_id:
            object_store_populator.object_store_id = object_store_id

        # Ideally we would do this without loading the actual job association
        # objects but change_state isn't yet optimized to do that so we need to
        # do that anyway. In the future though - this should be done with a
        # custom query that just loads Dataset.ids, passes them through object
        # store code, and sets object_store_id on those ids with a multi-update
        # afterward. State below needs to happen the same way.
        for dataset_assoc in job.output_datasets + job.output_library_datasets:
            dataset = dataset_assoc.dataset
            object_store_populator.set_object_store_id(dataset)

        job.object_store_id = object_store_populator.object_store_id
        self._setup_working_directory(job=job)

    def finish(
        self,
        tool_stdout,
        tool_stderr,
        tool_exit_code=None,
        job_stdout=None,
        job_stderr=None,
        check_output_detected_state=None,
        remote_metadata_directory=None,
    ):
        """
        Called to indicate that the associated command has been run. Updates
        the output datasets based on stderr and stdout from the command, and
        the contents of the output files.
        """
        finish_timer = util.ExecutionTimer()

        # default post job setup
        self.sa_session.expunge_all()
        job = self.get_job()

        def fail():
            return self.fail(job.info, tool_stdout=tool_stdout, tool_stderr=tool_stderr, exit_code=tool_exit_code, job_stdout=job_stdout, job_stderr=job_stderr)

        # TODO: After failing here, consider returning from the function.
        try:
            self.reclaim_ownership()
        except Exception:
            log.exception('(%s) Failed to change ownership of %s, failing' % (job.id, self.working_directory))
            return fail()

        # if the job was deleted, don't finish it
        if job.state == job.states.DELETED or job.state == job.states.ERROR:
            # SM: Note that, at this point, the exit code must be saved in case
            # there was an error. Errors caught here could mean that the job
            # was deleted by an administrator (based on old comments), but it
            # could also mean that a job was broken up into tasks and one of
            # the tasks failed. So include the stderr, stdout, and exit code:
            return fail()

        # We collect the stderr from tools that write their stderr to galaxy.json
        tool_provided_metadata = self.get_tool_provided_job_metadata()

        # Check the tool's stdout, stderr, and exit code for errors, but only
        # if the job has not already been marked as having an error.
        # The job's stdout and stderr will be set accordingly.

        # We set final_job_state to use for dataset management, but *don't* set
        # job.state until after dataset discovery to prevent history issues
        if check_output_detected_state is None:
            check_output_detected_state = self.check_tool_output(tool_stdout, tool_stderr, tool_exit_code=tool_exit_code, job=job, job_stdout=job_stdout, job_stderr=job_stderr)

        if check_output_detected_state == DETECTED_JOB_STATE.OK and not tool_provided_metadata.has_failed_outputs():
            final_job_state = job.states.OK
        else:
            final_job_state = job.states.ERROR

        if self.tool.version_string_cmd:
            version_filename = self.get_version_string_path()
            # TODO: Remove in Galaxy 20.XX, for running jobs at GX upgrade
            if not os.path.exists(version_filename):
                version_filename = self.get_version_string_path_legacy()
            if os.path.exists(version_filename):
                self.version_string = open(version_filename).read()
                os.unlink(version_filename)

        outputs_to_working_directory = util.asbool(self.get_destination_configuration("outputs_to_working_directory", False))
        if outputs_to_working_directory and not self.__link_file_check():
            for dataset_path in self.get_output_fnames():
                try:
                    shutil.move(dataset_path.false_path, dataset_path.real_path)
                    log.debug("finish(): Moved %s to %s" % (dataset_path.false_path, dataset_path.real_path))
                except (IOError, OSError):
                    # this can happen if Galaxy is restarted during the job's
                    # finish method - the false_path file has already moved,
                    # and when the job is recovered, it won't be found.
                    if os.path.exists(dataset_path.real_path) and os.stat(dataset_path.real_path).st_size > 0:
                        log.warning("finish(): %s not found, but %s is not empty, so it will be used instead"
                                    % (dataset_path.false_path, dataset_path.real_path))
                    else:
                        # Prior to fail we need to set job.state
                        job.set_state(final_job_state)
                        return self.fail("Job %s's output dataset(s) could not be read" % job.id)

        job_context = ExpressionContext(dict(stdout=job.stdout, stderr=job.stderr))
        implicit_collection_jobs = job.implicit_collection_jobs_association
        for dataset_assoc in job.output_datasets + job.output_library_datasets:
            context = self.get_dataset_finish_context(job_context, dataset_assoc)
            # should this also be checking library associations? - can a library item be added from a history before the job has ended? -
            # lets not allow this to occur
            # need to update all associated output hdas, i.e. history was shared with job running
            for dataset in dataset_assoc.dataset.dataset.history_associations + dataset_assoc.dataset.dataset.library_associations:
                purged = dataset.dataset.purged
                if not purged and dataset.dataset.external_filename is None:
                    trynum = 0
                    while trynum < self.app.config.retry_job_output_collection:
                        try:
                            # Attempt to short circuit NFS attribute caching
                            os.stat(dataset.dataset.file_name)
                            os.chown(dataset.dataset.file_name, os.getuid(), -1)
                            trynum = self.app.config.retry_job_output_collection
                        except (OSError, ObjectNotFound) as e:
                            trynum += 1
                            log.warning('Error accessing dataset with ID %i, will retry: %s', dataset.dataset.id, e)
                            time.sleep(2)
                if getattr(dataset, "hidden_beneath_collection_instance", None):
                    dataset.visible = False
                dataset.blurb = 'done'
                dataset.peek = 'no peek'
                dataset.info = (dataset.info or '')
                if context['stdout'].strip():
                    # Ensure white space between entries
                    dataset.info = dataset.info.rstrip() + "\n" + context['stdout'].strip()
                if context['stderr'].strip():
                    # Ensure white space between entries
                    dataset.info = dataset.info.rstrip() + "\n" + context['stderr'].strip()
                dataset.tool_version = self.version_string
                dataset.set_size()
                if 'uuid' in context:
                    dataset.dataset.uuid = context['uuid']
                self.__update_output(job, dataset)
                if not purged:
                    self._collect_extra_files(dataset.dataset, self.working_directory)
                # Handle composite datatypes of auto_primary_file type
                if dataset.datatype.composite_type == 'auto_primary_file' and not dataset.has_data():
                    try:
                        with NamedTemporaryFile() as temp_fh:
                            temp_fh.write(dataset.datatype.generate_primary_file(dataset))
                            temp_fh.flush()
                            self.object_store.update_from_file(dataset.dataset, file_name=temp_fh.name, create=True)
                            dataset.set_size()
                    except Exception as e:
                        log.warning('Unable to generate primary composite file automatically for %s: %s', dataset.dataset.id, e)
                if job.states.ERROR == final_job_state:
                    dataset.blurb = "error"
                    if not implicit_collection_jobs:
                        # Only unhide dataset outputs that are not part of a implicit collection
                        dataset.mark_unhidden()
                elif not purged:
                    # If the tool was expected to set the extension, attempt to retrieve it
                    if dataset.ext == 'auto':
                        dataset.extension = context.get('ext', 'data')
                        dataset.init_meta(copy_from=dataset)
                    # if a dataset was copied, it won't appear in our dictionary:
                    # either use the metadata from originating output dataset, or call set_meta on the copies
                    # it would be quicker to just copy the metadata from the originating output dataset,
                    # but somewhat trickier (need to recurse up the copied_from tree), for now we'll call set_meta()
                    retry_internally = util.asbool(self.get_destination_configuration("retry_metadata_internally", True))
                    metadata_set_successfully = self.external_output_metadata.external_metadata_set_successfully(dataset, dataset_assoc.name, self.sa_session, working_directory=self.working_directory)
                    if retry_internally and not metadata_set_successfully:
                        # If Galaxy was expected to sniff type and didn't - do so.
                        if dataset.ext == "_sniff_":
                            extension = sniff.handle_uploaded_dataset_file(dataset.dataset.file_name, self.app.datatypes_registry)
                            dataset.extension = extension

                        # call datatype.set_meta directly for the initial set_meta call during dataset creation
                        dataset.datatype.set_meta(dataset, overwrite=False)
                    elif (job.states.ERROR != final_job_state and not metadata_set_successfully):
                        dataset._state = model.Dataset.states.FAILED_METADATA
                    else:
                        self.external_output_metadata.load_metadata(dataset, dataset_assoc.name, self.sa_session, working_directory=self.working_directory, remote_metadata_directory=remote_metadata_directory)
                    line_count = context.get('line_count', None)
                    try:
                        # Certain datatype's set_peek methods contain a line_count argument
                        dataset.set_peek(line_count=line_count)
                    except TypeError:
                        # ... and others don't
                        dataset.set_peek()
                else:
                    # Handle purged datasets.
                    dataset.blurb = "empty"
                    if dataset.ext == 'auto':
                        dataset.extension = context.get('ext', 'txt')

                for context_key in TOOL_PROVIDED_JOB_METADATA_KEYS:
                    if context_key in context:
                        context_value = context[context_key]
                        setattr(dataset, context_key, context_value)

                self.sa_session.add(dataset)
            if job.states.ERROR == final_job_state:
                log.debug("(%s) setting dataset %s state to ERROR", job.id, dataset_assoc.dataset.dataset.id)
                # TODO: This is where the state is being set to error. Change it!
                dataset_assoc.dataset.dataset.state = model.Dataset.states.ERROR
                # Pause any dependent jobs (and those jobs' outputs)
                for dep_job_assoc in dataset_assoc.dataset.dependent_jobs:
                    self.pause(dep_job_assoc.job, "Execution of this dataset's job is paused because its input datasets are in an error state.")
            else:
                dataset_assoc.dataset.dataset.state = model.Dataset.states.OK
            # If any of the rest of the finish method below raises an
            # exception, the fail method will run and set the datasets to
            # ERROR.  The user will never see that the datasets are in error if
            # they were flushed as OK here, since upon doing so, the history
            # panel stops checking for updates.  So allow the
            # self.sa_session.flush() at the bottom of this method set
            # the state instead.

        for pja in job.post_job_actions:
            ActionBox.execute(self.app, self.sa_session, pja.post_job_action, job)
        # Flush all the dataset and job changes above.  Dataset state changes
        # will now be seen by the user.
        self.sa_session.flush()

        # The exit code will be null if there is no exit code to be set.
        # This is so that we don't assign an exit code, such as 0, that
        # is either incorrect or has the wrong semantics.
        if tool_exit_code is not None:
            job.exit_code = tool_exit_code
        # custom post process setup
        inp_data, out_data, out_collections = job.io_dicts()
        self.discover_outputs(job, inp_data, out_data, out_collections)
        # Certain tools require tasks to be completed after job execution
        # ( this used to be performed in the "exec_after_process" hook, but hooks are deprecated ).
        param_dict = self.get_param_dict(job)
        self.tool.exec_after_process(self.app, inp_data, out_data, param_dict, job=job)
        # Call 'exec_after_process' hook
        self.tool.call_hook('exec_after_process', self.app, inp_data=inp_data,
                            out_data=out_data, param_dict=param_dict,
                            tool=self.tool, stdout=job.stdout, stderr=job.stderr)
        job.command_line = unicodify(self.command_line)

        collected_bytes = 0
        # Once datasets are collected, set the total dataset size (includes extra files)
        for dataset_assoc in job.output_datasets:
            if not dataset_assoc.dataset.dataset.purged:
                dataset_assoc.dataset.dataset.set_total_size()
                collected_bytes += dataset_assoc.dataset.dataset.get_total_size()

        if job.user:
            job.user.adjust_total_disk_usage(collected_bytes)

        # Empirically, we need to update job.user and
        # job.workflow_invocation_step.workflow_invocation in separate
        # transactions. Best guess as to why is that the workflow_invocation
        # may or may not exist when the job is first loaded by the handler -
        # and depending on whether it is or not sqlalchemy orders the updates
        # differently and deadlocks can occur (one thread updates user and
        # waits on invocation and the other updates invocation and waits on
        # user).
        self.sa_session.flush()

        self._fix_output_permissions()

        # Finally set the job state.  This should only happen *after* all
        # dataset creation, and will allow us to eliminate force_history_refresh.
        job.set_final_state(final_job_state)
        if not job.tasks:
            # If job was composed of tasks, don't attempt to recollect statisitcs
            self._collect_metrics(job)
        self.sa_session.flush()
        log.debug('job %d ended (finish() executed in %s)' % (self.job_id, finish_timer))
        if job.state == job.states.ERROR:
            self._report_error()
        cleanup_job = self.cleanup_job
        delete_files = cleanup_job == 'always' or (job.state == job.states.OK and cleanup_job == 'onsuccess')
        self.cleanup(delete_files=delete_files)

    def discover_outputs(self, job, inp_data, out_data, out_collections):
        input_ext = 'data'
        input_dbkey = '?'
        for _, data in inp_data.items():
            # For loop odd, but sort simulating behavior in galaxy.tools.actions
            if not data:
                continue
            input_ext = data.ext
            input_dbkey = data.dbkey or '?'

        # Create generated output children and primary datasets.
        tool_working_directory = self.tool_working_directory
        tool_provided_job_metadata = self.get_tool_provided_job_metadata()
        self.tool.discover_outputs(
            out_data,
            out_collections,
            tool_provided_job_metadata,
            job=job,
            tool_working_directory=tool_working_directory,
            inp_data=inp_data,
            input_ext=input_ext,
            input_dbkey=input_dbkey,
        )

    def check_tool_output(self, tool_stdout, tool_stderr, tool_exit_code, job, job_stdout=None, job_stderr=None):
        job_id_tag = "<unknown job id>"
        if job is not None:
            job_id_tag = job.get_id_tag()

        state, tool_stdout, tool_stderr, job_messages = check_output(self.tool.stdio_regexes, self.tool.stdio_exit_codes, tool_stdout, tool_stderr, tool_exit_code, job_id_tag)

        # Store the modified stdout and stderr in the job:
        if job is not None:
            job.set_streams(tool_stdout, tool_stderr, job_messages=job_messages, job_stdout=job_stdout, job_stderr=job_stderr)

        return state

    def cleanup(self, delete_files=True):
        # At least one of these tool cleanup actions (job import), is needed
        # for the tool to work properly, that is why one might want to run
        # cleanup but not delete files.
        try:
            if delete_files:
                for fname in self.extra_filenames:
                    os.remove(fname)
                self.external_output_metadata.cleanup_external_metadata(self.sa_session)
            galaxy.tools.imp_exp.JobExportHistoryArchiveWrapper(self.app, self.job_id).cleanup_after_job()
            galaxy.tools.imp_exp.JobImportHistoryArchiveWrapper(self.app, self.job_id).cleanup_after_job()
            if delete_files:
                self.object_store.delete(self.get_job(), base_dir='job_work', entire_dir=True, dir_only=True, obj_dir=True)
        except Exception:
            log.exception("Unable to cleanup job %d", self.job_id)

    def _collect_extra_files(self, dataset, job_working_directory):
        object_store = self.app.object_store
        store_by = getattr(object_store, "store_by", "id")
        file_name = "dataset_%s_files" % getattr(dataset, store_by)
        temp_file_path = os.path.join(job_working_directory, file_name)
        extra_dir = None
        try:
            # This skips creation of directories - object store
            # automatically creates them.  However, empty directories will
            # not be created in the object store at all, which might be a
            # problem.
            for root, dirs, files in os.walk(temp_file_path):
                extra_dir = root.replace(job_working_directory, '', 1).lstrip(os.path.sep)
                for f in files:
                    self.object_store.update_from_file(
                        dataset,
                        extra_dir=extra_dir,
                        alt_name=f,
                        file_name=os.path.join(root, f),
                        create=True,
                        preserve_symlinks=True
                    )
        except Exception as e:
            log.debug("Error in collect_associated_files: %s" % (e))

    def _collect_metrics(self, has_metrics):
        job = has_metrics.get_job()
        per_plugin_properties = self.app.job_metrics.collect_properties(job.destination_id, self.job_id, self.working_directory)
        if per_plugin_properties:
            log.info("Collecting metrics for %s %s" % (type(has_metrics).__name__, getattr(has_metrics, 'id', None)))
        for plugin, properties in per_plugin_properties.items():
            for metric_name, metric_value in properties.items():
                if metric_value is not None:
                    has_metrics.add_metric(plugin, metric_name, metric_value)

    def get_output_sizes(self):
        sizes = []
        output_paths = self.get_output_fnames()
        for outfile in [unicodify(o) for o in output_paths]:
            if os.path.exists(outfile):
                sizes.append((outfile, os.stat(outfile).st_size))
            else:
                sizes.append((outfile, 0))
        return sizes

    def check_limits(self, runtime=None):
        if self.app.job_config.limits.output_size and self.app.job_config.limits.output_size > 0:
            for outfile, size in self.get_output_sizes():
                if size > self.app.job_config.limits.output_size:
                    log.warning('(%s) Job output size %s has exceeded the global output size limit', self.get_id_tag(), os.path.basename(outfile))
                    return (JobState.runner_states.OUTPUT_SIZE_LIMIT,
                            'Job output file grew too large (greater than %s), please try different inputs or parameters'
                            % util.nice_size(self.app.job_config.limits.output_size))
        if self.app.job_config.limits.walltime_delta is not None and runtime is not None:
            if runtime > self.app.job_config.limits.walltime_delta:
                log.warning('(%s) Job runtime %s has exceeded the global walltime, it will be terminated', self.get_id_tag(), runtime)
                return (JobState.runner_states.GLOBAL_WALLTIME_REACHED,
                        'Job ran longer than the maximum allowed execution time (runtime: %s, limit: %s), please try different inputs or parameters'
                        % (str(runtime).split('.')[0], self.app.job_config.limits.walltime))
        return None

    def has_limits(self):
        has_output_limit = self.app.job_config.limits.output_size and self.app.job_config.limits.output_size > 0
        has_walltime_limit = self.app.job_config.limits.walltime_delta is not None
        return has_output_limit or has_walltime_limit

    def get_command_line(self):
        return self.command_line

    def get_session_id(self):
        return self.session_id

    def get_env_setup_clause(self):
        if self.app.config.environment_setup_file is None:
            return ''
        return '[ -f "%s" ] && . %s' % (self.app.config.environment_setup_file, self.app.config.environment_setup_file)

    def get_input_dataset_fnames(self, ds):
        filenames = []
        filenames = [ds.file_name]
        # we will need to stage in metadata file names also
        # TODO: would be better to only stage in metadata files that are actually needed (found in command line, referenced in config files, etc.)
        for key, value in ds.metadata.items():
            if isinstance(value, model.MetadataFile):
                filenames.append(value.file_name)
        return filenames

    def get_input_fnames(self):
        job = self.get_job()
        filenames = []
        for da in job.input_datasets + job.input_library_datasets:  # da is JobToInputDatasetAssociation object
            if da.dataset:
                filenames.extend(self.get_input_dataset_fnames(da.dataset))
        return filenames

    def get_input_paths(self, job=None):
        if job is None:
            job = self.get_job()
        paths = []
        for da in job.input_datasets + job.input_library_datasets:  # da is JobToInputDatasetAssociation object
            if da.dataset:
                filenames = self.get_input_dataset_fnames(da.dataset)
                for real_path in filenames:
                    false_path = self.dataset_path_rewriter.rewrite_dataset_path(da.dataset, 'input')
                    paths.append(DatasetPath(da.id, real_path=real_path, false_path=false_path, mutable=False))
        return paths

    def get_output_basenames(self):
        return list(map(os.path.basename, map(str, self.get_output_fnames())))

    def get_output_fnames(self):
        if self.output_paths is None:
            self.compute_outputs()
        return self.output_paths

    def get_mutable_output_fnames(self):
        if self.output_paths is None:
            self.compute_outputs()
        return [dsp for dsp in self.output_paths if dsp.mutable]

    def get_output_hdas_and_fnames(self):
        if self.output_hdas_and_paths is None:
            self.compute_outputs()
        return self.output_hdas_and_paths

    def compute_outputs(self):
        dataset_path_rewriter = self.dataset_path_rewriter

        job = self.get_job()
        # Job output datasets are combination of history, library, and jeha datasets.
        special = self.sa_session.query(model.JobExportHistoryArchive).filter_by(job=job).first()
        false_path = None

        results = []
        for da in job.output_datasets + job.output_library_datasets:
            da_false_path = dataset_path_rewriter.rewrite_dataset_path(da.dataset, 'output')
            mutable = da.dataset.dataset.external_filename is None
            dataset_path = DatasetPath(da.dataset.dataset.id, da.dataset.file_name, false_path=da_false_path, mutable=mutable)
            results.append((da.name, da.dataset, dataset_path))

        self.output_paths = [t[2] for t in results]
        self.output_hdas_and_paths = dict([(t[0], t[1:]) for t in results])
        if special:
            false_path = dataset_path_rewriter.rewrite_dataset_path(special.dataset, 'output')
            dsp = DatasetPath(special.dataset.id, special.dataset.file_name, false_path)
            self.output_paths.append(dsp)
        return self.output_paths

    def get_output_file_id(self, file):
        if self.output_paths is None:
            self.get_output_fnames()
        for dp in self.output_paths:
            outputs_to_working_directory = util.asbool(self.get_destination_configuration("outputs_to_working_directory", False))
            if outputs_to_working_directory and os.path.basename(dp.false_path) == file:
                return dp.dataset_id
            elif os.path.basename(dp.real_path) == file:
                return dp.dataset_id
        return None

    @property
    def object_store(self):
        return self.app.object_store

    @property
    def tmp_dir_creation_statement(self):
        tmp_dir = self.get_destination_configuration("tmp_dir", None)
        if not tmp_dir or tmp_dir.lower() == "true":
            working_directory = self.working_directory
            return '''$([ ! -e '{0}/tmp' ] || mv '{0}/tmp' '{0}'/tmp.$(date +%Y%m%d-%H%M%S) ; mkdir '{0}/tmp'; echo '{0}/tmp')'''.format(working_directory)
        else:
            return tmp_dir

    def home_directory(self):
        home_target = self.home_target
        return self._target_to_directory(home_target)

    def tmp_directory(self):
        tmp_target = self.tmp_target
        return self._target_to_directory(tmp_target)

    def _target_to_directory(self, target):
        working_directory = self.working_directory
        tmp_dir = self.get_destination_configuration("tmp_dir", None)
        if target is None or (target == "job_tmp_if_explicit" and tmp_dir is None):
            return None
        elif target in ["job_tmp", "job_tmp_if_explicit"]:
            return "$_GALAXY_JOB_TMP_DIR"
        elif target == "shared_home":
            return self.get_destination_configuration("shared_home_dir", None)
        elif target == "job_home":
            return "$_GALAXY_JOB_HOME_DIR"
        elif target == "pwd":
            return os.path.join(working_directory, "working")
        else:
            raise Exception("Unknown target type [%s]" % target)

    def get_tool_provided_job_metadata(self):
        if self.tool_provided_job_metadata is not None:
            return self.tool_provided_job_metadata

        self.tool_provided_job_metadata = self.tool.tool_provided_metadata(self)
        return self.tool_provided_job_metadata

    def get_dataset_finish_context(self, job_context, output_dataset_assoc):
        meta = {}
        tool_provided_metadata = self.get_tool_provided_job_metadata()
        meta = tool_provided_metadata.get_dataset_meta(output_dataset_assoc.name, output_dataset_assoc.dataset.dataset.id)
        if meta:
            return ExpressionContext(meta, job_context)
        return job_context

    def invalidate_external_metadata(self):
        job = self.get_job()
        self.external_output_metadata.invalidate_external_metadata([output_dataset_assoc.dataset for
                                                                    output_dataset_assoc in
                                                                    job.output_datasets + job.output_library_datasets],
                                                                   self.sa_session)

    def setup_external_metadata(self, exec_dir=None, tmp_dir=None,
                                dataset_files_path=None, config_root=None,
                                config_file=None, datatypes_config=None,
                                resolve_metadata_dependencies=False,
                                set_extension=True, **kwds):
        # extension could still be 'auto' if this is the upload tool.
        job = self.get_job()
        if set_extension:
            for output_dataset_assoc in job.output_datasets:
                if output_dataset_assoc.dataset.ext == 'auto':
                    context = self.get_dataset_finish_context(dict(), output_dataset_assoc)
                    output_dataset_assoc.dataset.extension = context.get('ext', 'data')
            self.sa_session.flush()
        if tmp_dir is None:
            # this dir should should relative to the exec_dir
            tmp_dir = self.app.config.new_file_path
        if dataset_files_path is None:
            dataset_files_path = self.app.model.Dataset.file_path
        if config_root is None:
            config_root = self.app.config.root
        if config_file is None:
            config_file = self.app.config.config_file
        if datatypes_config is None:
            datatypes_config = os.path.join(self.working_directory, 'registry.xml')
            self.app.datatypes_registry.to_xml_file(path=datatypes_config)

        output_datasets = {}
        for output_dataset_assoc in job.output_datasets + job.output_library_datasets:
            output_name = output_dataset_assoc.name
            assert output_name not in output_datasets
            output_datasets[output_dataset_assoc.name] = output_dataset_assoc.dataset

        command = self.external_output_metadata.setup_external_metadata(output_datasets,
                                                                        self.sa_session,
                                                                        exec_dir=exec_dir,
                                                                        tmp_dir=tmp_dir,
                                                                        dataset_files_path=dataset_files_path,
                                                                        config_root=config_root,
                                                                        config_file=config_file,
                                                                        datatypes_config=datatypes_config,
                                                                        job_metadata=os.path.join(self.tool_working_directory, self.tool.provided_metadata_file),
                                                                        max_metadata_value_size=self.app.config.max_metadata_value_size,
                                                                        **kwds)
        if resolve_metadata_dependencies:
            metadata_tool = self.app.toolbox.get_tool("__SET_METADATA__")
            if metadata_tool is not None:
                # Due to tool shed hacks for migrate and installed tool tests...
                # see (``setup_shed_tools_for_test`` in test/base/driver_util.py).
                dependency_shell_commands = metadata_tool.build_dependency_shell_commands(job_directory=self.working_directory, metadata=True)
                if dependency_shell_commands:
                    dependency_shell_commands = "; ".join(dependency_shell_commands)
                    command = "%s; %s" % (dependency_shell_commands, command)
        return command

    @property
    def user(self):
        job = self.get_job()
        if job.user is not None:
            return job.user.email
        elif job.galaxy_session is not None and job.galaxy_session.user is not None:
            return job.galaxy_session.user.email
        elif job.history is not None and job.history.user is not None:
            return job.history.user.email
        elif job.galaxy_session is not None:
            return 'anonymous@' + job.galaxy_session.remote_addr.split()[-1]
        else:
            return 'anonymous@unknown'

    def __update_output(self, job, hda, clean_only=False):
        """Handle writing outputs to the object store.

        This should be called regardless of whether the job was failed or not so
        that writing of partial results happens and so that the object store is
        cleaned up if the dataset has been purged.
        """
        dataset = hda.dataset
        if dataset not in job.output_library_datasets:
            purged = dataset.purged
            if not purged and not clean_only:
                self.object_store.update_from_file(dataset, create=True)
            else:
                # If the dataset is purged and Galaxy is configured to write directly
                # to the object store from jobs - be sure that file is cleaned up. This
                # is a bit of hack - our object store abstractions would be stronger
                # and more consistent if tools weren't writing there directly.
                try:
                    dataset.full_delete()
                except ObjectNotFound:
                    pass

    def __link_file_check(self):
        """ outputs_to_working_directory breaks library uploads where data is
        linked.  This method is a hack that solves that problem, but is
        specific to the upload tool and relies on an injected job param.  This
        method should be removed ASAP and replaced with some properly generic
        and stateful way of determining link-only datasets. -nate
        """
        if self.tool:
            job = self.get_job()
            param_dict = job.get_param_values(self.app)
            return self.tool.id == 'upload1' and param_dict.get('link_data_only', None) == 'link_to_files'
        else:
            # The tool is unavailable, we try to move the outputs.
            return False

    def _change_ownership(self, username, gid):
        job = self.get_job()
        external_chown_script = self.get_destination_configuration("external_chown_script", None)
        if external_chown_script is not None:
            cmd = shlex.split(external_chown_script)
            cmd.extend([self.working_directory, username, str(gid)])
            log.debug('(%s) Changing ownership of working directory with: %s' % (job.id, ' '.join(cmd)))
            p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                log.error('external script failed.')
                log.error('stdout was: %s' % stdout)
                log.error('stderr was: %s' % stderr)
            assert p.returncode == 0

    def change_ownership_for_run(self):
        job = self.get_job()
        external_chown_script = self.get_destination_configuration("external_chown_script", None)
        if external_chown_script and job.user is not None:
            try:
                self._change_ownership(self.user_system_pwent[0], str(self.user_system_pwent[3]))
            except Exception:
                log.exception('(%s) Failed to change ownership of %s, making world-writable instead' % (job.id, self.working_directory))
                os.chmod(self.working_directory, 0o777)

    def reclaim_ownership(self):
        job = self.get_job()
        external_chown_script = self.get_destination_configuration("external_chown_script", None)
        if external_chown_script and job.user is not None:
            self._change_ownership(self.galaxy_system_pwent[0], str(self.galaxy_system_pwent[3]))

    @property
    def user_system_pwent(self):
        if self.__user_system_pwent is None:
            job = self.get_job()
            self.__user_system_pwent = job.user.system_user_pwent(self.app.config.real_system_username)
        return self.__user_system_pwent

    @property
    def galaxy_system_pwent(self):
        if self.__galaxy_system_pwent is None:
            self.__galaxy_system_pwent = pwd.getpwuid(os.getuid())
        return self.__galaxy_system_pwent

    def get_output_destination(self, output_path):
        """
        Destination for outputs marked as from_work_dir. This is the normal case,
        just copy these files directly to the ulimate destination.
        """
        return output_path

    @property
    def requires_setting_metadata(self):
        if self.tool:
            return self.tool.requires_setting_metadata
        return False

    def _report_error(self):
        job = self.get_job()
        tool = self.app.toolbox.get_tool(job.tool_id, tool_version=job.tool_version) or None
        for dataset in job.output_datasets:
            self.app.error_reports.default_error_plugin.submit_report(dataset, job, tool, user_submission=False)


class TaskWrapper(JobWrapper):
    """
    Extension of JobWrapper intended for running tasks.
    Should be refactored into a generalized executable unit wrapper parent, then jobs and tasks.
    """
    # Abstract this to be more useful for running tasks that *don't* necessarily compose a job.

    def __init__(self, task, queue):
        self.task_id = task.id
        super(TaskWrapper, self).__init__(task.job, queue)
        if task.prepare_input_files_cmd is not None:
            self.prepare_input_files_cmds = [task.prepare_input_files_cmd]
        else:
            self.prepare_input_files_cmds = None
        self.status = task.states.NEW

    @property
    def dataset_path_rewriter(self):
        if self._dataset_path_rewriter is None:
            self._dataset_path_rewriter = TaskPathRewriter(self.working_directory, self._job_dataset_path_rewriter)
        return self._dataset_path_rewriter

    def can_split(self):
        # Should the job handler split this job up? TaskWrapper should
        # always return False as the job has already been split.
        return False

    def get_job(self):
        if self.job_id:
            return self.sa_session.query(model.Job).get(self.job_id)
        else:
            return None

    def get_task(self):
        return self.sa_session.query(model.Task).get(self.task_id)

    def get_id_tag(self):
        # For compatibility with drmaa job runner and TaskWrapper, instead of using job_id directly
        return self.get_task().get_id_tag()

    def prepare(self, compute_environment=None):
        """
        Prepare the job to run by creating the working directory and the
        config files.
        """
        # Restore parameters from the database
        job = self._load_job()
        task = self.get_task()

        # DBTODO New method for generating command line for a task?

        tool_evaluator = self._get_tool_evaluator(job)
        compute_environment = compute_environment or self.default_compute_environment(job)
        tool_evaluator.set_compute_environment(compute_environment)

        self.sa_session.flush()

        self.command_line, self.extra_filenames, self.environment_variables = tool_evaluator.build()

        # Ensure galaxy_lib_dir is set in case there are any later chdirs
        self.galaxy_lib_dir

        # We need command_line persisted to the db in order for Galaxy to re-queue the job
        # if the server was stopped and restarted before the job finished
        task.command_line = self.command_line
        self.sa_session.add(task)
        self.sa_session.flush()

        self.param_dict = tool_evaluator.param_dict
        self.status = 'prepared'
        return self.extra_filenames

    def fail(self, message, exception=False):
        log.error("TaskWrapper Failure %s" % message)
        self.status = 'error'
        # How do we want to handle task failure?  Fail the job and let it clean up?

    def change_state(self, state, info=False, flush=True, job=None):
        task = self.get_task()
        self.sa_session.refresh(task)
        if info:
            task.info = info
        task.state = state
        self.sa_session.add(task)
        self.sa_session.flush()

    def get_state(self):
        task = self.get_task()
        self.sa_session.refresh(task)
        return task.state

    def get_exit_code(self):
        task = self.get_task()
        self.sa_session.refresh(task)
        return task.exit_code

    def set_runner(self, runner_url, external_id):
        task = self.get_task()
        self.sa_session.refresh(task)
        task.task_runner_name = runner_url
        task.task_runner_external_id = external_id
        # DBTODO Check task job_runner_stuff
        self.sa_session.add(task)
        self.sa_session.flush()

    def finish(self, stdout, stderr, tool_exit_code=None, **kwds):
        # DBTODO integrate previous finish logic.
        # Simple finish for tasks.  Just set the flag OK.
        """
        Called to indicate that the associated command has been run. Updates
        the output datasets based on stderr and stdout from the command, and
        the contents of the output files.
        """

        # This may have ended too soon
        log.debug('task %s for job %d ended; exit code: %d'
                  % (self.task_id, self.job_id,
                      tool_exit_code if tool_exit_code is not None else -256))
        # default post job setup_external_metadata
        self.sa_session.expunge_all()
        task = self.get_task()
        # if the job was deleted, don't finish it
        if task.state == task.states.DELETED:
            # Job was deleted by an administrator
            delete_files = self.cleanup_job in ('always', 'onsuccess')
            self.cleanup(delete_files=delete_files)
            return
        elif task.state == task.states.ERROR:
            self.fail(task.info)
            return

        # Check what the tool returned. If the stdout or stderr matched
        # regular expressions that indicate errors, then set an error.
        # The same goes if the tool's exit code was in a given range.
        if self.check_tool_output(stdout, stderr, tool_exit_code=tool_exit_code, job=task) == DETECTED_JOB_STATE.OK:
            task.state = task.states.OK
        else:
            task.state = task.states.ERROR

        # Save stdout and stderr
        task.set_streams(stdout, stderr)
        self._collect_metrics(task)
        task.exit_code = tool_exit_code
        task.command_line = self.command_line
        self.sa_session.flush()

    def cleanup(self, delete_files=True):
        # There is no task cleanup.  The job cleans up for all tasks.
        pass

    def get_command_line(self):
        return self.command_line

    def get_session_id(self):
        return self.session_id

    def get_output_file_id(self, file):
        # There is no permanent output file for tasks.
        return None

    def get_tool_provided_job_metadata(self):
        # DBTODO Handle this as applicable for tasks.
        return None

    def get_dataset_finish_context(self, job_context, dataset):
        # Handled at the parent job level.  Do nothing here.
        pass

    def setup_external_metadata(self, exec_dir=None, tmp_dir=None, dataset_files_path=None,
                                config_root=None, config_file=None, datatypes_config=None,
                                set_extension=True, **kwds):
        # There is no metadata setting for tasks.  This is handled after the merge, at the job level.
        return ""

    def get_output_destination(self, output_path):
        """
        Destination for outputs marked as from_work_dir. These must be copied with
        the same basenme as the path for the ultimate output destination. This is
        required in the task case so they can be merged.
        """
        return os.path.join(self.working_directory, os.path.basename(output_path))

    def _create_working_directory(self, job):
        task = self.get_task()
        working_directory = task.working_directory
        safe_makedirs(working_directory)
        return working_directory


@six.add_metaclass(ABCMeta)
class ComputeEnvironment(object):
    """ Definition of the job as it will be run on the (potentially) remote
    compute server.
    """

    @abstractmethod
    def output_names(self):
        """ Output unqualified filenames defined by job. """

    @abstractmethod
    def output_paths(self):
        """ Output DatasetPaths defined by job. """

    @abstractmethod
    def input_paths(self):
        """ Input DatasetPaths defined by job. """

    @abstractmethod
    def working_directory(self):
        """ Job working directory (potentially remote) """

    @abstractmethod
    def config_directory(self):
        """ Directory containing config files (potentially remote) """

    @abstractmethod
    def sep(self):
        """ os.path.sep for the platform this job will execute in.
        """

    @abstractmethod
    def new_file_path(self):
        """ Absolute path to dump new files for this job on compute server. """

    @abstractmethod
    def tool_directory(self):
        """ Absolute path to tool files for this job on compute server. """

    @abstractmethod
    def version_path(self):
        """ Location of the version file for the underlying tool. """

    @abstractmethod
    def unstructured_path_rewriter(self):
        """ Return a function that takes in a value, determines if it is path
        to be rewritten (will be passed non-path values as well - onus is on
        this function to determine both if its input is a path and if it should
        be rewritten.)
        """

    @abstractmethod
    def home_directory(self):
        """Home directory of target job - none if HOME should not be set."""

    @abstractmethod
    def tmp_directory(self):
        """Temp directory of target job - none if HOME should not be set."""


class SimpleComputeEnvironment(object):

    def config_directory(self):
        return self.working_directory()

    def sep(self):
        return os.path.sep

    def unstructured_path_rewriter(self):
        return lambda v: v


class SharedComputeEnvironment(SimpleComputeEnvironment):
    """ Default ComputeEnviornment for job and task wrapper to pass
    to ToolEvaluator - valid when Galaxy and compute share all the relevant
    file systems.
    """

    def __init__(self, job_wrapper, job):
        self.app = job_wrapper.app
        self.job_wrapper = job_wrapper
        self.job = job

    def output_names(self):
        return self.job_wrapper.get_output_basenames()

    def output_paths(self):
        return self.job_wrapper.get_output_fnames()

    def input_paths(self):
        return self.job_wrapper.get_input_paths(self.job)

    def working_directory(self):
        return self.job_wrapper.working_directory

    def new_file_path(self):
        return os.path.abspath(self.app.config.new_file_path)

    def version_path(self):
        return self.job_wrapper.get_version_string_path()

    def tool_directory(self):
        tool_dir = self.job_wrapper.tool.tool_dir
        if tool_dir is not None:
            tool_dir = os.path.abspath(tool_dir)
        return tool_dir

    def home_directory(self):
        return self.job_wrapper.home_directory()

    def tmp_directory(self):
        return self.job_wrapper.tmp_directory()


class NoopQueue(object):
    """
    Implements the JobQueue / JobStopQueue interface but does nothing
    """

    def put(self, *args, **kwargs):
        return

    def put_stop(self, *args):
        return

    def shutdown(self):
        return


class ParallelismInfo(object):
    """
    Stores the information (if any) for running multiple instances of the tool in parallel
    on the same set of inputs.
    """

    def __init__(self, tag):
        self.method = tag.get('method')
        if isinstance(tag, dict):
            items = tag.items()
        else:
            items = tag.attrib.items()
        self.attributes = dict([item for item in items if item[0] != 'method'])
        if len(self.attributes) == 0:
            # legacy basic mode - provide compatible defaults
            self.attributes['split_size'] = 20
            self.attributes['split_mode'] = 'number_of_parts'
