"""
Lower level of visualization framework which does three main things:
    - associate visualizations with objects
    - create urls to visualizations based on some target object(s)
    - unpack a query string into the desired objects needed for rendering
"""

import logging
import os
import weakref
from typing import (
    List,
    Optional,
)

from galaxy.exceptions import ObjectNotFound
from galaxy.util import (
    config_directories_from_setting,
    parse_xml,
)
from galaxy.visualization.plugins import (
    config_parser,
    plugin as vis_plugins,
)

log = logging.getLogger(__name__)


class VisualizationsRegistry:
    """
    Main responsibilities are:
        - discovering visualization plugins in the filesystem
        - testing if an object has a visualization that can be applied to it
        - generating a link to controllers.visualization.render with
            the appropriate params
        - validating and parsing params into resources (based on a context)
            used in the visualization template
    """

    #: base url to controller endpoint
    BASE_URL = "visualizations"
    #: name of files to search for additional template lookup directories
    TEMPLATE_PATHS_CONFIG = "additional_template_paths.xml"
    #: built-in visualizations
    BUILT_IN_VISUALIZATIONS = ["trackster", "circster", "sweepster", "phyloviz"]

    def __str__(self):
        return self.__class__.__name__

    def __init__(self, app, template_cache_dir=None, directories_setting=None, skip_bad_plugins=True, **kwargs):
        """
        Set up the manager and load all visualization plugins.

        :type   app:        galaxy.app.UniverseApplication
        :param  app:        the application (and its configuration) using this manager
        :type   base_url:   string
        :param  base_url:   url to prefix all plugin urls with
        :type   template_cache_dir: string
        :param  template_cache_dir: filesytem path to the directory where cached
            templates are kept
        """
        self.app = weakref.ref(app)
        self.config_parser = config_parser.VisualizationsConfigParser()
        self.base_url = self.BASE_URL
        self.template_cache_dir = template_cache_dir
        self.additional_template_paths = []
        self.directories = []
        self.skip_bad_plugins = skip_bad_plugins
        self.plugins = {}
        self.directories = config_directories_from_setting(directories_setting, app.config.root)
        self._load_configuration()
        self._load_plugins()

    def _load_configuration(self):
        """
        Load framework wide configuration, including:
            additional template lookup directories
        """
        for directory in self.directories:
            possible_path = os.path.join(directory, self.TEMPLATE_PATHS_CONFIG)
            if os.path.exists(possible_path):
                added_paths = self._parse_additional_template_paths(possible_path, directory)
                self.additional_template_paths.extend(added_paths)

    def _parse_additional_template_paths(self, config_filepath, base_directory):
        """
        Parse an XML config file at `config_filepath` for template paths
        (relative to `base_directory`) to add to each plugin's template lookup.

        Allows having a set of common templates for import/inheritance in
        plugin templates.

        :type   config_filepath:    string
        :param  config_filepath:    filesystem path to the config file
        :type   base_directory:     string
        :param  base_directory:     path prefixed to new, relative template paths
        """
        additional_paths = []
        xml_tree = parse_xml(config_filepath)
        paths_list = xml_tree.getroot()
        for rel_path_elem in paths_list.findall("path"):
            if rel_path_elem.text is not None:
                additional_paths.append(os.path.join(base_directory, rel_path_elem.text))
        return additional_paths

    def _load_plugins(self):
        """
        Search ``self.directories`` for potential plugins, load them, and cache
        in ``self.plugins``.
        """
        for plugin_path in self._find_plugins():
            try:
                plugin = self._load_plugin(plugin_path)
                if plugin and plugin.name not in self.plugins:
                    self.plugins[plugin.name] = plugin
                    log.info("%s, loaded plugin: %s", self, plugin.name)
                elif plugin and plugin.name in self.plugins:
                    log.warning("%s, plugin with name already exists: %s. Skipping...", self, plugin.name)
            except Exception:
                if not self.skip_bad_plugins:
                    raise
                log.exception("Plugin loading raised exception: %s. Skipping...", plugin_path)
        return self.plugins

    def _find_plugins(self):
        """
        Return the directory paths of plugins within ``self.directories``.

        Paths are considered a plugin path if they pass ``self.is_plugin``.
        :rtype:                 string generator
        :returns:               paths of valid plugins
        """
        # due to the ordering of listdir, there is an implicit plugin loading order here
        # could instead explicitly list on/off in master config file
        for directory in self.directories:
            for plugin_dir in sorted(os.listdir(directory)):
                plugin_path = os.path.join(directory, plugin_dir)
                if self._is_plugin(plugin_path):
                    yield plugin_path
                if os.path.isdir(plugin_path):
                    for plugin_subdir in sorted(os.listdir(plugin_path)):
                        plugin_subpath = os.path.join(plugin_path, plugin_subdir)
                        if self._is_plugin(plugin_subpath):
                            yield plugin_subpath

    # TODO: add fill_template fn that is able to load extra libraries beforehand (and remove after)
    # TODO: add template helpers specific to the plugins
    # TODO: some sort of url_for for these plugins
    def _is_plugin(self, plugin_path):
        """
        Determines whether the given filesystem path contains a plugin.

        In this base class, all sub-directories are considered plugins.

        :type   plugin_path:    string
        :param  plugin_path:    relative or absolute filesystem path to the
            potential plugin
        :rtype:                 bool
        :returns:               True if the path contains a plugin
        """
        # plugin_path must be a directory, have a config dir, and a config file matching the plugin dir name
        if not os.path.isdir(plugin_path):
            # super won't work here - different criteria
            return False
        if "config" not in os.listdir(plugin_path):
            return False
        expected_config_filename = f"{os.path.split(plugin_path)[1]}.xml"
        if not os.path.isfile(os.path.join(plugin_path, "config", expected_config_filename)):
            return False
        return True

    def _load_plugin(self, plugin_path):
        """
        Create the visualization plugin object, parse its configuration file,
        and return it.

        :type   plugin_path:    string
        :param  plugin_path:    relative or absolute filesystem path to the plugin
        :rtype:                 ``VisualizationPlugin``
        :returns:               the loaded plugin
        """
        plugin_name = os.path.split(plugin_path)[1]
        # TODO: this is the standard/older way to config
        config_file = os.path.join(plugin_path, "config", (f"{plugin_name}.xml"))
        if os.path.exists(config_file):
            config = self.config_parser.parse_file(config_file)
            if config is not None:
                # config may be none if the visualization is disabled
                plugin = self._build_plugin(plugin_name, plugin_path, config)
                return plugin
        else:
            raise ObjectNotFound(f"Visualization XML not found: {config_file}.")

    def _build_plugin(self, plugin_name, plugin_path, config):
        # TODO: as builder not factory

        # default class
        plugin_class = vis_plugins.VisualizationPlugin
        # js only
        if config["entry_point"]["type"] == "script":
            plugin_class = vis_plugins.ScriptVisualizationPlugin
        # js only using charts environment
        elif config["entry_point"]["type"] == "chart":
            plugin_class = vis_plugins.ChartVisualizationPlugin
        # from a static file (html, etc)
        elif config["entry_point"]["type"] == "html":
            plugin_class = vis_plugins.StaticFileVisualizationPlugin
        return plugin_class(
            self.app(),
            plugin_path,
            plugin_name,
            config,
            context=dict(
                base_url=self.base_url,
                template_cache_dir=self.template_cache_dir,
                additional_template_paths=self.additional_template_paths,
            ),
        )

    def get_plugin(self, key):
        """
        Wrap to throw error if plugin not in registry.
        """
        if key not in self.plugins:
            raise ObjectNotFound(f"Unknown or invalid visualization: {key}")
        return self.plugins[key]

    def get_plugins(self, embeddable=None):
        result = []
        for plugin in self.plugins.values():
            if embeddable and not plugin.config.get("embeddable"):
                continue
            result.append(plugin.to_dict())
        return sorted(result, key=lambda k: k.get("html"))

    # -- building links to visualizations from objects --
    def get_visualizations(self, trans, target_object):
        """
        Get the names of visualizations usable on the `target_object` and
        the urls to call in order to render the visualizations.
        """
        applicable_visualizations = []
        for vis_name in self.plugins:
            url_data = self.get_visualization(trans, vis_name, target_object)
            if url_data:
                applicable_visualizations.append(url_data)
        return sorted(applicable_visualizations, key=lambda k: k.get("html"))

    def get_visualization(self, trans, visualization_name, target_object):
        """
        Return data to build a url to the visualization with the given
        `visualization_name` if it's applicable to `target_object` or
        `None` if it's not.
        """
        if (visualization := self.plugins.get(visualization_name, None)) is not None:
            data_sources = visualization.config["data_sources"]
            for data_source in data_sources:
                model_class = data_source["model_class"]
                if isinstance(target_object, model_class):
                    tests = data_source["tests"]
                    if tests is None or self.is_object_applicable(trans, target_object, tests):
                        return visualization.to_dict()

    def is_object_applicable(self, trans, target_object, data_source_tests):
        """
        Run a visualization's data_source tests to find out if
        it can be applied to the target_object.
        """
        # log.debug( 'is_object_applicable( self, trans, %s, %s )', target_object, data_source_tests )
        for test in data_source_tests:
            test_type = test["type"]
            result_type = test["result_type"]
            test_result = test["result"]
            test_fn = test["fn"]
            supported_protocols = test.get("allow_uri_if_protocol", [])
            # log.debug( '%s %s: %s, %s, %s, %s', str( target_object ), 'is_object_applicable',
            #           test_type, result_type, test_result, test_fn )

            if test_type == "isinstance":
                # parse test_result based on result_type (curr: only datatype has to do this)
                if result_type == "datatype":
                    # convert datatypes to their actual classes (for use with isinstance)
                    datatype_class_name = test_result
                    test_result = trans.app.datatypes_registry.get_datatype_class_by_name(datatype_class_name)
                    if not test_result:
                        # but continue (with other tests) if can't find class by that name
                        # if self.debug:
                        #    log.warning( 'visualizations_registry cannot find class (%s)' +
                        #              ' for applicability test on: %s, id: %s', datatype_class_name,
                        #              target_object, getattr( target_object, 'id', '' ) )
                        continue

            # NOTE: tests are OR'd, if any test passes - the visualization can be applied
            if test_fn(target_object, test_result) and self._check_uri_support(target_object, supported_protocols):
                # log.debug( '\t test passed' )
                return True

        return False

    def _is_deferred(self, target_object) -> bool:
        """Whether the target object is a deferred object."""
        return getattr(target_object, "state", None) == "deferred"

    def _deferred_source_uri(self, target_object) -> Optional[str]:
        """Get the source uri from a deferred object."""
        sources = getattr(target_object, "sources", None)
        if sources and sources[0]:
            return sources[0].source_uri
        return None

    def _check_uri_support(self, target_object, supported_protocols: List[str]) -> bool:
        """Test if the target object is deferred and has a supported protocol."""
        if not self._is_deferred(target_object):
            return True  # not deferred, so no uri to check

        if not supported_protocols:
            return False  # no protocols defined, means no support for deferred objects

        if "*" in supported_protocols:
            return True  # wildcard support for all protocols

        deferred_source_uri = self._deferred_source_uri(target_object)
        if deferred_source_uri:
            protocol = deferred_source_uri.split("://")[0]
            return protocol in supported_protocols
        return False
