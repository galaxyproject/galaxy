"""
Support for running a tool in Galaxy via an internal job management system
"""

import copy
import datetime
import errno
import json
import logging
import os
import pwd
import shlex
import shutil
import sys
import time
import traceback
from json import loads
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    TYPE_CHECKING,
)

import yaml
from packaging.version import Version
from pulsar.client.staging import COMMAND_VERSION_FILENAME
from sqlalchemy import select

from galaxy import (
    model,
    util,
)
from galaxy.datatypes import sniff
from galaxy.exceptions import (
    MessageException,
    ObjectInvalid,
    ObjectNotFound,
)
from galaxy.files import ProvidesFileSourcesUserContext
from galaxy.job_execution.actions.post import ActionBox
from galaxy.job_execution.compute_environment import SharedComputeEnvironment
from galaxy.job_execution.output_collect import (
    collect_extra_files,
    collect_shrinked_content_from_path,
)
from galaxy.job_execution.setup import (
    create_working_directory_for_job,
    ensure_configs_directory,
    JobIO,
    TOOL_PROVIDED_JOB_METADATA_FILE,
    TOOL_PROVIDED_JOB_METADATA_KEYS,
)
from galaxy.jobs.mapper import (
    JobMappingException,
    JobRunnerMapper,
)
from galaxy.jobs.runners import (
    BaseJobRunner,
    JobState,
)
from galaxy.metadata import get_metadata_compute_strategy
from galaxy.model import (
    Job,
    store,
    Task,
)
from galaxy.model.base import transaction
from galaxy.model.store import copy_dataset_instance_metadata_attributes
from galaxy.model.store.discover import MaxDiscoveredFilesExceededError
from galaxy.objectstore import (
    ObjectStorePopulator,
    serialize_static_object_store_config,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.tool_util.deps import requirements
from galaxy.tool_util.output_checker import (
    check_output,
    DETECTED_JOB_STATE,
)
from galaxy.tool_util.parser.stdio import StdioErrorLevel
from galaxy.tools.evaluation import (
    PartialToolEvaluator,
    ToolEvaluator,
)
from galaxy.util import (
    parse_xml_string,
    RWXRWXRWX,
    safe_makedirs,
    unicodify,
)
from galaxy.util.bunch import Bunch
from galaxy.util.expressions import ExpressionContext
from galaxy.util.path import external_chown
from galaxy.util.xml_macros import load
from galaxy.web_stack.handlers import ConfiguresHandlers
from galaxy.work.context import WorkRequestContext

if TYPE_CHECKING:
    from galaxy.jobs.handler import JobHandlerQueue
    from galaxy.tools import Tool

log = logging.getLogger(__name__)

# Override with config.default_job_shell.
DEFAULT_JOB_SHELL = "/bin/bash"
DEFAULT_LOCAL_WORKERS = 4

DEFAULT_CLEANUP_JOB = "always"
VALID_TOOL_CLASSES = ["local", "requires_galaxy"]


class JobDestination(Bunch):
    """
    Provides details about where a job runs
    """

    def __init__(self, **kwds):
        self["id"] = None
        self["url"] = None
        self["tags"] = None
        self["runner"] = None
        self["legacy"] = False
        self["converted"] = False
        self["shell"] = None
        self["env"] = []
        self["resubmit"] = []
        # dict is appropriate (rather than a bunch) since keys may not be valid as attributes
        self["params"] = {}

        # Use the values persisted in an existing job
        if "from_job" in kwds and kwds["from_job"].destination_id is not None:
            self["id"] = kwds["from_job"].destination_id
            self["params"] = kwds["from_job"].destination_params

        super().__init__(**kwds)


class JobToolConfiguration(Bunch):
    """
    Provides details on what handler and destination a tool should use

    A JobToolConfiguration will have the required attribute 'id' and optional
    attributes 'handler', 'destination', and 'params'
    """

    def __init__(self, **kwds):
        self["handler"] = None
        self["destination"] = None
        self["params"] = {}
        super().__init__(**kwds)

    def get_resource_group(self):
        return self.get("resources", None)


def config_exception(e, file):
    abs_path = os.path.abspath(file)
    message = f"Problem parsing file '{abs_path}', "
    message += "please correct the indicated portion of the file and restart Galaxy. "
    message += unicodify(e)
    log.exception(message)
    return Exception(message)


def job_config_xml_to_dict(config, root):
    config_dict = {}

    runners = {}
    config_dict["runners"] = runners

    # Parser plugins section populate 'runners' and 'dynamic' in config_dict.
    if (plugins := root.find("plugins")) is not None:
        for plugin in ConfiguresHandlers._findall_with_required(plugins, "plugin", ("id", "type", "load")):
            if plugin.get("type") == "runner":
                workers = plugin.get("workers", plugins.get("workers", JobConfiguration.DEFAULT_NWORKERS))
                runner_kwds = JobConfiguration.get_params(config, plugin)
                plugin_id = plugin.get("id")
                runner_info = dict(id=plugin_id, load=plugin.get("load"), workers=int(workers), kwds=runner_kwds)
                runners[plugin_id] = runner_info
            else:
                log.error(f"Unknown plugin type: {plugin.get('type')}")

        for plugin in ConfiguresHandlers._findall_with_required(plugins, "plugin", ("id", "type")):
            if plugin.get("id") == "dynamic" and plugin.get("type") == "runner":
                config_dict["dynamic"] = JobConfiguration.get_params(config, plugin)

    handling_config_dict = ConfiguresHandlers.xml_to_dict(config, root.find("handlers"))
    config_dict["handling"] = handling_config_dict

    # Parse destinations
    environments = []

    destinations = root.find("destinations")
    for destination in ConfiguresHandlers._findall_with_required(destinations, "destination", ("id", "runner")):
        destination_id = destination.get("id")
        destination_metrics = destination.get("metrics", None)

        environment = {"id": destination_id}

        metrics_to_dict = {"src": "default"}
        if destination_metrics:
            if not util.asbool(destination_metrics):
                metrics_to_dict = {"src": "disabled"}
            else:
                metrics_to_dict = {"src": "path", "path": destination_metrics}
        else:
            metrics_elements = ConfiguresHandlers._findall_with_required(destination, "job_metrics", ())
            if metrics_elements:
                metrics_to_dict = {"src": "xml_element", "xml_element": metrics_elements[0]}

        environment["metrics"] = metrics_to_dict

        params = JobConfiguration.get_params(config, destination)
        # Handle legacy XML enabling sudo when using docker by default.
        if "docker_sudo" not in params:
            params["docker_sudo"] = "true"

        # TODO: handle enabled/disabled in configure_from
        environment["params"] = params
        environment["env"] = JobConfiguration.get_envs(destination)
        destination_resubmits = JobConfiguration.get_resubmits(destination)
        if destination_resubmits:
            environment["resubmit"] = destination_resubmits
        # TODO: handle empty resubmits defaults in configure_from

        runner = destination.get("runner")
        if runner:
            environment["runner"] = runner

        tags = destination.get("tags")
        # Store tags as a list
        if tags is not None:
            tags = [x.strip() for x in tags.split(",")]
            environment["tags"] = tags

        environments.append(environment)

    config_dict["execution"] = {
        "environments": environments,
    }
    default_destination = ConfiguresHandlers.get_xml_default(config, destinations)
    if default_destination:
        config_dict["execution"]["default"] = default_destination

    resources_config_dict = {}
    resource_groups = {}

    # Parse resources...
    if (resources := root.find("resources")) is not None:
        default_resource_group = resources.get("default", None)
        if default_resource_group:
            resources_config_dict["default"] = default_resource_group

        for group in ConfiguresHandlers._findall_with_required(resources, "group"):
            group_id = group.get("id")
            fields_str = group.get("fields", None) or group.text or ""
            fields = [f for f in fields_str.split(",") if f]
            resource_groups[group_id] = fields

    resources_config_dict["groups"] = resource_groups
    config_dict["resources"] = resources_config_dict

    # Parse tool mappings
    config_dict["tools"] = []
    if (tools := root.find("tools")) is not None:
        for tool in tools.findall("tool"):
            # There can be multiple definitions with identical ids, but different params
            tool_mapping_conf = {}
            for key in ["handler", "destination", "id", "resources", "class"]:
                value = tool.get(key)
                if value:
                    if key == "destination":
                        key = "environment"
                    tool_mapping_conf[key] = value
            tool_mapping_conf["params"] = JobConfiguration.get_params(config, tool)
            config_dict["tools"].append(tool_mapping_conf)

    limits_config = []
    if (limits := root.find("limits")) is not None:
        for limit in JobConfiguration._findall_with_required(limits, "limit", ("type",)):
            limit_dict = {}
            for key in ["type", "tag", "id", "window"]:
                if key == "type" and key.startswith("destination_"):
                    key = f"environment_{key[len('destination_'):]}"
                value = limit.get(key)
                if value:
                    limit_dict[key] = value
                limit_dict["value"] = limit.text
            limits_config.append(limit_dict)

    config_dict["limits"] = limits_config
    return config_dict


class JobConfiguration(ConfiguresHandlers):
    """A parser and interface to advanced job management features.

    These features are configured in the job configuration, by default, ``job_conf.yml``
    """

    runner_plugins: List[dict]
    handlers: dict
    handler_runner_plugins: Dict[str, str]
    tools: Dict[str, list]
    tool_classes: Dict[str, list]
    resource_groups: Dict[str, list]
    destinations: Dict[str, tuple]
    resource_parameters: Dict[str, Any]
    DEFAULT_BASE_HANDLER_POOLS = ("job-handlers",)

    DEFAULT_NWORKERS = 4

    DEFAULT_HANDLER_READY_WINDOW_SIZE = 100

    JOB_RESOURCE_CONDITIONAL_XML = """<conditional name="__job_resource">
        <param name="__job_resource__select" type="select" label="Job Resource Parameters">
            <option value="no">Use default job resource parameters</option>
            <option value="yes">Specify job resource parameters</option>
        </param>
        <when value="no"/>
        <when value="yes"/>
    </conditional>"""

    def __init__(self, app: MinimalManagerApp):
        """Parse the job configuration XML."""
        self.app = app
        self.runner_plugins = []
        self.dynamic_params: Optional[Dict[str, Any]] = None
        self.handlers = {}
        self.handler_runner_plugins = {}
        self.default_handler_id = None
        self.handler_assignment_methods = None
        self.handler_assignment_methods_configured = False
        self.handler_max_grab = None
        self.handler_ready_window_size = None
        self.destinations = {}
        self.default_destination_id = None
        self.tools = {}
        self.tool_classes = {}
        self.resource_groups = {}
        self.default_resource_group = None
        self.resource_parameters = {}
        self.limits = Bunch(
            registered_user_concurrent_jobs=None,
            anonymous_user_concurrent_jobs=None,
            walltime=None,
            walltime_delta=None,
            total_walltime={},
            output_size=None,
            destination_user_concurrent_jobs={},
            destination_total_concurrent_jobs={},
        )

        default_resubmits = []
        default_resubmit_condition = self.app.config.default_job_resubmission_condition
        if default_resubmit_condition:
            default_resubmits.append(
                dict(
                    environment=None,
                    condition=default_resubmit_condition,
                    handler=None,
                    delay=None,
                )
            )
        self.default_resubmits = default_resubmits

        self.__parse_resource_parameters()
        # Initialize the config
        try:
            if "job_config" in self.app.config.config_dict:
                job_config_dict = self.app.config.config_dict["job_config"]
                log.debug("Read job configuration inline from Galaxy config")
            else:
                job_config_file = self.app.config.job_config_file
                if not self.app.config.is_set("job_config_file") and not os.path.exists(job_config_file):
                    old_default_job_config_file = os.path.join(self.app.config.config_dir, "job_conf.xml")
                    if os.path.exists(old_default_job_config_file):
                        job_config_file = old_default_job_config_file
                        log.warning(
                            "Implicit loading of job_conf.xml has been deprecated and will be removed in a future"
                            f" release of Galaxy. Please convert to YAML at {self.app.config.job_config_file} or"
                            f" explicitly set `job_config_file` to {job_config_file} to remove this message"
                        )
                if ".xml" in job_config_file:
                    tree = load(job_config_file)
                    job_config_dict = self.__parse_job_conf_xml(tree)
                else:
                    with open(job_config_file) as f:
                        job_config_dict = yaml.safe_load(f)
                log.debug(f"Read job configuration from file: {job_config_file}")

            # Load tasks if configured
            if self.app.config.use_tasked_jobs:
                job_config_dict["runners"]["tasks"] = dict(
                    id="tasks", load="tasks", workers=self.app.config.local_task_queue_workers, kwds={}
                )

            self._configure_from_dict(job_config_dict)

            log.debug("Done loading job configuration")

        except OSError:
            log.warning(
                'Job configuration "%s" does not exist, using default job configuration',
                self.app.config.job_config_file,
            )
            self.__set_default_job_conf()
        except Exception as e:
            raise config_exception(e, job_config_file)

    def _configure_from_dict(self, job_config_dict):
        for runner_id, runner_info in job_config_dict["runners"].items():
            if "kwds" not in runner_info:
                # convert all 'extra' parameters into kwds, allows defining a runner
                # with a flat dictionary.
                kwds = {}
                for key, value in runner_info.items():
                    if key in ["id", "load", "workers"]:
                        continue
                    kwds[key] = value
                runner_info["kwds"] = kwds

            if not self.__is_enabled(runner_info.get("kwds")):
                continue
            runner_info["id"] = runner_id
            if runner_id == "dynamic":
                log.warning("Deprecated treatment of dynamic running configuration as an actual job runner.")
                self.dynamic_params = runner_info["kwds"]
                continue
            self.runner_plugins.append(runner_info)
        if "dynamic" in job_config_dict:
            self.dynamic_params = job_config_dict["dynamic"]

        # Parse handlers
        handling_config_dict = job_config_dict.get("handling", {})
        self._init_handler_assignment_methods(handling_config_dict)
        self._init_handlers(handling_config_dict)
        if not self.handler_assignment_methods_configured:
            self._set_default_handler_assignment_methods()
        else:
            self.app.application_stack.init_job_handling(self)
        log.info("Job handler assignment methods set to: %s", ", ".join(self.handler_assignment_methods))
        for tag, handlers in [(t, h) for t, h in self.handlers.items() if isinstance(h, list)]:
            log.info("Tag [%s] handlers: %s", tag, ", ".join(handlers))
        self.handler_ready_window_size = int(
            handling_config_dict.get("ready_window_size", JobConfiguration.DEFAULT_HANDLER_READY_WINDOW_SIZE)
        )

        # Parse environments
        job_metrics = self.app.job_metrics
        execution_dict = job_config_dict.get("execution", {})
        environments = execution_dict.get("environments", [])
        enviroment_iter = (
            ((e["id"], e) for e in environments) if isinstance(environments, list) else environments.items()
        )
        for environment_id, environment_dict in enviroment_iter:
            metrics = environment_dict.get("metrics")
            if metrics is None:
                metrics = {"src": "default"}
            if isinstance(metrics, list):
                job_metrics.set_destination_conf_dicts(environment_id, metrics)
            else:
                metrics_src = metrics.get("src") or "default"
                if metrics_src != "default":
                    # customized metrics for this environment.
                    if metrics_src == "disabled":
                        job_metrics.set_destination_instrumenter(environment_id, None)
                    elif metrics_src == "xml_element":
                        metrics_element = metrics.get("xml_element")
                        job_metrics.set_destination_conf_element(environment_id, metrics_element)
                    elif metrics_src == "path":
                        metrics_conf_path = self.app.config.resolve_path(metrics.get("path"))
                        job_metrics.set_destination_conf_file(environment_id, metrics_conf_path)

            destination_kwds = {}

            params = environment_dict.get("params")
            if params is None:
                # Treat the excess keys in the environment as the destination parameters
                # allowing a flat configuration of these things.
                params = {}
                for key, value in environment_dict.items():
                    if key in ["id", "tags", "runner", "shell", "env", "resubmit"]:
                        continue
                    params[key] = value
                environment_dict["params"] = params

            for key in ["tags", "runner", "shell", "env", "resubmit", "params"]:
                if key in environment_dict:
                    destination_kwds[key] = environment_dict[key]
            destination_kwds["id"] = environment_id
            job_destination = JobDestination(**destination_kwds)
            if not self.__is_enabled(job_destination.params):
                continue

            if not job_destination.resubmit:
                resubmits = self.default_resubmits
                job_destination.resubmit = resubmits

            self.destinations[environment_id] = (job_destination,)
            if job_destination.tags is not None:
                for tag in job_destination.tags:
                    if tag not in self.destinations:
                        self.destinations[tag] = []
                    self.destinations[tag].append(job_destination)

        # Determine the default destination
        self.default_destination_id = self._ensure_default_set(
            execution_dict.get("default"), list(self.destinations.keys()), auto=True
        )

        # Read in resources
        resources = job_config_dict.get("resources", {})
        self.default_resource_group = resources.get("default", None)
        for group_id, fields in resources.get("groups", {}).items():
            self.resource_groups[group_id] = fields

        tools = job_config_dict.get("tools", [])
        for tool in tools:
            raw_tool_id = tool.get("id")
            tool_class = tool.get("class")
            if raw_tool_id is not None:
                assert tool_class is None
                tool_id = raw_tool_id.lower().rstrip("/")
                if tool_id not in self.tools:
                    self.tools[tool_id] = []
            else:
                assert tool_class in VALID_TOOL_CLASSES, tool_class
                if tool_class not in self.tool_classes:
                    self.tool_classes[tool_class] = []

            params = tool.get("params")
            if params is None:
                params = {}
                for key, value in tool.items():
                    if key in ["environment", "handler", "id", "resources"]:
                        continue
                    params[key] = value
                tool["params"] = params
            if "environment" in tool:
                tool["destination"] = tool.pop("environment")

            jtc = JobToolConfiguration(**dict(tool.items()))
            if raw_tool_id:
                self.tools[tool_id].append(jtc)
            else:
                self.tool_classes[tool_class].append(jtc)

        types = dict(
            registered_user_concurrent_jobs=int,
            anonymous_user_concurrent_jobs=int,
            walltime=str,
            total_walltime=str,
            output_size=util.size_to_bytes,
        )

        # Parse job limits
        for limit_dict in job_config_dict.get("limits", []):
            limit_type = limit_dict.get("type")
            if limit_type.startswith("environment_"):
                limit_type = f"destination_{limit_type[len('environment_'):]}"

            limit_value = limit_dict.get("value")
            # concurrent_jobs renamed to destination_user_concurrent_jobs in job_conf.xml
            if limit_type in (
                "destination_user_concurrent_jobs",
                "concurrent_jobs",
                "destination_total_concurrent_jobs",
            ):
                id = limit_dict.get("tag", None) or limit_dict.get("id")
                if limit_type == "destination_total_concurrent_jobs":
                    self.limits.destination_total_concurrent_jobs[id] = int(limit_value)
                else:
                    self.limits.destination_user_concurrent_jobs[id] = int(limit_value)
            elif limit_type == "total_walltime":
                self.limits.total_walltime["window"] = int(limit_dict.get("window")) or 30
                self.limits.total_walltime["raw"] = types.get(limit_type, str)(limit_value)
            elif limit_value:
                self.limits.__dict__[limit_type] = types.get(limit_type, str)(limit_value)

        if self.limits.walltime is not None:
            h, m, s = (int(v) for v in self.limits.walltime.split(":"))
            self.limits.walltime_delta = datetime.timedelta(0, s, 0, 0, m, h)

        if "raw" in self.limits.total_walltime:
            h, m, s = (int(v) for v in self.limits.total_walltime["raw"].split(":"))
            self.limits.total_walltime["delta"] = datetime.timedelta(0, s, 0, 0, m, h)

    def __parse_job_conf_xml(self, tree):
        """Loads the new-style job configuration from options in the job config file (by default, job_conf.xml).

        :param tree: Object representing the root ``<job_conf>`` object in the job config file.
        :type tree: ``lxml.etree._Element``
        """
        root = tree.getroot()
        log.debug(f"Loading job configuration from {self.app.config.job_config_file}")

        job_config_dict = job_config_xml_to_dict(self.app.config, root)
        return job_config_dict

    def _parse_handler(self, handler_id, process_dict):
        for plugin_id in process_dict.get("plugins") or []:
            if handler_id not in self.handler_runner_plugins:
                self.handler_runner_plugins[handler_id] = []
            self.handler_runner_plugins[handler_id].append(plugin_id)

    def __set_default_job_conf(self):
        # Run jobs locally
        self.runner_plugins = [dict(id="local", load="local", workers=DEFAULT_LOCAL_WORKERS)]
        # Load tasks if configured
        if self.app.config.use_tasked_jobs:
            self.runner_plugins.append(dict(id="tasks", load="tasks", workers=DEFAULT_LOCAL_WORKERS))
        # Set the handlers
        self._init_handler_assignment_methods()
        if not self.handler_assignment_methods_configured:
            self._set_default_handler_assignment_methods()
        else:
            self.app.application_stack.init_job_handling(self)
        self.handler_ready_window_size = JobConfiguration.DEFAULT_HANDLER_READY_WINDOW_SIZE
        # Set the destination
        self.default_destination_id = "local"
        self.destinations["local"] = [JobDestination(id="local", runner="local")]
        log.debug("Done loading job configuration")

    def get_tool_resource_xml(self, tool_id, tool_type):
        """Given a tool id, return XML elements describing parameters to
        insert into job resources.

        :tool id: A tool ID (a string)
        :tool type: A tool type (a string)

        :returns: List of parameter elements.
        """
        if tool_id and tool_type in ("default", "manage_data"):
            # TODO: Only works with exact matches, should handle different kinds of ids
            # the way destination lookup does.
            resource_group = None
            if tool_id in self.tools:
                resource_group = self.tools[tool_id][0].get_resource_group()
            resource_group = resource_group or self.default_resource_group
            if resource_group and resource_group in self.resource_groups:
                fields_names = self.resource_groups[resource_group]
                fields = []
                for field_name in fields_names:
                    if field_name not in self.resource_parameters:
                        raise KeyError(
                            f"Failed to find field for resource {field_name} in resource parameters {self.resource_parameters}"
                        )
                    fields.append(parse_xml_string(self.resource_parameters[field_name]))

                if fields:
                    conditional_element = parse_xml_string(self.JOB_RESOURCE_CONDITIONAL_XML)
                    when_yes_elem = conditional_element.findall("when")[1]
                    for parameter in fields:
                        when_yes_elem.append(parameter)
                    return conditional_element

    def __parse_resource_parameters(self):
        self.resource_parameters = util.parse_resource_parameters(self.app.config.job_resource_params_file)

    @staticmethod
    def get_params(config, parent):
        rval = {}
        for param in parent.findall("param"):
            key = param.get("id")
            if key in ["container", "container_override"]:
                containers = map(requirements.container_from_element, param.findall("container"))
                param_value = [c.to_dict() for c in containers]
            else:
                param_value = param.text

            if "from_environ" in param.attrib:
                environ_var = param.attrib["from_environ"]
                param_value = os.environ.get(environ_var, param_value)
            elif "from_config" in param.attrib:
                config_val = param.attrib["from_config"]
                param_value = config.config_dict.get(config_val, param_value)

            rval[key] = param_value
        return rval

    def __get_params(self, parent):
        """Parses any child <param> tags in to a dictionary suitable for persistence.

        :param parent: Parent element in which to find child <param> tags.
        :type parent: ``lxml.etree._Element``

        :returns: dict
        """
        return JobConfiguration.get_params(self.app.config, parent)

    @staticmethod
    def get_envs(parent):
        """Parses any child <env> tags in to a dictionary suitable for persistence.

        :param parent: Parent element in which to find child <env> tags.
        :type parent: ``lxml.etree._Element``

        :returns: dict
        """
        rval = []
        for param in parent.findall("env"):
            rval.append(
                dict(
                    name=param.get("id"),
                    file=param.get("file"),
                    execute=param.get("exec"),
                    value=param.text,
                    raw=util.asbool(param.get("raw", "false")),
                )
            )
        return rval

    @staticmethod
    def get_resubmits(parent):
        """Parses any child <resubmit> tags in to a dictionary suitable for persistence.

        :param parent: Parent element in which to find child <resubmit> tags.
        :type parent: ``lxml.etree._Element``

        :returns: dict
        """
        rval = []
        for resubmit in parent.findall("resubmit"):
            rval.append(
                dict(
                    condition=resubmit.get("condition"),
                    environment=resubmit.get("destination"),
                    handler=resubmit.get("handler"),
                    delay=resubmit.get("delay"),
                )
            )
        return rval

    def __is_enabled(self, params):
        """Check for an enabled parameter - pop it out - and return as boolean."""
        enabled = True
        if "enabled" in (params or {}):
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
        return JobToolConfiguration(
            id="_default_", handler=self.default_handler_id, destination=self.default_destination_id
        )

    # Called upon instantiation of a Tool object
    def get_job_tool_configurations(self, ids, tool_classes):
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
        match_found = False
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
                rval.extend(self.tools[id])
                match_found = True

        if not match_found:
            for tool_class in tool_classes:
                if tool_class in self.tool_classes:
                    rval.extend(self.tool_classes[tool_class])
                    match_found = True
                    break
        if not match_found:
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

    def get_destinations(self, id_or_tag) -> Iterable[JobDestination]:
        """Given a destination ID or tag, return all JobDestinations matching the provided ID or tag

        :param id_or_tag: A destination ID or tag.
        :type id_or_tag: str

        :returns: list or tuple of JobDestinations

        Destinations are not deepcopied, so they should not be passed to
        anything which might modify them.
        """
        return self.destinations.get(id_or_tag, [])

    def get_job_runner_plugins(self, handler_id: str):
        """Load all configured job runner plugins

        :returns: list of job runner plugins
        """
        rval: Dict[str, BaseJobRunner] = {}
        if handler_id in self.handler_runner_plugins:
            plugins_to_load = [rp for rp in self.runner_plugins if rp["id"] in self.handler_runner_plugins[handler_id]]
            log.info(
                "Handler '%s' will load specified runner plugins: %s",
                handler_id,
                ", ".join(rp["id"] for rp in plugins_to_load),
            )
        else:
            plugins_to_load = self.runner_plugins
            log.info("Handler '%s' will load all configured runner plugins", handler_id)
        for runner in plugins_to_load:
            class_names = []
            module = None
            id = runner["id"]
            load = runner["load"]
            if ":" in load:
                # Name to load was specified as '<module>:<class>'
                module_name, class_name = load.rsplit(":", 1)
                class_names = [class_name]
                module = __import__(module_name)
            else:
                # Name to load was specified as '<module>'
                if "." not in load:
                    # For legacy reasons, try from galaxy.jobs.runners first if there's no '.' in the name
                    module_name = f"galaxy.jobs.runners.{load}"
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
            for comp in module_name.split(".")[1:]:
                module = getattr(module, comp)
            assert module  # make mypy happy
            if not class_names:
                # If there's not a ':', we check <module>.__all__ for class names
                try:
                    assert module.__all__
                    class_names = module.__all__
                except AssertionError:
                    log.error(f'Runner "{load}" does not contain a list of exported classes in __all__')
                    continue
            for class_name in class_names:
                runner_class = getattr(module, class_name)
                try:
                    assert issubclass(runner_class, BaseJobRunner)
                except TypeError:
                    log.warning(f"A non-class name was found in __all__, ignoring: {id}")
                    continue
                except AssertionError:
                    log.warning(
                        f"Job runner classes must be subclassed from BaseJobRunner, {id} has bases: {runner_class.__bases__}"
                    )
                    continue
                try:
                    rval[id] = runner_class(
                        self.app, runner.get("workers", JobConfiguration.DEFAULT_NWORKERS), **runner.get("kwds", {})
                    )
                except TypeError:
                    log.exception(
                        "Job runner '%s:%s' has not been converted to a new-style runner or encountered TypeError on load",
                        module_name,
                        class_name,
                    )
                    rval[id] = runner_class(self.app)
                log.debug(f"Loaded job runner '{module_name}:{class_name}' as '{id}'")
        return rval

    def is_id(self, collection):
        """Given a collection of handlers or destinations, indicate whether the collection represents a real ID

        :param collection: A representation of a destination or handler
        :type collection: tuple or list

        :returns: bool
        """
        return isinstance(collection, tuple)

    def is_tag(self, collection):
        """Given a collection of handlers or destinations, indicate whether the collection represents a tag

        :param collection: A representation of a destination or handler
        :type collection: tuple or list

        :returns: bool
        """
        return isinstance(collection, list)

    def convert_legacy_destinations(self, job_runners):
        """Converts legacy (from a URL) destinations to contain the appropriate runner params defined in the URL.

        :param job_runners: All loaded job runner plugins.
        :type job_runners: list of job runner plugins
        """
        for id, destination in [
            (id, destinations[0]) for id, destinations in self.destinations.items() if self.is_id(destinations)
        ]:
            # Only need to deal with real destinations, not members of tags
            if destination.legacy and not destination.converted:
                if destination.runner in job_runners:
                    destination.params = job_runners[destination.runner].url_to_destination(destination.url).params
                    destination.converted = True
                    if destination.params:
                        log.debug(f"Legacy destination with id '{id}', url '{destination.url}' converted, got params:")
                        for k, v in destination.params.items():
                            log.debug(f"    {k}: {v}")
                    else:
                        log.debug(f"Legacy destination with id '{id}', url '{destination.url}' converted, got params:")
                else:
                    log.warning(
                        f"Legacy destination with id '{id}' could not be converted: Unknown runner plugin: {destination.runner}"
                    )


class HasResourceParameters:
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


class MinimalJobWrapper(HasResourceParameters):
    """
    Wraps a 'model.Job' with convenience methods for running processes and
    state management.
    """

    is_task = False

    def __init__(
        self,
        job: model.Job,
        app: MinimalManagerApp,
        use_persisted_destination: bool = False,
        tool: Optional["Tool"] = None,
    ):
        self.job_id = job.id
        self.session_id = job.session_id
        self.user_id = job.user_id
        self.app = app
        self.tool = tool
        self.sa_session = self.app.model.context
        self.extra_filenames: List[str] = []
        self.environment_variables: List[Dict[str, str]] = []
        self.interactivetools: List[Dict[str, Any]] = []
        self.command_line = None
        self.version_command_line = None
        self._dependency_shell_commands = None
        # Tool versioning variables
        self.version_string = ""
        self.__galaxy_lib_dir = None
        # If the job has an object_store_id ensure working directory is setup, otherwise
        # wait for that to be assigned before configuring it. Either way the working
        # directory does not to be configured on this object before prepare() is called.
        if job.object_store_id:
            self._setup_working_directory(job=job)
        # the path rewriter needs destination params, so it cannot be set up until after the destination has been
        # resolved
        self._job_io = None
        self.tool_provided_job_metadata = None
        self.params = None
        if job.params:
            self.params = loads(job.params)
        self.runner_command_line = None

        # Wrapper holding the info required to restore and clean up from files used for setting metadata externally
        self.__external_output_metadata = None
        self.__has_tasks = bool(job.tasks)

        self.__commands_in_new_shell = True
        self.__user_system_pwent = None
        self.__galaxy_system_pwent = None
        self.__working_directory = None

    @property
    def external_output_metadata(self):
        if self.__external_output_metadata is None:
            self.__external_output_metadata = get_metadata_compute_strategy(
                self.app.config,
                self.job_id,
                metadata_strategy_override=self.metadata_strategy,
                tool_id=self.tool.id,
                tool_type=self.tool.tool_type,
            )
        return self.__external_output_metadata

    @property
    def metadata_strategy(self):
        try:
            metadata_strategy_override = self.get_destination_configuration("metadata_strategy", None)
        except JobMappingException:
            metadata_strategy_override = None
        if self.__has_tasks:
            metadata_strategy_override = "directory"
        return metadata_strategy_override

    @property
    def remote_command_line(self):
        use_remote = self.get_destination_configuration("tool_evaluation_strategy") == "remote"
        # It wouldn't be hard to support history export, but we want to do this in task queue workers anyway ...
        stmt = select(model.JobExportHistoryArchive).filter_by(job=self.get_job()).limit(1)
        return use_remote and self.external_output_metadata.extended and not self.sa_session.scalars(stmt).first()

    def tool_directory(self):
        tool_dir = self.tool and self.tool.tool_dir
        if tool_dir is not None:
            tool_dir = os.path.abspath(tool_dir)
        return tool_dir

    @property
    def job_io(self):
        if self._job_io is None:
            job = self.get_job()
            work_request = WorkRequestContext(self.app, user=job.user, galaxy_session=job.galaxy_session)
            user_context = ProvidesFileSourcesUserContext(work_request)
            tool_source = self.tool and self.tool.tool_source.to_string()
            self._job_io = JobIO(
                sa_session=self.sa_session,
                job=job,
                working_directory=self.working_directory,
                outputs_directory=self.outputs_directory,
                outputs_to_working_directory=self.outputs_to_working_directory,
                galaxy_url=self.galaxy_url,
                version_path=self.get_version_string_path(),
                tool_directory=self.tool_directory(),
                home_directory=self.home_directory(),
                tmp_directory=self.tmp_directory(),
                tool_data_path=self.app.config.tool_data_path,
                galaxy_data_manager_data_path=self.app.config.galaxy_data_manager_data_path,
                new_file_path=self.app.config.new_file_path,
                builds_file_path=self.app.config.builds_file_path,
                len_file_path=self.app.config.len_file_path,
                file_sources_dict=self.app.file_sources.to_dict(for_serialization=True, user_context=user_context),
                user_context=user_context,
                check_job_script_integrity=self.app.config.check_job_script_integrity,
                check_job_script_integrity_count=self.app.config.check_job_script_integrity_count,
                check_job_script_integrity_sleep=self.app.config.check_job_script_integrity_sleep,
                tool_source=tool_source,
                tool_source_class=type(self.tool.tool_source).__name__ if self.tool else None,
                tool_dir=self.tool and self.tool.tool_dir,
                is_task=self.is_task,
            )
        return self._job_io

    @property
    def outputs_directory(self):
        """Default location of ``outputs_to_working_directory``."""
        return None if self.created_with_galaxy_version < Version("20.01") else "outputs"

    @property
    def outputs_to_working_directory(self):
        return util.asbool(self.get_destination_configuration("outputs_to_working_directory", False))

    @property
    def created_with_galaxy_version(self):
        galaxy_version = self.get_job().galaxy_version or "19.05"
        return Version(galaxy_version)

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
        """Remove the job after it is complete, should return "always", "onsuccess", or "never"."""
        return self.get_destination_configuration("cleanup_job", DEFAULT_CLEANUP_JOB)

    @property
    def requires_containerization(self):
        return util.asbool(self.get_destination_configuration("require_container", "False"))

    @property
    def use_metadata_binary(self):
        return util.asbool(self.get_destination_configuration("use_metadata_binary", "False"))

    def can_split(self):
        # Should the job handler split this job up?
        return self.app.config.use_tasked_jobs and self.tool.parallelism

    @property
    def is_cwl_job(self):
        return self.tool.tool_type == "cwl"

    def get_job_runner_url(self):
        log.warning(f"({self.job_id}) Job runner URLs are deprecated, use destinations instead.")
        return self.job_destination.url

    def get_parallelism(self):
        return self.tool.parallelism

    @property
    def shell(self):
        return self.job_destination.shell or getattr(self.app.config, "default_job_shell", DEFAULT_JOB_SHELL)

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
        return os.environ.get("VIRTUAL_ENV", None)

    # legacy naming
    get_job_runner = get_job_runner_url

    @property
    def job_destination(self) -> JobDestination:
        """Subclassses can return a configured job destination."""
        return JobDestination()

    @property
    def galaxy_url(self):
        return self.get_destination_configuration("galaxy_infrastructure_url")

    def get_job(self) -> model.Job:
        job = self.sa_session.get(Job, self.job_id)
        assert job
        return job

    def get_id_tag(self):
        # For compatibility with drmaa, which uses job_id right now, and TaskWrapper
        return self.get_job().get_id_tag()

    def get_param_dict(self, _job=None):
        """
        Restore the dictionary of parameters from the database.
        """
        job = _job or self.get_job()
        param_dict = {p.name: p.value for p in job.parameters}
        param_dict = self.tool.params_from_strings(param_dict, self.app)
        return param_dict

    @property
    def validate_outputs(self):
        job = self.get_job()
        for p in job.parameters:
            if p.name == "__validate_outputs__":
                log.info(f"validate... {p.value}")
                return loads(p.value)
        return False

    def get_version_string_path(self):
        return os.path.abspath(os.path.join(self.working_directory, "outputs", COMMAND_VERSION_FILENAME))

    def __prepare_upload_paramfile(self, job):
        """Special case paramfile handling for the upload tool. Copies the paramfile to the working directory"""
        new = os.path.join(self.working_directory, "upload_params.json")
        param_file_path = json.loads(next(iter(param.value for param in job.parameters if param.name == "paramfile")))
        try:
            shutil.copy2(param_file_path, new)
        except OSError as exc:
            # It won't exist at the old path if setup was interrupted and tried again later
            if exc.errno != errno.ENOENT or not os.path.exists(new):
                raise

    def prepare(self, compute_environment=None):
        """
        Prepare the job to run by creating the working directory and the
        config files.
        """
        prepare_timer = util.ExecutionTimer()

        if not os.path.exists(self.working_directory):
            os.mkdir(self.working_directory)

        job = self._load_job()

        def get_special():
            stmt = select(model.JobExportHistoryArchive).filter_by(job=job).limit(1)
            if jeha := self.sa_session.scalars(stmt).first():
                return jeha.fda
            stmt = select(model.GenomeIndexToolData).filter_by(job=job).limit(1)
            return self.sa_session.scalars(stmt).first()

        # TODO: The upload tool actions that create the paramfile can probably be turned in to a configfile to remove this special casing
        if job.tool_id == "upload1":
            self.__prepare_upload_paramfile(job)

        tool_evaluator = self._get_tool_evaluator(job)
        compute_environment = compute_environment or self.default_compute_environment(job)
        tool_evaluator.set_compute_environment(compute_environment, get_special=get_special)
        (
            self.command_line,
            self.version_command_line,
            self.extra_filenames,
            self.environment_variables,
            self.interactivetools,
        ) = tool_evaluator.build()
        job.command_line = self.command_line

        # Ensure galaxy_lib_dir is set in case there are any later chdirs
        self.galaxy_lib_dir  # noqa: B018
        if self.tool.requires_galaxy_python_environment or self.remote_command_line:
            # These tools (upload, metadata, data_source) may need access to the datatypes registry.
            self.app.datatypes_registry.to_xml_file(os.path.join(self.working_directory, "registry.xml"))
        if self.remote_command_line:
            os.makedirs(os.path.join(self.working_directory, "metadata", "outputs_new"), exist_ok=True)
            self.job_io.to_json(path=os.path.join(self.working_directory, "metadata", "outputs_new", "job_io.json"))
            self.app.tool_data_tables.to_json(
                path=os.path.join(self.working_directory, "metadata", "outputs_new", "tool_data_tables.json")
            )
        job.dependencies = self.tool.dependencies
        self.sa_session.add(job)
        with transaction(self.sa_session):
            self.sa_session.commit()
        log.debug(f"Job wrapper for Job [{job.id}] prepared {prepare_timer}")

    def _setup_working_directory(self, job=None):
        if job is None:
            job = self.get_job()
        try:
            working_directory = self._create_working_directory(job)
            self.__working_directory = working_directory
            # The tool execution is given a working directory beneath the
            # "job" working directory.
            safe_makedirs(self.tool_working_directory)
            safe_makedirs(os.path.join(working_directory, "outputs"))
            log.debug("(%s) Working directory for job is: %s", self.job_id, self.working_directory)
        except ObjectInvalid:
            raise Exception("(%s) Unable to create job working directory", job.id)

    @property
    def guest_ports(self):
        if hasattr(self, "interactivetools"):
            # This works when the job is being prepared
            guest_ports = [ep.get("port") for ep in self.interactivetools]
            return guest_ports
        else:
            # This works when handling a running job
            job = self._load_job()
            return [ep.tool_port for ep in job.interactivetool_entry_points]

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
                job, base_dir="job_work", dir_only=True, obj_dir=True
            )
        return self.__working_directory

    def working_directory_exists(self) -> bool:
        job = self.get_job()
        return self.app.object_store.exists(job, base_dir="job_work", dir_only=True, obj_dir=True)

    @property
    def tool_working_directory(self):
        return os.path.join(self.working_directory, "working")

    def _create_working_directory(self, job):
        return create_working_directory_for_job(self.object_store, job)

    def clear_working_directory(self):
        job = self.get_job()
        if not os.path.exists(self.working_directory):
            log.warning(
                "(%s): Working directory clear requested but %s does not exist", self.job_id, self.working_directory
            )
            return

        self.object_store.create(
            job, base_dir="job_work", dir_only=True, obj_dir=True, extra_dir="_cleared_contents", extra_dir_at_root=True
        )
        base = self.object_store.get_filename(
            job, base_dir="job_work", dir_only=True, obj_dir=True, extra_dir="_cleared_contents", extra_dir_at_root=True
        )
        date_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        arc_dir = os.path.join(base, date_str)
        shutil.move(self.working_directory, arc_dir)
        self._setup_working_directory(job=job)
        log.debug("(%s) Previous working directory moved to %s", self.job_id, arc_dir)

    def default_compute_environment(self, job=None):
        if not job:
            job = self.get_job()
        return SharedComputeEnvironment(self.job_io, job)

    def _load_job(self):
        # Load job from database and verify it has user or session.
        # Restore parameters from the database
        job = self.get_job()
        if job.user is None and job.galaxy_session is None:
            raise Exception(f"Job {job.id} has no user and no session.")
        return job

    def _get_tool_evaluator(self, job):
        klass = PartialToolEvaluator if self.remote_command_line else ToolEvaluator
        tool_evaluator = klass(
            app=self.app,
            job=job,
            tool=self.tool,
            local_working_directory=self.working_directory,
        )
        return tool_evaluator

    def _fix_output_permissions(self):
        for path in [dp.real_path for dp in self.job_io.get_mutable_output_fnames()]:
            if os.path.exists(path):
                util.umask_fix_perms(path, self.app.config.umask, 0o666, self.app.config.gid)

    def fail(
        self,
        message,
        exception=False,
        tool_stdout="",
        tool_stderr="",
        exit_code=None,
        job_stdout=None,
        job_stderr=None,
        job_metrics_directory=None,
    ):
        """
        Indicate job failure by setting state and message on all output
        datasets.
        """
        job = self.get_job()
        self.sa_session.refresh(job)

        # If this fail method is being called because a dynamic rule raised JobMappingException, the call to
        # self.get_destination_configuration() below accesses self.job_destination and will just cause
        # JobMappingException to be raised again.
        try:
            self.job_destination  # noqa: B018
        except JobMappingException as exc:
            log.debug(
                "(%s) fail(): Job destination raised JobMappingException('%s'), caching fake '__fail__' "
                "destination for completion of fail method",
                self.get_id_tag(),
                unicodify(exc.failure_message),
            )
            self.job_runner_mapper.cached_job_destination = JobDestination(id="__fail__")

        # Might be AssertionError or other exception
        message = str(message)
        working_directory_exists = self.working_directory_exists()

        if not job.tasks and working_directory_exists:
            # If job was composed of tasks, don't attempt to recollect statistics
            self._collect_metrics(job, job_metrics_directory)

        # if the job was deleted, don't fail it
        if not job.state == job.states.DELETED:
            # Check if the failure is due to an exception
            if exception:
                # Save the traceback immediately in case we generate another
                # below
                job.traceback = unicodify(traceback.format_exc(), strip_null=True)
                # Get the exception and let the tool attempt to generate
                # a better message
                etype, evalue, tb = sys.exc_info()

            try:
                if self.outputs_to_working_directory and not self.__link_file_check() and working_directory_exists:
                    for dataset_path in self.job_io.get_output_fnames():
                        try:
                            shutil.move(dataset_path.false_path, dataset_path.real_path)
                            log.debug("fail(): Moved %s to %s", dataset_path.false_path, dataset_path.real_path)
                        except FileNotFoundError as e:
                            log.warning("fail(): Missing output file in working directory: %s", unicodify(e))
            except Exception as e:
                log.exception(str(e))
            for dataset_assoc in job.output_datasets + job.output_library_datasets:
                dataset = dataset_assoc.dataset
                self.sa_session.refresh(dataset)
                dataset.state = dataset.states.ERROR
                dataset.blurb = "tool error"
                dataset.info = message
                dataset.mark_unhidden()
                if dataset.ext == "auto":
                    dataset.extension = "data"
                try:
                    self.__update_output(job, dataset)
                except Exception:
                    # Failure to update the output of a failed job should not prevent completion of the failure method
                    log.exception(
                        "(%s) fail(): Failed to update job output dataset with id: %s",
                        self.get_id_tag(),
                        dataset.dataset.id,
                    )
                # Pause any dependent jobs (and those jobs' outputs)
                for dep_job_assoc in dataset.dependent_jobs:
                    self.pause(
                        dep_job_assoc.job,
                        "Execution of this dataset's job is paused because its input datasets are in an error state.",
                    )
            job.set_final_state(
                job.states.ERROR, supports_skip_locked=self.app.application_stack.supports_skip_locked()
            )
            job.command_line = self.command_line
            job.info = message
            # TODO: Put setting the stdout, stderr, and exit code in one place
            # (not duplicated with the finish method).
            job.set_streams(tool_stdout, tool_stderr, job_stdout=job_stdout, job_stderr=job_stderr)
            # Let the exit code be Null if one is not provided:
            if exit_code is not None:
                job.exit_code = exit_code

            self.sa_session.add(job)
            with transaction(self.sa_session):
                self.sa_session.commit()
        else:
            for dataset_assoc in job.output_datasets:
                dataset = dataset_assoc.dataset
                # Any reason for clean_only here? We should probably be more consistent and transfer
                # the partial files to the object store regardless of whether job.state == DELETED
                self.__update_output(job, dataset, clean_only=True)

        if working_directory_exists:
            self._fix_output_permissions()
        self._report_error()
        # Perform email action even on failure.
        for pja in [
            pjaa.post_job_action for pjaa in job.post_job_actions if pjaa.post_job_action.action_type == "EmailAction"
        ]:
            ActionBox.execute(self.app, self.sa_session, pja, job)

        # If the job was deleted, call tool specific fail actions (used for e.g. external metadata) and clean up
        if self.tool:
            try:
                self.tool.job_failed(self, message, exception)
            except Exception:
                log.exception(f"Error occured while calling tool specific fail actions for job {job.id}")
        cleanup_job = self.cleanup_job
        delete_files = cleanup_job == "always" or (cleanup_job == "onsuccess" and job.state == job.states.DELETED)
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

        if "__resubmit_delay_seconds" in (destination_params := job.destination_params):
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
        with transaction(self.sa_session):
            self.sa_session.commit()

    def change_state(self, state, info=False, flush=True, job=None):
        if job is None:
            job = self.get_job()
            self.sa_session.refresh(job)
        else:
            # job attributes may have been changed, so we can't refresh here,
            # but we want to make sure that the terminal state check below works
            # on the current job state value to minimize race conditions.
            self.sa_session.expire(job, ["state"])

        if job.state in model.Job.terminal_states:
            log.warning(
                "(%s) Ignoring state change from '%s' to '%s' for job that is already terminal",
                job.id,
                job.state,
                state,
            )
            return
        if info:
            job.info = info
        state_changed = job.set_state(state)
        self.sa_session.add(job)
        if state_changed:
            job.update_output_states(self.app.application_stack.supports_skip_locked())
        if flush:
            with transaction(self.sa_session):
                self.sa_session.commit()

    def get_state(self) -> str:
        job = self.get_job()
        self.sa_session.refresh(job)
        return job.state

    def set_runner(self, runner_url, external_id):
        log.warning("set_runner() is deprecated, use set_job_destination()")
        self.set_job_destination(self.job_destination, external_id)

    def set_external_id(self, external_id, job=None, flush=True):
        if job is None:
            job = self.get_job()
        job.job_runner_external_id = external_id
        self.sa_session.add(job)
        if flush:
            with transaction(self.sa_session):
                self.sa_session.commit()

    @property
    def home_target(self):
        home_target = self.tool and self.tool.home_target
        return home_target

    @property
    def tmp_target(self):
        return self.tool and self.tool.tmp_target

    def get_destination_configuration(self, key, default=None):
        """Get a destination parameter that can be defaulted back
        in app.config if it needs to be applied globally.
        """
        dest_params = self.job_destination.params
        return self.get_job().get_destination_configuration(dest_params, self.app.config, key, default)

    def enqueue(self):
        job = self.get_job()
        # Change to queued state before handing to worker thread so the runner won't pick it up again
        self.change_state(model.Job.states.QUEUED, flush=False, job=job)
        # Persist the destination so that the job will be included in counts if using concurrency limits
        self.set_job_destination(self.job_destination, None, flush=False, job=job)
        # Set object store after job destination so can leverage parameters...
        self._set_object_store_ids(job)
        with transaction(self.sa_session):
            self.sa_session.commit()
        return True

    def set_job_destination(self, job_destination, external_id=None, flush=True, job=None):
        """Subclasses should implement this to persist a destination, if necessary."""

    def _set_object_store_ids(self, job):
        if job.object_store_id:
            # We aren't setting this during job creation anymore, but some existing
            # jobs may have this set. Skip this following code if that is the case.
            return

        object_store = self.app.object_store
        if not object_store.object_store_allows_id_selection:
            self._set_object_store_ids_basic(job)
        else:
            self._set_object_store_ids_full(job)

    def _set_object_store_ids_basic(self, job):
        object_store_id = self.get_destination_configuration("object_store_id", None)
        object_store_populator = ObjectStorePopulator(self.app, job.user)
        require_shareable = job.requires_shareable_storage(self.app.security_agent)

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
            object_store_populator.set_object_store_id(dataset, require_shareable=require_shareable)

        job.object_store_id = object_store_populator.object_store_id
        self._setup_working_directory(job=job)

    def _set_object_store_ids_full(self, job):
        user = job.user
        object_store_id = self.get_destination_configuration("object_store_id", None)
        split_object_stores = None
        object_store_id_overrides = None

        if object_store_id is None:
            object_store_id = job.preferred_object_store_id
        if object_store_id is None and job.workflow_invocation_step:
            workflow_invocation_step = job.workflow_invocation_step
            invocation_object_stores = workflow_invocation_step.preferred_object_stores
            if invocation_object_stores.is_split_configuration:
                # Redo for subworkflows...
                outputs_object_store_populator = ObjectStorePopulator(self.app, user)
                preferred_outputs_object_store_id = invocation_object_stores.preferred_outputs_object_store_id
                outputs_object_store_populator.object_store_id = preferred_outputs_object_store_id

                intermediate_object_store_populator = ObjectStorePopulator(self.app, user)
                preferred_intermediate_object_store_id = invocation_object_stores.preferred_intermediate_object_store_id
                intermediate_object_store_populator.object_store_id = preferred_intermediate_object_store_id

                # default for the job... probably isn't used in anyway but for job working
                # directory?
                object_store_id = invocation_object_stores.preferred_outputs_object_store_id
                object_store_populator = intermediate_object_store_populator
                output_names = [o.output_name for o in workflow_invocation_step.workflow_step.unique_workflow_outputs]
                if invocation_object_stores.step_effective_outputs is not None:
                    output_names = [
                        o for o in output_names if invocation_object_stores.is_output_name_an_effective_output(o)
                    ]

                # we resolve the precreated datasets here with object store populators
                # but for dynamically created datasets after the job we need to record
                # the outputs and set them accordingly
                object_store_id_overrides = {o: preferred_outputs_object_store_id for o in output_names}

                def split_object_stores(output_name):  # noqa: F811 https://github.com/PyCQA/pyflakes/issues/783
                    if "|__part__|" in output_name:
                        output_name = output_name.split("|__part__|", 1)[0]
                    if output_name in output_names:
                        return outputs_object_store_populator
                    else:
                        return intermediate_object_store_populator

            else:
                object_store_id = invocation_object_stores.preferred_object_store_id

        if object_store_id is None:
            history = job.history
            if history is not None:
                object_store_id = history.preferred_object_store_id
        if object_store_id is None:
            if user is not None:
                object_store_id = user.preferred_object_store_id

        require_shareable = job.requires_shareable_storage(self.app.security_agent)
        if not split_object_stores:
            object_store_populator = ObjectStorePopulator(self.app, user)

            if object_store_id:
                object_store_populator.object_store_id = object_store_id

            for dataset_assoc in job.output_datasets + job.output_library_datasets:
                dataset = dataset_assoc.dataset
                object_store_populator.set_object_store_id(dataset, require_shareable=require_shareable)

            job.object_store_id = object_store_populator.object_store_id
            self._setup_working_directory(job=job)
        else:
            for dataset_assoc in job.output_datasets + job.output_library_datasets:
                dataset = dataset_assoc.dataset
                dataset_object_store_populator = split_object_stores(dataset_assoc.name)
                dataset_object_store_populator.set_object_store_id(dataset, require_shareable=require_shareable)
            job.object_store_id = object_store_populator.object_store_id
            job.object_store_id_overrides = object_store_id_overrides
            self._setup_working_directory(job=job)

    def _finish_dataset(self, output_name, dataset, job, context, final_job_state, remote_metadata_directory):
        implicit_collection_jobs = job.implicit_collection_jobs_association
        purged = dataset.dataset.purged
        if not purged and dataset.dataset.external_filename is None:
            trynum = 0
            while trynum < self.app.config.retry_job_output_collection:
                try:
                    # Attempt to short circuit NFS attribute caching
                    os.stat(dataset.dataset.get_file_name())
                    os.chown(dataset.dataset.get_file_name(), os.getuid(), -1)
                    trynum = self.app.config.retry_job_output_collection
                except (OSError, ObjectNotFound) as e:
                    trynum += 1
                    log.warning("Error accessing dataset with ID %i, will retry: %s", dataset.dataset.id, unicodify(e))
                    time.sleep(2)
        if getattr(dataset, "hidden_beneath_collection_instance", None):
            dataset.visible = False
        dataset.blurb = "done"
        dataset.peek = "no peek"
        dataset.info = dataset.info or ""
        if context["stdout"].strip():
            # Ensure white space between entries
            dataset.info = f"{dataset.info.rstrip()}\n{context['stdout'].strip()}"
        if context["stderr"].strip():
            # Ensure white space between entries
            dataset.info = f"{dataset.info.rstrip()}\n{context['stderr'].strip()}"
        dataset.tool_version = self.version_string
        if "uuid" in context:
            dataset.dataset.uuid = context["uuid"]
        self.__update_output(job, dataset)
        if not purged:
            collect_extra_files(self.object_store, dataset, self.working_directory, self.outputs_to_working_directory)
        if job.states.ERROR == final_job_state:
            dataset.blurb = "error"
            if not implicit_collection_jobs:
                # Only unhide dataset outputs that are not part of a implicit collection
                dataset.mark_unhidden()
        elif not purged:
            # If the tool was expected to set the extension, attempt to retrieve it
            if dataset.ext == "auto":
                dataset.extension = context.get("ext", "data")
                dataset.init_meta(copy_from=dataset)
            # if a dataset was copied, it won't appear in our dictionary:
            # either use the metadata from originating output dataset, or call set_meta on the copies
            # it would be quicker to just copy the metadata from the originating output dataset,
            # but somewhat trickier (need to recurse up the copied_from tree), for now we'll call set_meta()
            retry_internally = util.asbool(self.get_destination_configuration("retry_metadata_internally", True))
            if not retry_internally and self.tool.tool_type == "interactive":
                retry_internally = util.asbool(
                    self.get_destination_configuration("retry_interactivetool_metadata_internally", retry_internally)
                )
            metadata_set_successfully = self.external_output_metadata.external_metadata_set_successfully(
                dataset, output_name, self.sa_session, working_directory=self.working_directory
            )
            if not metadata_set_successfully:
                if self.tool.tool_type == "expression":
                    dataset.set_metadata_success_state()
                elif retry_internally:
                    # If Galaxy was expected to sniff type and didn't - do so.
                    if dataset.ext == "_sniff_":
                        extension = sniff.handle_uploaded_dataset_file(
                            dataset.dataset.get_file_name(), self.app.datatypes_registry
                        )
                        dataset.extension = extension

                    # call datatype.set_meta directly for the initial set_meta call during dataset creation
                    dataset.datatype.set_meta(dataset, overwrite=False)
                else:
                    dataset.state = model.HistoryDatasetAssociation.states.FAILED_METADATA
            else:
                self.external_output_metadata.load_metadata(
                    dataset,
                    output_name,
                    self.sa_session,
                    working_directory=self.working_directory,
                    remote_metadata_directory=remote_metadata_directory,
                )
            if final_job_state != job.states.ERROR:
                line_count = context.get("line_count", None)
                dataset.set_peek(line_count=line_count)
        else:
            # Handle purged datasets.
            dataset.blurb = "empty"
            if dataset.ext == "auto":
                dataset.extension = context.get("ext", "txt")

        for context_key in TOOL_PROVIDED_JOB_METADATA_KEYS:
            if context_key in context:
                context_value = context[context_key]
                setattr(dataset, context_key, context_value)

        self.sa_session.add(dataset)

    def finish(
        self,
        tool_stdout,
        tool_stderr,
        tool_exit_code=None,
        job_stdout=None,
        job_stderr=None,
        check_output_detected_state=None,
        remote_metadata_directory=None,
        job_metrics_directory=None,
    ):
        """
        Called to indicate that the associated command has been run. Updates
        the output datasets based on stderr and stdout from the command, and
        the contents of the output files.
        """
        finish_timer = self.app.execution_timer_factory.get_timer(
            "internals.galaxy.jobs.job_wrapper_finish", "job_wrapper.finish for job ${job_id} executed"
        )

        # default post job setup
        job = self.get_job()

        def fail(message=job.info, exception=None):
            if not isinstance(exception, (AssertionError, MessageException)):
                # Only attach MessageException and AssertionErrors to job.traceback
                exception = None
            return self.fail(
                message,
                tool_stdout=tool_stdout,
                tool_stderr=tool_stderr,
                exit_code=tool_exit_code,
                job_stdout=job_stdout,
                job_stderr=job_stderr,
                exception=exception,
                job_metrics_directory=job_metrics_directory,
            )

        # TODO: After failing here, consider returning from the function.
        try:
            self.reclaim_ownership()
        except Exception:
            log.exception(f"({job.id}) Failed to change ownership of {self.working_directory}, failing")
            return fail()

        # if the job was deleted, don't finish it
        if job.state == job.states.DELETED or job.state == job.states.ERROR:
            # SM: Note that, at this point, the exit code must be saved in case
            # there was an error. Errors caught here could mean that the job
            # was deleted by an administrator (based on old comments), but it
            # could also mean that a job was broken up into tasks and one of
            # the tasks failed. So include the stderr, stdout, and exit code:
            return fail()

        extended_metadata = self.external_output_metadata.extended

        # We collect the stderr from tools that write their stderr to galaxy.json
        tool_provided_metadata = self.get_tool_provided_job_metadata()

        # Check the tool's stdout, stderr, and exit code for errors, but only
        # if the job has not already been marked as having an error.
        # The job's stdout and stderr will be set accordingly.

        # We set final_job_state to use for dataset management, but *don't* set
        # job.state until after dataset discovery to prevent history issues
        if check_output_detected_state is None:
            check_output_detected_state = self.check_tool_output(
                tool_stdout,
                tool_stderr,
                tool_exit_code=tool_exit_code,
                job=job,
                job_stdout=job_stdout,
                job_stderr=job_stderr,
            )

        if check_output_detected_state == DETECTED_JOB_STATE.OK and not tool_provided_metadata.has_failed_outputs():
            final_job_state = job.states.OK
        else:
            final_job_state = job.states.ERROR

        if not extended_metadata and self.outputs_to_working_directory and not self.__link_file_check():
            # output will be moved by job if metadata_strategy is extended_metadata, so skip moving here
            for dataset_path in self.job_io.get_output_fnames():
                try:
                    shutil.move(dataset_path.false_path, dataset_path.real_path)
                    log.debug(f"finish(): Moved {dataset_path.false_path} to {dataset_path.real_path}")
                except OSError:
                    # this can happen if Galaxy is restarted during the job's
                    # finish method - the false_path file has already moved,
                    # and when the job is recovered, it won't be found.
                    if os.path.exists(dataset_path.real_path) and os.stat(dataset_path.real_path).st_size > 0:
                        log.warning(
                            "finish(): %s not found, but %s is not empty, so it will be used instead",
                            dataset_path.false_path,
                            dataset_path.real_path,
                        )
                    else:
                        # Prior to fail we need to set job.state
                        job.set_state(final_job_state)
                        return fail(f"Job {job.id}'s output dataset(s) could not be read")

        job_context = ExpressionContext(dict(stdout=tool_stdout, stderr=tool_stderr))
        if extended_metadata:
            try:
                import_options = store.ImportOptions(allow_dataset_object_edit=True, allow_edit=True)
                import_model_store = store.get_import_model_store_for_directory(
                    os.path.join(self.working_directory, "metadata", "outputs_populated"),
                    app=self.app,
                    import_options=import_options,
                    user=job.user,
                    tag_handler=self.app.tag_handler.create_tag_handler_session(job.galaxy_session),
                )
                import_model_store.perform_import(history=job.history, job=job)
                if job.state == job.states.ERROR:
                    final_job_state = job.state
            except store.FileTracebackException as e:
                job.traceback = e.traceback
                log.exception(f"Problem generating command line for Job {job.id}.\n{job.traceback}")
                raise
            except Exception:
                log.exception(f"problem importing job outputs. stdout [{job.stdout}] stderr [{job.stderr}]")
                raise
        else:
            if self.tool.version_string_cmd:
                version_filename = self.get_version_string_path()
                self.version_string = collect_shrinked_content_from_path(version_filename)

        output_dataset_associations = job.output_datasets + job.output_library_datasets
        inp_data, out_data, out_collections = job.io_dicts()

        if not extended_metadata:
            # importing metadata will discover outputs if extended metadata
            try:
                self.discover_outputs(job, inp_data, out_data, out_collections, final_job_state=final_job_state)
            except MaxDiscoveredFilesExceededError as e:
                final_job_state = job.states.ERROR
                job.job_messages = [
                    {
                        "type": "internal",
                        "desc": str(e),
                        "error_level": StdioErrorLevel.FATAL,
                    }
                ]

            for dataset_assoc in output_dataset_associations:
                is_discovered_dataset = getattr(dataset_assoc.dataset, "discovered", False)
                context = self.get_dataset_finish_context(job_context, dataset_assoc)
                # should this also be checking library associations? - can a library item be added from a history before the job has ended? -
                # lets not allow this to occur
                # need to update all associated output hdas, i.e. history was shared with job running
                for dataset in (
                    dataset_assoc.dataset.dataset.history_associations
                    + dataset_assoc.dataset.dataset.library_associations
                ):
                    if is_discovered_dataset:
                        if dataset is dataset_assoc.dataset:
                            continue
                        elif dataset.extension == dataset_assoc.dataset.extension or dataset.extension == "auto":
                            copy_dataset_instance_metadata_attributes(dataset_assoc.dataset, dataset)
                            continue
                    output_name = dataset_assoc.name

                    # Handles retry internally on error for instance...
                    self._finish_dataset(output_name, dataset, job, context, final_job_state, remote_metadata_directory)
                if (
                    not final_job_state == job.states.ERROR
                    and not dataset_assoc.dataset.dataset.state == job.states.ERROR
                    and not dataset_assoc.dataset.dataset.state == model.Dataset.states.DEFERRED
                ):
                    # We don't set datsets in error state to OK because discover_outputs may have already set the state to error
                    dataset_assoc.dataset.dataset.state = model.Dataset.states.OK

        if job.states.ERROR == final_job_state:
            for dataset_assoc in output_dataset_associations:
                log.debug("(%s) setting dataset %s state to ERROR", job.id, dataset_assoc.dataset.dataset.id)
                # TODO: This is where the state is being set to error. Change it!
                dataset_assoc.dataset.dataset.state = model.Dataset.states.ERROR
                # Pause any dependent jobs (and those jobs' outputs)
                for dep_job_assoc in dataset_assoc.dataset.dependent_jobs:
                    self.pause(
                        dep_job_assoc.job,
                        "Execution of this dataset's job is paused because its input datasets are in an error state.",
                    )

        for pja in job.post_job_actions:
            if pja.post_job_action.action_type not in ActionBox.immediate_actions:
                ActionBox.execute(self.app, self.sa_session, pja.post_job_action, job, final_job_state=final_job_state)

        # The exit code will be null if there is no exit code to be set.
        # This is so that we don't assign an exit code, such as 0, that
        # is either incorrect or has the wrong semantics.
        if tool_exit_code is not None:
            job.exit_code = tool_exit_code
        # custom post process setup

        collected_bytes = 0
        quota_source_info = None
        # Once datasets are collected, set the total dataset size (includes extra files)
        for dataset_assoc in job.output_datasets:
            dataset = dataset_assoc.dataset.dataset
            # assume all datasets in a job get written to the same objectstore
            quota_source_info = dataset.quota_source_info
            collected_bytes += dataset.set_total_size()
            if dataset.purged:
                # Purge, in case job wrote directly to object store
                dataset.full_delete()
                collected_bytes = 0

        user = job.user
        if user and collected_bytes > 0 and quota_source_info is not None and quota_source_info.use:
            user.adjust_total_disk_usage(collected_bytes, quota_source_info.label)

        # Certain tools require tasks to be completed after job execution
        # ( this used to be performed in the "exec_after_process" hook, but hooks are deprecated ).
        param_dict = self.get_param_dict(job)
        task_wrapper = None
        try:
            task_wrapper = self.tool.exec_after_process(
                self.app, inp_data, out_data, param_dict, job=job, final_job_state=final_job_state
            )
        except Exception as e:
            log.exception(f"exec_after_process hook failed for job {self.job_id}")
            return fail("exec_after_process hook failed", exception=e)

        # Call 'exec_after_process' hook
        self.tool.call_hook(
            "exec_after_process",
            self.app,
            inp_data=inp_data,
            out_data=out_data,
            param_dict=param_dict,
            tool=self.tool,
            stdout=job.stdout,
            stderr=job.stderr,
        )

        self._fix_output_permissions()

        # Empirically, we need to update job.user and
        # job.workflow_invocation_step.workflow_invocation in separate
        # transactions. Best guess as to why is that the workflow_invocation
        # may or may not exist when the job is first loaded by the handler -
        # and depending on whether it is or not sqlalchemy orders the updates
        # differently and deadlocks can occur (one thread updates user and
        # waits on invocation and the other updates invocation and waits on
        # user).
        with transaction(self.sa_session):
            self.sa_session.commit()

        # Finally set the job state.  This should only happen *after* all
        # dataset creation, and will allow us to eliminate force_history_refresh.
        job.set_final_state(final_job_state, supports_skip_locked=self.app.application_stack.supports_skip_locked())
        if not job.tasks:
            # If job was composed of tasks, don't attempt to recollect statistics
            self._collect_metrics(job, job_metrics_directory)
        with transaction(self.sa_session):
            self.sa_session.commit()
        if job.state == job.states.ERROR:
            self._report_error()
        elif task_wrapper:
            # Only task is setting metadata (if necessary) on expression tool output.
            # The dataset state is SETTING_METADATA, which delays dependent jobs until the task completes.
            task_wrapper.delay()
        cleanup_job = self.cleanup_job
        delete_files = cleanup_job == "always" or (job.state == job.states.OK and cleanup_job == "onsuccess")
        self.cleanup(delete_files=delete_files)
        log.debug(finish_timer.to_str(job_id=self.job_id, tool_id=job.tool_id))

    def discover_outputs(self, job, inp_data, out_data, out_collections, final_job_state):
        # Try to just recover input_ext and dbkey from job parameters (used and set in
        # galaxy.tools.actions). Old jobs may have not set these in the job parameters
        # before persisting them.
        input_params = job.raw_param_dict()
        input_ext = input_params.get("__input_ext")
        input_dbkey = input_params.get("dbkey")
        if input_ext is not None:
            input_ext = loads(input_ext)
            input_dbkey = loads(input_dbkey)
        else:
            # Legacy jobs without __input_ext.
            input_ext = "data"
            input_dbkey = "?"
            for _, data in inp_data.items():
                # For loop odd, but sort simulating behavior in galaxy.tools.actions
                if not data:
                    continue
                input_ext = data.ext
                input_dbkey = data.dbkey or "?"

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
            final_job_state=final_job_state,
        )

    def check_tool_output(self, tool_stdout, tool_stderr, tool_exit_code, job, job_stdout=None, job_stderr=None):
        state, tool_stdout, tool_stderr, job_messages = check_output(
            self.tool.stdio_regexes, self.tool.stdio_exit_codes, tool_stdout, tool_stderr, tool_exit_code
        )

        # Store the modified stdout and stderr in the job:
        if job is not None:
            job.set_streams(
                tool_stdout, tool_stderr, job_messages=job_messages, job_stdout=job_stdout, job_stderr=job_stderr
            )

        return state

    def cleanup(self, delete_files: bool = True) -> None:
        # At least one of these tool cleanup actions (job import), is needed
        # for the tool to work properly, that is why one might want to run
        # cleanup but not delete files.
        try:
            if delete_files:
                for fname in self.extra_filenames:
                    try:
                        os.remove(fname)
                    except OSError as e:
                        if e.errno != errno.ENOENT:
                            raise
            if delete_files:
                self.object_store.delete(
                    self.get_job(), base_dir="job_work", entire_dir=True, dir_only=True, obj_dir=True
                )
        except Exception:
            log.exception("Unable to cleanup job %d", self.job_id)

    def _collect_metrics(self, has_metrics, job_metrics_directory=None):
        job = has_metrics.get_job()
        if job_metrics_directory is None:
            try:
                # working directory might have been purged already
                job_metrics_directory = self.working_directory
            except Exception:
                log.exception("Could not recover job metrics")
                return
        per_plugin_properties = self.app.job_metrics.collect_properties(
            job.destination_id, self.job_id, job_metrics_directory
        )
        if per_plugin_properties:
            log.info(
                f"Collecting metrics for {type(has_metrics).__name__} {getattr(has_metrics, 'id', None)} in {job_metrics_directory}"
            )
        for plugin, properties in per_plugin_properties.items():
            for metric_name, metric_value in properties.items():
                if metric_value is not None:
                    has_metrics.add_metric(plugin, metric_name, metric_value)

    def get_output_sizes(self):
        sizes = []
        output_paths = self.job_io.get_output_fnames()
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
                    log.warning(
                        "(%s) Job output size %s has exceeded the global output size limit",
                        self.get_id_tag(),
                        os.path.basename(outfile),
                    )
                    return (
                        JobState.runner_states.OUTPUT_SIZE_LIMIT,
                        f"Job output file grew too large (greater than {util.nice_size(self.app.job_config.limits.output_size)}), please try different inputs or parameters",
                    )
        if self.app.job_config.limits.walltime_delta is not None and runtime is not None:
            if runtime > self.app.job_config.limits.walltime_delta:
                log.warning(
                    "(%s) Job runtime %s has exceeded the global walltime, it will be terminated",
                    self.get_id_tag(),
                    runtime,
                )
                return (
                    JobState.runner_states.GLOBAL_WALLTIME_REACHED,
                    "Job ran longer than the maximum allowed execution time (runtime: {}, limit: {}), please try different inputs or parameters".format(
                        str(runtime).split(".")[0], self.app.job_config.limits.walltime
                    ),
                )
        return None

    def has_limits(self):
        has_output_limit = self.app.job_config.limits.output_size and self.app.job_config.limits.output_size > 0
        has_walltime_limit = self.app.job_config.limits.walltime_delta is not None
        return has_output_limit or has_walltime_limit

    def get_command_line(self):
        """Return complete command line, including possible version command."""
        if self.remote_command_line:
            return None
        return f'{self.version_command_line or ""}{self.command_line}'

    def get_session_id(self):
        return self.session_id

    def get_env_setup_clause(self):
        if self.app.config.environment_setup_file is None:
            return ""
        return f'[ -f "{self.app.config.environment_setup_file}" ] && . {self.app.config.environment_setup_file}'

    @property
    def object_store(self):
        return self.app.object_store

    @property
    def tmp_dir_creation_statement(self):
        tmp_dir = self.get_destination_configuration("tmp_dir", None)
        try:
            if not tmp_dir or util.asbool(tmp_dir):
                working_directory = self.working_directory
                return f"""$([ ! -e '{working_directory}/tmp' ] || mv '{working_directory}/tmp' '{working_directory}'/tmp.$(date +%Y%m%d-%H%M%S) ; mkdir '{working_directory}/tmp'; echo '{working_directory}/tmp')"""
            else:
                return tmp_dir
        except ValueError:
            # Catch case where tmp_dir is a complex expression and not a boolean value
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
            raise Exception(f"Unknown target type [{target}]")

    def get_tool_provided_job_metadata(self):
        if self.tool_provided_job_metadata is None:
            self.tool_provided_job_metadata = self.tool.tool_provided_metadata(self)
        return self.tool_provided_job_metadata

    def get_dataset_finish_context(self, job_context, output_dataset_assoc):
        meta = {}
        tool_provided_metadata = self.get_tool_provided_job_metadata()
        dataset = output_dataset_assoc.dataset.dataset
        meta = tool_provided_metadata.get_dataset_meta(output_dataset_assoc.name, dataset.id, dataset.uuid)
        if meta:
            return ExpressionContext(meta, job_context)
        return job_context

    def setup_external_metadata(
        self,
        exec_dir=None,
        tmp_dir=None,
        dataset_files_path=None,
        config_root=None,
        config_file=None,
        datatypes_config=None,
        resolve_metadata_dependencies=False,
        set_extension=True,
        **kwds,
    ):
        # extension could still be 'auto' if this is the upload tool.
        job = self.get_job()
        if set_extension:
            for output_dataset_assoc in job.output_datasets:
                if output_dataset_assoc.dataset.ext == "auto":
                    context = self.get_dataset_finish_context({}, output_dataset_assoc)
                    output_dataset_assoc.dataset.extension = context.get("ext", "data")
            with transaction(self.sa_session):
                self.sa_session.commit()
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
            datatypes_config = os.path.join(self.working_directory, "metadata", "registry.xml")
            safe_makedirs(os.path.join(self.working_directory, "metadata"))
            self.app.datatypes_registry.to_xml_file(path=datatypes_config)

        inp_data, out_data, out_collections = job.io_dicts(exclude_implicit_outputs=True)

        required_user_object_store_uris = set()
        for out_dataset_instance in out_data.values():
            object_store_id = out_dataset_instance.dataset.object_store_id
            if object_store_id and object_store_id.startswith("user_objects://"):
                required_user_object_store_uris.add(object_store_id)

        job_metadata = os.path.join(self.tool_working_directory, self.tool.provided_metadata_file)
        object_store_conf = serialize_static_object_store_config(self.object_store, required_user_object_store_uris)
        command = self.external_output_metadata.setup_external_metadata(
            out_data,
            out_collections,
            self.sa_session,
            exec_dir=exec_dir,
            tmp_dir=tmp_dir,
            dataset_files_path=dataset_files_path,
            config_root=config_root,
            config_file=config_file,
            datatypes_config=datatypes_config,
            job_metadata=job_metadata,
            provided_metadata_style=self.tool.provided_metadata_style,
            object_store_conf=object_store_conf,
            tool=self.tool,
            job=job,
            max_metadata_value_size=self.app.config.max_metadata_value_size,
            max_discovered_files=self.app.config.max_discovered_files,
            validate_outputs=self.validate_outputs,
            link_data_only=self.__link_file_check(),
            **kwds,
        )
        if resolve_metadata_dependencies:
            metadata_tool = self.app.toolbox.get_tool("__SET_METADATA__")
            if metadata_tool is not None:
                # Due to tool shed hacks for migrate and installed tool tests...
                # see (``setup_shed_tools_for_test`` in test/base/driver_util.py).
                dependency_shell_commands = metadata_tool.build_dependency_shell_commands(
                    job_directory=self.working_directory, metadata=True
                )
                if dependency_shell_commands:
                    dependency_shell_commands = "; ".join(dependency_shell_commands)
                    command = f"{dependency_shell_commands}; {command}"
        return command

    def check_for_entry_points(self, check_already_configured=True):
        if not self.tool.produces_entry_points:
            return True

        job = self.get_job()
        if check_already_configured and job.all_entry_points_configured:
            return True

        working_directory = self.working_directory
        container_runtime_path = os.path.join(working_directory, "container_runtime.json")
        if os.path.exists(container_runtime_path):
            with open(container_runtime_path) as f:
                try:
                    container_runtime = json.load(f)
                except ValueError:
                    # File exists, but is not fully populated yet
                    return False
            log.debug(f"found container runtime {container_runtime}")
            self.app.interactivetool_manager.configure_entry_points(job, container_runtime)
            return True
        container_exception_path = os.path.join(working_directory, "container_monitor_exception.txt")
        if os.path.exists(container_exception_path):
            with open(container_exception_path) as fh:
                exception_string = fh.read()
            error_message = "Monitoring interactive tool entry point failed"
            log.error(f"Monitoring interactive tool entry point for job {self.job_id} failed: {exception_string}")
            self.fail(error_message)
            # local job runner uses return value to determine if we're done polling
            return True

    def container_monitor_command(self, container, **kwds):
        if (
            not container
            or not self.tool.produces_entry_points
            or not self.get_destination_configuration("container_monitor", True)
        ):
            return None

        exec_dir = kwds.get("exec_dir", os.path.abspath(os.getcwd()))
        monitor_command = self.get_destination_configuration("container_monitor_command")
        get_ip_method = self.get_destination_configuration("container_monitor_get_ip_method")
        work_dir = self.working_directory
        configs_dir = ensure_configs_directory(work_dir)
        container_config = os.path.join(configs_dir, "container_config.json")
        self.extra_filenames.append(container_config)

        # What should be done with the result... 'file' or 'callback'
        result = self.get_destination_configuration("container_monitor_result", "file")
        galaxy_url = self.galaxy_url
        container_config_dict = {
            "container_name": container.container_name,
            "container_type": container.container_type,
            "connection_configuration": container.connection_configuration,
        }
        if result == "callback":
            job_id = self.job_id
            encoded_job_id = self.app.security.encode_id(job_id)
            job_key = self.app.security.encode_id(job_id, kind="jobs_files")
            endpoint_base = "%s/api/jobs/%s/ports?job_key=%s"
            callback_url = endpoint_base % (galaxy_url, encoded_job_id, job_key)
            container_config_dict["callback_url"] = callback_url

        if get_ip_method:
            assert get_ip_method.startswith("command:"), f"Unsupported get_ip_method: {get_ip_method}"
            container_config_dict["get_ip_method"] = get_ip_method

        with open(container_config, "w") as f:
            json.dump(container_config_dict, f)

        if not monitor_command:
            _monitor_py = shlex.quote(os.path.join(exec_dir, "lib/galaxy_ext/container_monitor/monitor.py"))
            monitor_command = f"python {_monitor_py}"
        return f"({monitor_command} &); sleep 1 "

    @property
    def user(self):
        job = self.get_job()
        if user_email := job.get_user_email():
            return user_email
        elif job.galaxy_session is not None:
            return f"anonymous@{job.galaxy_session.remote_addr.split()[-1]}"
        else:
            return "anonymous@unknown"

    def __update_output(self, job, hda, clean_only=False):
        """Handle writing outputs to the object store.

        This should be called regardless of whether the job was failed or not so
        that writing of partial results happens and so that the object store is
        cleaned up if the dataset has been purged.
        """
        dataset = hda.dataset
        dataset.set_total_size()
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
        """outputs_to_working_directory breaks library uploads where data is
        linked.  This method is a hack that solves that problem, but is
        specific to the upload tool and relies on an injected job param.  This
        method should be removed ASAP and replaced with some properly generic
        and stateful way of determining link-only datasets. -nate
        """
        if self.tool and self.tool.id == "upload1":
            job = self.get_job()
            param_dict = job.get_param_values(self.app)
            return param_dict.get("link_data_only") == "link_to_files"
        else:
            # The tool is unavailable, we try to move the outputs.
            return False

    def change_ownership_for_run(self):
        job = self.get_job()
        external_chown_script = self.get_destination_configuration("external_chown_script", None)
        if job.user is not None and external_chown_script:
            ret = external_chown(
                self.working_directory, self.user_system_pwent, external_chown_script, description="working directory"
            )
            if not ret:
                os.chmod(self.working_directory, RWXRWXRWX)

    def reclaim_ownership(self):
        job = self.get_job()
        external_chown_script = self.get_destination_configuration("external_chown_script", None)
        if job.user is not None and external_chown_script:
            external_chown(
                self.working_directory, self.galaxy_system_pwent, external_chown_script, description="working directory"
            )

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
        just copy these files directly to the ultimate destination.
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

    def set_container(self, container):
        if container:
            cont = model.JobContainerAssociation(
                job=self.get_job(),
                container_type=container.container_type,
                container_name=container.container_name,
                container_info=container.container_info,
            )
            self.sa_session.add(cont)
            with transaction(self.sa_session):
                self.sa_session.commit()


