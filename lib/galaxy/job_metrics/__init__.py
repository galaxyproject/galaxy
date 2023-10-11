"""This module defines the job metrics collection framework for Galaxy jobs.

The framework consists of two parts - the :class:`JobMetrics` class and
individual :class:`JobInstrumenter` plugins.

A :class:`JobMetrics` object reads any number of plugins from a configuration
source such as an XML file, a YAML file, or a dictionary.

Each :class:`JobInstrumenter` plugin object describes how to inject a bits
of shell code into a job scripts (before and after tool commands run) and then
collect the output of these from a job directory.
"""
import collections
import logging
import os
from abc import (
    ABCMeta,
    abstractmethod,
)
from typing import (
    Any,
    Dict,
    List,
    NamedTuple,
    Optional,
)

from galaxy import util
from galaxy.util import plugin_config
from . import formatting
from .safety import (
    DEFAULT_SAFETY,
    Safety,
)

log = logging.getLogger(__name__)


DEFAULT_FORMATTER = formatting.JobMetricFormatter()


class DictifiableMetric(NamedTuple):
    """The full context of a metric that is ready to be exposed to an external client."""

    title: str
    value: str
    raw_value: str
    name: str
    plugin: str
    safety: Safety = Safety.POTENTIALLY_SENSITVE

    def dict(self) -> Dict[str, str]:
        return dict(
            title=self.title,
            value=self.value,
            plugin=self.plugin,
            name=self.name,
            raw_value=self.raw_value,
        )


class RawMetric(NamedTuple):
    metric_name: str
    metric_value: Any
    metric_plugin: str


class JobMetrics:
    """Load and store a collection of :class:`JobInstrumenter` objects."""

    def __init__(self, conf_file=None, **kwargs):
        """Load :class:`JobInstrumenter` objects from specified configuration file."""
        self.plugin_classes = self.__plugins_dict()
        self.default_job_instrumenter = JobInstrumenter.from_file(self.plugin_classes, conf_file, **kwargs)
        self.job_instrumenters = collections.defaultdict(lambda: self.default_job_instrumenter)

    def format(self, plugin: str, key: str, value: Any) -> formatting.FormattedMetric:
        """Find :class:`formatting.JobMetricFormatter` corresponding to instrumented plugin value."""
        if plugin in self.plugin_classes:
            plugin_class = self.plugin_classes[plugin]
            formatter = plugin_class.formatter
        else:
            formatter = DEFAULT_FORMATTER
        return formatter.format(key, value)

    def dictifiable_metrics(self, raw_metrics: List[RawMetric], allowed_safety: Safety) -> List[DictifiableMetric]:
        def raw_to_dictifiable(raw_metric: RawMetric) -> DictifiableMetric:
            metric_name, metric_value, metric_plugin = raw_metric
            title, value = self.format(metric_plugin, metric_name, metric_value)
            configured_plugin = self.default_job_instrumenter.get_configured_plugin(metric_plugin)
            if configured_plugin is not None:
                safety = configured_plugin.safety(metric_name)
            elif metric_plugin in self.plugin_classes:
                plugin_class = self.plugin_classes[metric_plugin]
                safety = plugin_class.default_safety
            else:
                safety = DEFAULT_SAFETY
            return DictifiableMetric(
                title,
                value,
                str(metric_value),
                metric_name,
                metric_plugin,
                safety,
            )

        metrics = map(raw_to_dictifiable, raw_metrics)
        return [m for m in metrics if m.safety.value >= allowed_safety.value]

    def set_destination_conf_file(self, destination_id, conf_file):
        instrumenter = JobInstrumenter.from_file(self.plugin_classes, conf_file)
        self.set_destination_instrumenter(destination_id, instrumenter)

    def set_destination_conf_element(self, destination_id, element):
        plugin_source = plugin_config.PluginConfigSource("xml", element)
        instrumenter = JobInstrumenter(self.plugin_classes, plugin_source)
        self.set_destination_instrumenter(destination_id, instrumenter)

    def set_destination_conf_dicts(self, destination_id, conf_dicts):
        plugin_source = plugin_config.PluginConfigSource("dict", conf_dicts)
        instrumenter = JobInstrumenter(self.plugin_classes, plugin_source)
        self.set_destination_instrumenter(destination_id, instrumenter)

    def set_destination_instrumenter(self, destination_id, job_instrumenter=None):
        if job_instrumenter is None:
            job_instrumenter = NULL_JOB_INSTRUMENTER
        self.job_instrumenters[destination_id] = job_instrumenter

    def collect_properties(self, destination_id, job_id, job_directory):
        return self.job_instrumenters[destination_id].collect_properties(job_id, job_directory)

    def __plugins_dict(self):
        import galaxy.job_metrics.instrumenters

        return plugin_config.plugins_dict(galaxy.job_metrics.instrumenters, "plugin_type")


