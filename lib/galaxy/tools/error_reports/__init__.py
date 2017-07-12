"""This module defines the error reporting framework for Galaxy jobs.
"""
import collections
import logging
import os

from galaxy.util import plugin_config

log = logging.getLogger(__name__)


class ErrorReports(object):
    """Load and store a collection of :class:`ErrorSink` objects."""

    def __init__(self, conf_file=None, **kwargs):
        """Load :class:`ErrorSink` objects from specified configuration file."""
        self.plugin_classes = self.__plugins_dict()
        self.default_error_sink = ErrorSink.from_file(self.plugin_classes, conf_file, **kwargs)
        self.error_sinks = collections.defaultdict(lambda: self.default_error_sink)

    def __plugins_dict(self):
        import galaxy.tools.error_reports.sinks
        return plugin_config.plugins_dict(galaxy.tools.error_reports.sinks, 'plugin_type')


class NullErrorSink(object):

    def submit_report(self, dataset, job, tool, **kwargs):
        return "Submitted Bug Report"


NULL_ERROR_SINK = NullErrorSink()


class ErrorSink(object):

    def __init__(self, plugin_classes, plugins_source, **kwargs):
        self.extra_kwargs = kwargs
        self.plugin_classes = plugin_classes
        self.plugins = self.__plugins_from_source(plugins_source)

    def submit_report(self, dataset, job, tool, user_submission=False, **kwargs):
        responses = []
        for plugin in self.plugins:
            if user_submission == plugin.user_submission:
                try:
                    response = plugin.submit_report(dataset, job, tool, **kwargs)
                    log.debug("Bug report plugin %s generated response %s", plugin, response)
                    if plugin.verbose and response:
                        responses.append(response)
                except Exception:
                    log.exception("Failed to generate submit_report commands for plugin %s", plugin)
        return responses

    def __plugins_from_source(self, plugins_source):
        return plugin_config.load_plugins(self.plugin_classes, plugins_source, self.extra_kwargs)

    @staticmethod
    def from_file(plugin_classes, conf_file, **kwargs):
        if not conf_file or not os.path.exists(conf_file):
            return NULL_ERROR_SINK
        plugins_source = plugin_config.plugin_source_from_path(conf_file)
        return ErrorSink(plugin_classes, plugins_source, **kwargs)