class JobWrapper(MinimalJobWrapper):
    def __init__(self, job, queue: "JobHandlerQueue", use_persisted_destination=False):
        app = queue.app
        super().__init__(
            job,
            app=app,
            use_persisted_destination=use_persisted_destination,
            tool=app.toolbox.get_tool(job.tool_id, job.tool_version, exact=True),
        )
        self.queue = queue
        self.job_runner_mapper = JobRunnerMapper(self, queue.dispatcher.url_to_destination, self.app.job_config)
        if use_persisted_destination:
            self.job_runner_mapper.cached_job_destination = JobDestination(from_job=job)

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

    def set_job_destination(self, job_destination, external_id=None, flush=True, job=None):
        """
        Persist job destination params in the database for recovery.

        self.job_destination is not used because a runner may choose to rewrite
        parts of the destination (e.g. the params).
        """
        if job is None:
            job = self.get_job()
        log.debug(f"({job.id}) Persisting job destination (destination id: {job_destination.id})")
        job.destination_id = job_destination.id
        job.destination_params = job_destination.params
        job.job_runner_name = job_destination.runner
        job.job_runner_external_id = external_id
        self.sa_session.add(job)
        if flush:
            with transaction(self.sa_session):
                self.sa_session.commit()


class TaskWrapper(JobWrapper):
    """
    Extension of JobWrapper intended for running tasks.
    Should be refactored into a generalized executable unit wrapper parent, then jobs and tasks.
    """

    # Abstract this to be more useful for running tasks that *don't* necessarily compose a job.

    is_task = True

    def __init__(self, task, queue):
        self.task_id = task.id
        super().__init__(task.job, queue)
        if task.prepare_input_files_cmd is not None:
            self.prepare_input_files_cmds = [task.prepare_input_files_cmd]
        else:
            self.prepare_input_files_cmds = None
        self.status = task.states.NEW

    def can_split(self):
        # Should the job handler split this job up? TaskWrapper should
        # always return False as the job has already been split.
        return False

    def get_job(self):
        if self.job_id:
            return self.sa_session.get(Job, self.job_id)
        else:
            return None

    def get_task(self):
        return self.sa_session.get(Task, self.task_id)

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

        with transaction(self.sa_session):
            self.sa_session.commit()

        if not self.remote_command_line:
            (
                self.command_line,
                self.version_command_line,
                extra_filenames,
                self.environment_variables,
                *_,
            ) = tool_evaluator.build()
            self.extra_filenames.extend(extra_filenames)

        # Ensure galaxy_lib_dir is set in case there are any later chdirs
        self.galaxy_lib_dir  # noqa: B018

        # We need command_line persisted to the db in order for Galaxy to re-queue the job
        # if the server was stopped and restarted before the job finished
        task.command_line = self.command_line
        self.sa_session.add(task)
        with transaction(self.sa_session):
            self.sa_session.commit()

        self.status = "prepared"
        return self.extra_filenames

    def fail(
        self, message, exception=False, tool_stdout="", tool_stderr="", exit_code=None, job_stdout=None, job_stderr=None
    ):
        log.error(f"TaskWrapper Failure {message}")
        self.status = "error"
        super().fail(
            message,
            exception=exception,
            tool_stdout=tool_stdout,
            tool_stderr=tool_stderr,
            exit_code=exit_code,
            job_stdout=job_stdout,
            job_stderr=job_stderr,
        )
        # How do we want to handle task failure?  Fail the job and let it clean up?

    def change_state(self, state, info=False, flush=True, job=None):
        task = self.get_task()
        self.sa_session.refresh(task)
        if info:
            task.info = info
        task.state = state
        self.sa_session.add(task)
        with transaction(self.sa_session):
            self.sa_session.commit()

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
        with transaction(self.sa_session):
            self.sa_session.commit()

    def finish(self, stdout, stderr, tool_exit_code=None, **kwds):
        # DBTODO integrate previous finish logic.
        # Simple finish for tasks.  Just set the flag OK.
        """
        Called to indicate that the associated command has been run. Updates
        the output datasets based on stderr and stdout from the command, and
        the contents of the output files.
        """

        # This may have ended too soon
        log.debug(
            "task %s for job %d ended; exit code: %d"
            % (self.task_id, self.job_id, tool_exit_code if tool_exit_code is not None else -256)
        )
        # default post job setup_external_metadata
        task = self.get_task()
        # if the job was deleted, don't finish it
        if task.state == task.states.DELETED:
            # Job was deleted by an administrator
            delete_files = self.cleanup_job in ("always", "onsuccess")
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
        with transaction(self.sa_session):
            self.sa_session.commit()

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

    def setup_external_metadata(
        self,
        exec_dir=None,
        tmp_dir=None,
        dataset_files_path=None,
        config_root=None,
        config_file=None,
        datatypes_config=None,
        set_extension=True,
        **kwds,
    ):
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


class NoopQueue:
    """
    Implements the JobQueue / JobStopQueue interface but does nothing
    """

    def put(self, *args, **kwargs):
        return

    def put_stop(self, *args):
        return

    def shutdown(self):
        return


__all__ = (
    "JobDestination",
    "NoopQueue",
    "JobToolConfiguration",
    "JobConfiguration",
    "JobWrapper",
    "TaskWrapper",
    "TOOL_PROVIDED_JOB_METADATA_FILE",
)
