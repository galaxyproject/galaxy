"""
Lower level of visualization framework which does three main things:
    - associate visualizations with objects
    - create urls to visualizations based on some target object(s)
    - unpack a query string into the desired objects needed for rendering
"""

import logging
import os
import weakref

import galaxy.model
from galaxy.exceptions import ObjectNotFound
from galaxy.util import (
    config_directories_from_setting,
    parse_xml,
)
from galaxy.visualization.plugins import (
    config_parser,
    plugin as vis_plugins,
)
from galaxy.visualization.plugins.datasource_testing import is_object_applicable

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

    # -- building links to visualizations from objects --
    def get_visualizations(self, trans, target_object=None, embeddable=None):
        """
        Get the names of visualizations usable on the `target_object` and
        the urls to call in order to render the visualizations.
        """
        result = []
        for vis_name, vis_plugin in self.plugins.items():
            if vis_plugin.config.get("hidden"):
                continue
            if embeddable and not vis_plugin.config.get("embeddable"):
                continue
            if target_object is not None and self.get_visualization(trans, vis_name, target_object) is None:
                continue
            result.append(vis_plugin.to_dict())
        return sorted(result, key=lambda k: k.get("html"))

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
                model_class = getattr(galaxy.model, model_class, None)
                if isinstance(target_object, model_class):
                    tests = data_source["tests"]
                    if tests is None or is_object_applicable(trans, target_object, tests):
                        return visualization.to_dict()
