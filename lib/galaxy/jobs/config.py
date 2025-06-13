import copy
import datetime
import logging
import os
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
)

import yaml

from galaxy import util
from galaxy.jobs.runners import BaseJobRunner
from galaxy.structured_app import MinimalManagerApp
from galaxy.tool_util.deps import requirements
from galaxy.util import (
    parse_xml_string,
    unicodify,
)
from galaxy.util.bunch import Bunch
from galaxy.util.xml_macros import load
from galaxy.web_stack.handlers import ConfiguresHandlers

log = logging.getLogger(__name__)

DEFAULT_LOCAL_WORKERS = 4
VALID_TOOL_CLASSES = ["local", "requires_galaxy"]


def config_exception(e, file):
    abs_path = os.path.abspath(file)
    message = f"Problem parsing file '{abs_path}', "
    message += "please correct the indicated portion of the file and restart Galaxy. "
    message += unicodify(e)
    log.exception(message)
    return Exception(message)


def job_config_dict_from_xml_or_yaml(job_config_file: str):
    if ".xml" in job_config_file:
        tree = load(job_config_file)
        job_config_dict = JobConfiguration.__parse_job_conf_xml(tree)
    else:
        with open(job_config_file) as f:
            job_config_dict = yaml.safe_load(f)
    return job_config_dict


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


@dataclass
class JobConfigurationLimits:
    registered_user_concurrent_jobs: Optional[int] = None
    anonymous_user_concurrent_jobs: Optional[int] = None
    walltime: Optional[str] = None
    walltime_delta: Optional[datetime.timedelta] = None
    total_walltime: Dict[str, Any] = field(default_factory=dict)
    output_size: Optional[int] = None
    destination_user_concurrent_jobs: Dict[str, int] = field(default_factory=dict)
    destination_total_concurrent_jobs: Dict[str, int] = field(default_factory=dict)


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
        self.limits = JobConfigurationLimits()

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
                if not job_config_file:
                    raise OSError()

                job_config_dict = job_config_dict_from_xml_or_yaml(job_config_file)
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
        environments_list = list(
            ((e["id"], e) for e in environments) if isinstance(environments, list) else environments.items()
        )
        for _, environment_dict in environments_list:
            runner = environment_dict.get("runner")
            if runner == "dynamic_tpv":
                environment_dict["runner"] = "dynamic"
                environment_dict["type"] = "python"
                environment_dict["function"] = "map_tool_to_destination"
                environment_dict["rules_module"] = "tpv.rules"

        for environment_id, environment_dict in environments_list:
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

    @classmethod
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
