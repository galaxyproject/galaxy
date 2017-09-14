"""
Base class for plugins - frameworks or systems that may:
 * add code at startup
 * allow hooks to be called
and base class for plugins that:
 * serve static content
 * serve templated html
 * have some configuration at startup
"""
import imp
import logging
import os.path
import sys

import mako.lookup

from galaxy import util
from galaxy.util import (
    bunch,
    odict
)

log = logging.getLogger(__name__)


class PluginManagerException(Exception):
    """Base exception for plugin frameworks.
    """
    pass


class PluginManagerConfigException(PluginManagerException):
    """Exception for plugin framework configuration errors.
    """
    pass


# ============================================================================= base
class PluginManager(object):
    """
    Plugins represents an section of code that is not tracked in the
    Galaxy repository, allowing the addition of custom code to a Galaxy
    installation without changing the code base.

    A PluginManager discovers and manages these plugins.

    This is an non-abstract class but its usefulness is limited and is meant
    to be inherited.
    """

    def __init__(self, app, directories_setting=None, skip_bad_plugins=True, **kwargs):
        """
        Set up the manager and load all plugins.

        :type   app:    UniverseApplication
        :param  app:    the application (and its configuration) using this manager
        :type   directories_setting: string (default: None)
        :param  directories_setting: the filesystem path (or paths)
            to search for plugins. Can be CSV string of paths. Will be treated as
            absolute if a path starts with '/', relative otherwise.
        :type   skip_bad_plugins:    boolean (default: True)
        :param  skip_bad_plugins:    whether to skip plugins that cause
            exceptions when loaded or to raise that exception
        """
        self.directories = []
        self.skip_bad_plugins = skip_bad_plugins
        self.plugins = odict.odict()

        self.directories = util.config_directories_from_setting(directories_setting, app.config.root)

        self._load_configuration()
        self._load_plugins()

    def _load_configuration(self):
        """
        Override to load some framework/plugin specifc configuration.
        """
        # Abstract method
        return True

    def _load_plugins(self):
        """
        Search ``self.directories`` for potential plugins, load them, and cache
        in ``self.plugins``.
        :rtype:                 odict
        :returns:               ``self.plugins``
        """
        for plugin_path in self._find_plugins():
            try:
                plugin = self._load_plugin(plugin_path)

                if plugin and plugin.name not in self.plugins:
                    self.plugins[plugin.name] = plugin
                    log.info('%s, loaded plugin: %s', self, plugin.name)
                # NOTE: prevent silent, implicit overwrite here (two plugins in two diff directories)
                # TODO: overwriting may be desired
                elif plugin and plugin.name in self.plugins:
                    log.warning('%s, plugin with name already exists: %s. Skipping...', self, plugin.name)

            except Exception:
                if not self.skip_bad_plugins:
                    raise
                log.exception('Plugin loading raised exception: %s. Skipping...', plugin_path)

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
        if not os.path.isdir(plugin_path):
            return False
        return True

    def _load_plugin(self, plugin_path):
        """
        Create, load, and/or initialize the plugin and return it.

        Plugin bunches are decorated with:
            * name : the plugin name
            * path : the plugin path

        :type   plugin_path:    string
        :param  plugin_path:    relative or absolute filesystem path to the plugin
        :rtype:                 ``util.bunch.Bunch``
        :returns:               the loaded plugin object
        """
        plugin = bunch.Bunch(
            # TODO: need a better way to define plugin names
            #   pro: filesystem name ensures uniqueness
            #   con: rel. inflexible
            name=os.path.split(plugin_path)[1],
            path=plugin_path
        )
        return plugin


