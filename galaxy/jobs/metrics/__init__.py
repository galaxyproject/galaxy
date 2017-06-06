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

from galaxy import util
from galaxy.util import plugin_config

from ..metrics import formatting

log = logging.getLogger(__name__)


DEFAULT_FORMATTER = formatting.JobMetricFormatter()


class JobMetrics(object):
    """Load and store a collection of :class:`JobInstrumenter` objects."""

    def __init__(self, conf_file=None, **kwargs):
        """Load :class:`JobInstrumenter` objects from specified configuration file."""
        self.plugin_classes = self.__plugins_dict()
        self.default_job_instrumenter = JobInstrumenter.from_file(self.plugin_classes, conf_file, **kwargs)
        self.job_instrumenters = collections.defaultdict(lambda: self.default_job_instrumenter)

    def format(self, plugin, key, value):
        """Find :class:`formatting.JobMetricFormatter` corresponding to instrumented plugin value."""
        if plugin in self.plugin_classes:
            plugin_class = self.plugin_classes[ plugin ]
            formatter = plugin_class.formatter
        else:
            formatter = DEFAULT_FORMATTER
        return formatter.format(key, value)

    def set_destination_conf_file(self, destination_id, conf_file):
        instrumenter = JobInstrumenter.from_file(self.plugin_classes, conf_file)
        self.set_destination_instrumenter(destination_id, instrumenter)

    def set_destination_conf_element(self, destination_id, element):
        instrumenter = JobInstrumenter(self.plugin_classes, ('xml', element))
        self.set_destination_instrumenter(destination_id, instrumenter)

    def set_destination_instrumenter(self, destination_id, job_instrumenter=None):
        if job_instrumenter is None:
            job_instrumenter = NULL_JOB_INSTRUMENTER
        self.job_instrumenters[ destination_id ] = job_instrumenter

    def collect_properties(self, destination_id, job_id, job_directory):
        return self.job_instrumenters[ destination_id ].collect_properties(job_id, job_directory)

    def __plugins_dict(self):
        import galaxy.jobs.metrics.instrumenters
        return plugin_config.plugins_dict(galaxy.jobs.metrics.instrumenters, 'plugin_type')


class NullJobInstrumenter(object):

    def pre_execute_commands(self, job_directory):
        return None

    def post_execute_commands(self, job_directory):
        return None

    def collect_properties(self, job_id, job_directory):
        return {}


NULL_JOB_INSTRUMENTER = NullJobInstrumenter()


class JobInstrumenter(object):

    def __init__(self, plugin_classes, plugins_source, **kwargs):
        self.extra_kwargs = kwargs
        self.plugin_classes = plugin_classes
        self.plugins = self.__plugins_from_source(plugins_source)

    def pre_execute_commands(self, job_directory):
        commands = []
        for plugin in self.plugins:
            try:
                plugin_commands = plugin.pre_execute_instrument(job_directory)
                if plugin_commands:
                    commands.extend(util.listify(plugin_commands))
            except Exception:
                log.exception("Failed to generate pre-execute commands for plugin %s", plugin)
        return "\n".join([ c for c in commands if c ])

    def post_execute_commands(self, job_directory):
        commands = []
        for plugin in self.plugins:
            try:
                plugin_commands = plugin.post_execute_instrument(job_directory)
                if plugin_commands:
                    commands.extend(util.listify(plugin_commands))
            except Exception:
                log.exception("Failed to generate post-execute commands for plugin %s", plugin)
        return "\n".join([ c for c in commands if c ])

    def collect_properties(self, job_id, job_directory):
        per_plugin_properites = {}
        for plugin in self.plugins:
            try:
                properties = plugin.job_properties(job_id, job_directory)
                if properties:
                    per_plugin_properites[ plugin.plugin_type ] = properties
            except Exception:
                log.exception("Failed to collect job properties for plugin %s", plugin)
        return per_plugin_properites

    def __plugins_from_source(self, plugins_source):
        return plugin_config.load_plugins(self.plugin_classes, plugins_source, self.extra_kwargs)

    @staticmethod
    def from_file(plugin_classes, conf_file, **kwargs):
        if not conf_file or not os.path.exists(conf_file):
            return NULL_JOB_INSTRUMENTER
        plugins_source = plugin_config.plugin_source_from_path(conf_file)
        return JobInstrumenter(plugin_classes, plugins_source, **kwargs)
