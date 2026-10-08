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
    TYPE_CHECKING,
)

import galaxy.model
from galaxy.exceptions import ObjectNotFound
from galaxy.util import config_directories_from_setting
from galaxy.util.path import safe_contains
from galaxy.visualization.plugins import config_parser
from galaxy.visualization.plugins.datasource_testing import is_object_applicable
from galaxy.visualization.plugins.plugin import VisualizationPlugin

if TYPE_CHECKING:
    from galaxy.managers.context import ProvidesAppContext
    from galaxy.managers.visualization_admin import VisualizationPackageManager
    from galaxy.structured_app import StructuredApp

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

    #: base directory of visualizations
    BASE_DIR = "static/plugins/visualizations"
    #: base url to controller endpoint
    BASE_URL = "visualizations"

    def __str__(self):
        return self.__class__.__name__

    def __init__(
        self,
        app: "StructuredApp",
        directories_setting: str | None = None,
        skip_bad_plugins: bool = True,
        package_manager: "VisualizationPackageManager | None" = None,
    ) -> None:
        """
        Set up the manager and load all visualization plugins.

        :type   app:        galaxy.app.UniverseApplication
        :param  app:        the application (and its configuration) using this manager
        """
        self.app = weakref.ref(app)
        self.config_parser = config_parser.PluginConfigParser()
        self.base_url = self.BASE_URL
        self.skip_bad_plugins = skip_bad_plugins
        self.plugins: dict[str, VisualizationPlugin] = {}
        self.package_manager = package_manager
        self.directories = config_directories_from_setting(directories_setting, app.config.root)
        self.directories.append(os.path.join(app.config.root, self.BASE_DIR))
        self._load_plugins()

    def reload(self) -> None:
        """Rediscover plugins on disk, replacing the loaded set."""
        self._load_plugins()

    def _load_plugins(self):
        """
        Search ``self.directories`` for potential plugins, load them, and cache
        in ``self.plugins``.
        """
        # Build into a fresh dict and swap at the end so a reload never exposes a partial set
        plugins: dict[str, VisualizationPlugin] = {}
        for plugin_path in self._find_plugins():
            try:
                plugin = self._load_plugin(plugin_path)
                if plugin and plugin.name not in plugins:
                    plugins[plugin.name] = plugin
                    log.info("%s, loaded plugin: %s", self, plugin.name)
                elif plugin and plugin.name in plugins:
                    log.warning("%s, plugin with name already exists: %s. Skipping...", self, plugin.name)
            except Exception:
                if not self.skip_bad_plugins:
                    raise
                log.exception("Plugin loading raised exception: %s. Skipping...", plugin_path)
        if self.package_manager is not None:
            # Loaded straight from the package store (nothing is copied into static/, which may be
            # read-only) and they win over a built-in of the same name.
            for package_path in self.package_manager.get_enabled_packages().values():
                try:
                    plugin = self._load_plugin(package_path, runtime=True)
                    if plugin.name in plugins:
                        log.info("%s, runtime package overrides built-in plugin: %s", self, plugin.name)
                    plugins[plugin.name] = plugin
                except Exception:
                    if not self.skip_bad_plugins:
                        raise
                    log.exception("Runtime visualization package failed to load: %s. Skipping...", package_path)
        self.plugins = plugins
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
            if not os.path.isdir(directory):
                continue
            for plugin_dir in sorted(os.listdir(directory)):
                plugin_path = os.path.join(directory, plugin_dir)
                if self._is_plugin(plugin_path):
                    yield plugin_path
                if os.path.isdir(plugin_path):
                    for plugin_subdir in sorted(os.listdir(plugin_path)):
                        plugin_subpath = os.path.join(plugin_path, plugin_subdir)
                        if self._is_plugin(plugin_subpath):
                            yield plugin_subpath

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
        expected_config_filename = f"{os.path.basename(plugin_path)}.xml"
        return os.path.isfile(os.path.join(plugin_path, "static", expected_config_filename))

    def _load_plugin(self, plugin_path, runtime=False):
        """
        Create the visualization plugin object, parse its configuration file,
        and return it.

        :type   plugin_path:    string
        :param  plugin_path:    relative or absolute filesystem path to the plugin
        :rtype:                 ``VisualizationPlugin``
        :returns:               the loaded plugin
        """
        plugin_name = os.path.split(plugin_path)[1]
        config_file = os.path.join(plugin_path, "static", f"{plugin_name}.xml")
        if os.path.exists(config_file):
            config = self.config_parser.parse_file(config_file)
            if config is not None:
                app = self.app()
                url_prefix = app.config.galaxy_url_prefix.rstrip("/") if app is not None else ""
                if runtime:
                    # served by Galaxy itself, straight out of the package store
                    return VisualizationPlugin(
                        plugin_path,
                        plugin_name,
                        config,
                        url_prefix=url_prefix,
                        static_path=f"/api/plugins/{plugin_name}/static",
                        runtime=True,
                    )
                # built-ins are served from the copy the client build puts in Galaxy's static tree
                static_dir = os.path.join(app.config.root, self.BASE_DIR, plugin_name, "static") if app else None
                return VisualizationPlugin(
                    plugin_path, plugin_name, config, url_prefix=url_prefix, static_dir=static_dir
                )
        raise ObjectNotFound(f"Visualization XML not found in config or static paths for: {plugin_name}.")

    def get_plugin(self, key):
        """
        Wrap to throw error if plugin not in registry.
        """
        if key not in self.plugins:
            raise ObjectNotFound(f"Unknown or invalid visualization: {key}")
        return self.plugins[key]

    def get_runtime_static_file(self, name: str, file_path: str) -> str:
        """
        Return the filesystem path of a static file belonging to a runtime-installed package.

        Built-in plugins are served from Galaxy's static tree instead, so they aren't resolved here.
        """
        plugin = self.plugins.get(name)
        if plugin is None or not plugin.runtime:
            raise ObjectNotFound(f"Unknown runtime visualization: {name}")
        if os.path.isabs(file_path):
            raise ObjectNotFound(f"File not found in visualization {name}: {file_path}")
        static_dir = os.path.realpath(plugin.static_dir)
        candidate = os.path.realpath(os.path.join(static_dir, file_path))
        if not safe_contains(static_dir, candidate) or not os.path.isfile(candidate):
            raise ObjectNotFound(f"File not found in visualization {name}: {file_path}")
        return candidate

    # -- building links to visualizations from objects --
    def get_visualizations(self, trans: "ProvidesAppContext", target_object=None, embeddable=None):
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

    def get_visualization(self, trans: "ProvidesAppContext", visualization_name, target_object):
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
                if model_class and isinstance(target_object, model_class):
                    tests = data_source["tests"]
                    if tests is None or is_object_applicable(trans, target_object, tests):
                        return visualization.to_dict()