class JobInstrumenterI(metaclass=ABCMeta):
    @abstractmethod
    def pre_execute_commands(self, job_directory: str) -> Optional[str]:
        return None

    @abstractmethod
    def post_execute_commands(self, job_directory: str) -> Optional[str]:
        return None

    @abstractmethod
    def collect_properties(self, job_id, job_directory: str) -> Dict[str, Any]:
        return {}

    @abstractmethod
    def get_configured_plugin(self, plugin_type: str):
        return None


class NullJobInstrumenter(JobInstrumenterI):
    def pre_execute_commands(self, job_directory):
        return None

    def post_execute_commands(self, job_directory):
        return None

    def collect_properties(self, job_id, job_directory):
        return {}

    def get_configured_plugin(self, plugin_type: str):
        return None


NULL_JOB_INSTRUMENTER = NullJobInstrumenter()


class JobInstrumenter(JobInstrumenterI):
    def __init__(self, plugin_classes, plugins_source, **kwargs):
        self.extra_kwargs = kwargs
        self.plugin_classes = plugin_classes
        self.plugins = self.__plugins_from_source(plugins_source)

    def get_configured_plugin(self, plugin_type: str):
        for plugin in self.plugins:
            if plugin.plugin_type == plugin_type:
                return plugin
        return None

    def pre_execute_commands(self, job_directory):
        commands = []
        for plugin in self.plugins:
            try:
                plugin_commands = plugin.pre_execute_instrument(job_directory)
                if plugin_commands:
                    commands.extend(util.listify(plugin_commands))
            except Exception:
                log.exception("Failed to generate pre-execute commands for plugin %s", plugin)
        return "\n".join(c for c in commands if c)

    def post_execute_commands(self, job_directory):
        commands = []
        for plugin in self.plugins:
            try:
                plugin_commands = plugin.post_execute_instrument(job_directory)
                if plugin_commands:
                    commands.extend(util.listify(plugin_commands))
            except Exception:
                log.exception("Failed to generate post-execute commands for plugin %s", plugin)
        return "\n".join(c for c in commands if c)

    def collect_properties(self, job_id, job_directory):
        per_plugin_properties = {}
        for plugin in self.plugins:
            try:
                properties = plugin.job_properties(job_id, job_directory)
                if properties:
                    per_plugin_properties[plugin.plugin_type] = properties
            except FileNotFoundError as e:
                log.warning("Failed to collect job properties for plugin %s: %s", plugin, e)
            except Exception:
                log.exception("Failed to collect job properties for plugin %s", plugin)
        return per_plugin_properties

    def __plugins_from_source(self, plugins_source):
        return plugin_config.load_plugins(self.plugin_classes, plugins_source, self.extra_kwargs)

    @staticmethod
    def from_file(plugin_classes, conf_file, **kwargs) -> "JobInstrumenterI":
        if not conf_file or not os.path.exists(conf_file):
            return NULL_JOB_INSTRUMENTER
        plugins_source = plugin_config.plugin_source_from_path(conf_file)
        return JobInstrumenter(plugin_classes, plugins_source, **kwargs)


__all__ = (
    "JobInstrumenter",
    "Safety",
)
