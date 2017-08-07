"""This module defines the error reporting framework for Galaxy jobs.
"""
import collections
import logging
import os

from galaxy.util import plugin_config

log = logging.getLogger(__name__)


class ErrorReports(object):
    """Load and store a collection of :class:`ErrorPlugin` objects."""

    def __init__(self, conf_file=None, **kwargs):
        """Load :class:`ErrorPlugin` objects from specified configuration file."""
        self.plugin_classes = self.__plugins_dict()
        self.default_error_plugin = ErrorPlugin.from_file(self.plugin_classes, conf_file, **kwargs)
        self.error_plugin = collections.defaultdict(lambda: self.default_error_plugin)

    def __plugins_dict(self):
        import galaxy.tools.error_reports.plugins
        return plugin_config.plugins_dict(galaxy.tools.error_reports.plugins, 'plugin_type')


class NullErrorPlugin(object):

    def submit_report(self, dataset, job, tool, **kwargs):
        return "Submitted Bug Report"


NULL_ERROR_PLUGIN = NullErrorPlugin()


class ErrorPlugin(object):

    def __init__(self, plugin_classes, plugins_source, **kwargs):
        self.extra_kwargs = kwargs
        self.app = kwargs['app']
        self.plugin_classes = plugin_classes
        self.plugins = self.__plugins_from_source(plugins_source)

    def _can_access_dataset(self, dataset, user):
        if user:
            roles = user.all_roles()
        else:
            roles = []
        return self.app.security_agent.can_access_dataset(roles, dataset.dataset)

    def submit_report(self, dataset, job, tool, user=None, user_submission=False, **kwargs):
        if user_submission:
            assert self._can_access_dataset(dataset, user), Exception("You are not allowed to access this dataset.")

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
            return NULL_ERROR_PLUGIN
        plugins_source = plugin_config.plugin_source_from_path(conf_file)
        return ErrorPlugin(plugin_classes, plugins_source, **kwargs)