# ============================================================================= base
class PageServingPluginManager(PluginManager):
    """
    Page serving plugins are files/directories that:
        * are not tracked in the Galaxy repository and allow adding custom code
            to a Galaxy installation
        * serve static files (css, js, images, etc.),
        * render templates

    A PageServingPluginManager sets up all the above components.
    """
    # TODO: I'm unclear of the utility of this class - it prob. will only have one subclass (vis reg). Fold into?

    #: default static url base
    DEFAULT_BASE_URL = ''
    #: does the class need static files served?
    serves_static = True
    #: does the class need template files served?
    serves_templates = True
    #: default number of templates to search for plugin template lookup
    DEFAULT_TEMPLATE_COLLECTION_SIZE = 10
    #: default encoding of plugin templates
    DEFAULT_TEMPLATE_ENCODING = 'utf-8'
    #: name of files to search for additional template lookup directories
    additional_template_paths_config_filename = 'additional_template_paths.xml'

    def __init__(self, app, base_url='', template_cache_dir=None, **kwargs):
        """
        Set up the manager and load all plugins.

        :type   app:        UniverseApplication
        :param  app:        the application (and its configuration) using this manager
        :type   base_url:   string
        :param  base_url:   url to prefix all plugin urls with
        :type   template_cache_dir: string
        :param  template_cache_dir: filesytem path to the directory where cached
            templates are kept
        """
        self.base_url = base_url or self.DEFAULT_BASE_URL
        if not self.base_url:
            raise PluginManagerException('base_url or DEFAULT_BASE_URL required')
        self.template_cache_dir = template_cache_dir
        self.additional_template_paths = []
        self.directories = []
        self.skip_bad_plugins = skip_bad_plugins
        self.plugins = odict.odict()
        self.directories = util.config_directories_from_setting(directories_setting, app.config.root)
        self._load_configuration()
        self._load_plugins()

    def _load_configuration(self):
        """
        Load framework wide configuration, including:
            additional template lookup directories
        """
        for directory in self.directories:
            possible_path = os.path.join(directory, self.additional_template_paths_config_filename)
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
        xml_tree = util.parse_xml(config_filepath)
        paths_list = xml_tree.getroot()
        for rel_path_elem in paths_list.findall('path'):
            if rel_path_elem.text is not None:
                additional_paths.append(os.path.join(base_directory, rel_path_elem.text))
        return additional_paths

    def _is_plugin(self, plugin_path):
        """
        Determines whether the given filesystem path contains a plugin.

        If the manager ``serves_templates`` and a sub-directory contains another
        sub-directory named 'templates' it's considered valid.
        If the manager ``serves_static`` and a sub-directory contains another
        sub-directory named 'static' it's considered valid.

        :type   plugin_path:    string
        :param  plugin_path:    relative or absolute filesystem path to the
            potential plugin
        :rtype:                 bool
        :returns:               True if the path contains a plugin
        """
        if not super(PageServingPluginManager, self)._is_plugin(plugin_path):
            return False
        # reject only if we don't have either
        listdir = os.listdir(plugin_path)
        if(('templates' not in listdir) and ('static' not in listdir)):
            return False
        return True

    def _load_plugin(self, plugin_path):
        """
        Create the plugin and decorate with static and/or template paths and urls.

        Plugin bunches are decorated with:
            * name : the plugin name
            * path : the plugin path
            * base_url : a url to the plugin

        :type   plugin_path:    string
        :param  plugin_path:    relative or absolute filesystem path to the plugin
        :rtype:                 ``util.bunch.Bunch``
        :returns:               the loaded plugin object
        """
        plugin = super(PageServingPluginManager, self).load_plugin(plugin_path)
        # TODO: urlencode?
        plugin['base_url'] = '/'.join([self.base_url, plugin.name])
        plugin = self._set_up_static_plugin(plugin)
        plugin = self._set_up_template_plugin(plugin)

        return plugin

    def _set_up_static_plugin(self, plugin):
        """
        Decorate the plugin with paths and urls needed to serve static content.

        Plugin bunches are decorated with:
            * serves_static : whether this plugin will serve static content

        If the plugin path contains a 'static' sub-dir, the following are added:
            * static_path   : the filesystem path to the static content
            * static_url    : the url to use when serving static content

        :type   plugin: ``util.bunch.Bunch``
        :param  plugin: the plugin to decorate
        :rtype:         ``util.bunch.Bunch``
        :returns:       the loaded plugin object
        """
        plugin['serves_static'] = False
        static_path = os.path.join(plugin.path, 'static')
        if self.serves_static and os.path.isdir(static_path):
            plugin.serves_static = True
            plugin['static_path'] = static_path
            plugin['static_url'] = '/'.join([plugin.base_url, 'static'])
        return plugin

    def _set_up_template_plugin(self, plugin):
        """
        Decorate the plugin with paths needed to fill templates.

        Plugin bunches are decorated with:
            * serves_templates :    whether this plugin will use templates

        If the plugin path contains a 'static' sub-dir, the following are added:
            * template_path   : the filesystem path to the template sub-dir
            * template_lookup : the (currently Mako) TemplateLookup used to search
                for templates

        :type   plugin: ``util.bunch.Bunch``
        :param  plugin: the plugin to decorate
        :rtype:         ``util.bunch.Bunch``
        :returns:       the loaded plugin object
        """
        plugin['serves_templates'] = False
        template_path = os.path.join(plugin.path, 'templates')
        if self.serves_templates and os.path.isdir(template_path):
            plugin.serves_templates = True
            plugin['template_path'] = template_path
            plugin['template_lookup'] = self.build_plugin_template_lookup(plugin)
        return plugin

    # ------------------------------------------------------------------------- serving static files
    def get_static_urls_and_paths(self):
        """
        For each plugin, return a 2-tuple where the first element is a url path
        to the plugin's static files and the second is a filesystem path to those
        same files.

        Meant to be passed to a Static url map.

        :rtype:         list of 2-tuples
        :returns:       all urls and paths for each plugin serving static content
        """
        # called during the static middleware creation (buildapp.py, wrap_in_static)
        urls_and_paths = []
        for plugin in self.plugins.values():
            if plugin.serves_static:
                urls_and_paths.append((plugin.static_url, plugin.static_path))
        return urls_and_paths

    # ------------------------------------------------------------------------- templates
    def _build_plugin_template_lookup(self, plugin):
        """
        Builds the object that searches for templates (cached or not) when rendering.

        :type   plugin: ``util.bunch.Bunch``
        :param  plugin: the plugin containing the templates
        :rtype:         ``Mako.lookup.TemplateLookup``
        :returns:       template lookup for this plugin
        """
        if not plugin.serves_templates:
            return None
        template_lookup_paths = plugin.template_path
        if self.additional_template_paths:
            template_lookup_paths = [template_lookup_paths] + self.additional_template_paths
        template_lookup = self._create_mako_template_lookup(self.template_cache_dir, template_lookup_paths)
        return template_lookup

    def _create_mako_template_lookup(self, cache_dir, paths,
                                     collection_size=DEFAULT_TEMPLATE_COLLECTION_SIZE, output_encoding=DEFAULT_TEMPLATE_ENCODING):
        """
        Create a ``TemplateLookup`` with defaults.

        :rtype:         ``Mako.lookup.TemplateLookup``
        :returns:       all urls and paths for each plugin serving static content
        """
        # TODO: possible to add galaxy/templates into the lookup here?
        return mako.lookup.TemplateLookup(
            directories=paths,
            module_directory=cache_dir,
            collection_size=collection_size,
            output_encoding=output_encoding)

    def fill_template(self, trans, plugin, template_filename, **kwargs):
        """
        Pass control over to trans and render ``template_filename``.

        :type   trans:              ``galaxy.web.framework.webapp.GalaxyWebTransaction``
        :param  trans:              transaction doing the rendering
        :type   plugin:             ``util.bunch.Bunch``
        :param  plugin:             the plugin containing the template to render
        :type   template_filename:  string
        :param  template_filename:  the path of the template to render relative to
            ``plugin.template_path``
        :returns:       rendered template
        """
        # defined here to be overridden
        return trans.fill_template(template_filename, template_lookup=plugin.template_lookup, **kwargs)

    # TODO: add fill_template fn that is able to load extra libraries beforehand (and remove after)
    # TODO: add template helpers specific to the plugins
    # TODO: some sort of url_for for these plugins

