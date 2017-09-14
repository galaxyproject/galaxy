"""
Lower level of visualization framework which does three main things:
    - associate visualizations with objects
    - create urls to visualizations based on some target object(s)
    - unpack a query string into the desired objects needed for rendering
"""
import imp
import logging
import mako.lookup
import os
import sys
import weakref

from galaxy.util import bunch
from galaxy.util import config_directories_from_setting
from galaxy.util import odict
from galaxy.util import parse_xml
from galaxy.web import url_for
from galaxy.exceptions import ObjectNotFound
from galaxy.visualization.plugins import config_parser
from galaxy.visualization.plugins import plugin as vis_plugins
from galaxy.visualization.plugins import utils as vis_utils

log = logging.getLogger(__name__)


class VisualizationsRegistry(object):
    """
    Main responsibilities are:
        - discovering visualization plugins in the filesystem
        - testing if an object has a visualization that can be applied to it
        - generating a link to controllers.visualization.render with
            the appropriate params
        - validating and parsing params into resources (based on a context)
            used in the visualization template
    """
    NAMED_ROUTE = 'visualization_plugin'
    DEFAULT_BASE_URL = 'visualizations'
    # these should be handled somewhat differently - and be passed onto their resp. methods in ctrl.visualization
    # TODO: change/remove if/when they can be updated to use this system
    #: any built in visualizations that have their own render method in ctrls/visualization
    BUILT_IN_VISUALIZATIONS = [
        'trackster',
        'circster',
        'sweepster',
        'phyloviz'
    ]

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

    def __str__(self):
        return self.__class__.__name__

    def __init__(self, app, base_url='', template_cache_dir=None, directories_setting=None, skip_bad_plugins=True, **kwargs):
        """
        Set up the manager and load all visualization plugins.

        :type   app:        UniverseApplication
        :param  app:        the application (and its configuration) using this manager
        :type   base_url:   string
        :param  base_url:   url to prefix all plugin urls with
        :type   template_cache_dir: string
        :param  template_cache_dir: filesytem path to the directory where cached
            templates are kept
        """
        self.app = weakref.ref(app)
        self.config_parser = config_parser.VisualizationsConfigParser()
        self.base_url = base_url or self.DEFAULT_BASE_URL
        if not self.base_url:
            raise Exception('base_url or DEFAULT_BASE_URL required')
        self.template_cache_dir = template_cache_dir
        self.additional_template_paths = []
        self.directories = []
        self.skip_bad_plugins = skip_bad_plugins
        self.plugins = odict.odict()
        self.directories = config_directories_from_setting(directories_setting, app.config.root)
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
        xml_tree = parse_xml(config_filepath)
        paths_list = xml_tree.getroot()
        for rel_path_elem in paths_list.findall('path'):
            if rel_path_elem.text is not None:
                additional_paths.append(os.path.join(base_directory, rel_path_elem.text))
        return additional_paths

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
        if 'config' not in os.listdir(plugin_path):
            return False
        expected_config_filename = '%s.xml' % (os.path.split(plugin_path)[1])
        if not os.path.isfile(os.path.join(plugin_path, 'config', expected_config_filename)):
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
        config_file = os.path.join(plugin_path, 'config', (plugin_name + '.xml'))
        config = self.config_parser.parse_file(config_file)
        # config file is required, otherwise skip this visualization
        if not config:
            return None
        plugin = self._build_plugin(plugin_name, plugin_path, config)
        return plugin

    def _build_plugin(self, plugin_name, plugin_path, config):
        # TODO: as builder not factory

        # default class
        plugin_class = vis_plugins.VisualizationPlugin
        # jupyter, etc
        if config['plugin_type'] == 'interactive_environment':
            plugin_class = vis_plugins.InteractiveEnvironmentPlugin
        # js only
        elif config['entry_point']['type'] == 'script':
            plugin_class = vis_plugins.ScriptVisualizationPlugin
        # from a static file (html, etc)
        elif config['entry_point']['type'] == 'html':
            plugin_class = vis_plugins.StaticFileVisualizationPlugin

        plugin = plugin_class(self.app(), plugin_path, plugin_name, config, context=dict(
            base_url=self.base_url,
            template_cache_dir=self.template_cache_dir,
            additional_template_paths=self.additional_template_paths
        ))
        return plugin

    def get_plugin(self, key):
        """
        Wrap to throw error if plugin not in registry.
        """
        if key not in self.plugins:
            raise ObjectNotFound('Unknown or invalid visualization: ' + key)
        return self.plugins[key]

    # -- building links to visualizations from objects --
    def get_visualizations(self, trans, target_object):
        """
        Get the names of visualizations usable on the `target_object` and
        the urls to call in order to render the visualizations.
        """
        # TODO:?? a list of objects? YAGNI?
        applicable_visualizations = []
        for vis_name in self.plugins:
            url_data = self.get_visualization(trans, vis_name, target_object)
            if url_data:
                applicable_visualizations.append(url_data)
        return applicable_visualizations

    def get_visualization(self, trans, visualization_name, target_object):
        """
        Return data to build a url to the visualization with the given
        `visualization_name` if it's applicable to `target_object` or
        `None` if it's not.
        """
        # log.debug( 'VisReg.get_visualization: %s, %s', visualization_name, target_object )
        visualization = self.plugins.get(visualization_name, None)
        if not visualization:
            return None

        data_sources = visualization.config['data_sources']
        for data_source in data_sources:
            # log.debug( 'data_source: %s', data_source )
            # currently a model class is required
            model_class = data_source['model_class']
            # log.debug( '\t model_class: %s', model_class )
            if not isinstance(target_object, model_class):
                continue
            # log.debug( '\t passed model_class' )

            # TODO: not true: must have test currently
            tests = data_source['tests']
            if tests and not self.is_object_applicable(trans, target_object, tests):
                continue
            # log.debug( '\t passed tests' )

            param_data = data_source['to_params']
            url = self.get_visualization_url(trans, target_object, visualization, param_data)
            display_name = visualization.config.get('name', None)
            render_target = visualization.config.get('render_target', 'galaxy_main')
            embeddable = visualization.config.get('embeddable', False)
            # remap some of these vars for direct use in ui.js, PopupMenu (e.g. text->html)
            return {
                'href'      : url,
                'html'      : display_name,
                'target'    : render_target,
                'embeddable': embeddable
            }

        return None

    def is_object_applicable(self, trans, target_object, data_source_tests):
        """
        Run a visualization's data_source tests to find out if
        it can be applied to the target_object.
        """
        # log.debug( 'is_object_applicable( self, trans, %s, %s )', target_object, data_source_tests )
        for test in data_source_tests:
            test_type = test['type']
            result_type = test['result_type']
            test_result = test['result']
            test_fn = test['fn']
            # log.debug( '%s %s: %s, %s, %s, %s', str( target_object ), 'is_object_applicable',
            #           test_type, result_type, test_result, test_fn )

            if test_type == 'isinstance':
                # parse test_result based on result_type (curr: only datatype has to do this)
                if result_type == 'datatype':
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
            if test_fn(target_object, test_result):
                # log.debug( '\t test passed' )
                return True

        return False

    def get_visualization_url(self, trans, target_object, visualization, param_data):
        """
        Generates a url for the visualization with `visualization`
        for use with the given `target_object` with a query string built
        from the configuration data in `param_data`.
        """
        # precondition: the target_object should be usable by the visualization (accrd. to data_sources)
        # convert params using vis.data_source.to_params
        params = self.get_url_params(trans, target_object, param_data)

        # we want existing visualizations to work as normal but still be part of the registry (without mod'ing)
        #   so generate their urls differently
        url = None
        if visualization.name in self.BUILT_IN_VISUALIZATIONS:
            url = url_for(controller='visualization', action=visualization.name, **params)
        # TODO: needs to be split off as it's own registry
        elif isinstance(visualization, vis_plugins.InteractiveEnvironmentPlugin):
            url = url_for('interactive_environment_plugin', visualization_name=visualization.name, **params)
        else:
            url = url_for(self.NAMED_ROUTE, visualization_name=visualization.name, **params)

        # TODO:?? not sure if embedded would fit/used here? or added in client...
        return url

    def get_url_params(self, trans, target_object, param_data):
        """
        Convert the applicable objects and assoc. data into a param dict
        for a url query string to add to the url that loads the visualization.
        """
        params = {}
        for to_param_name, to_param_data in param_data.items():
            # TODO??: look into params as well? what is required, etc.
            target_attr = to_param_data.get('param_attr', None)
            assign = to_param_data.get('assign', None)
            # one or the other is needed
            # assign takes precedence (goes last, overwrites)?
            # NOTE this is only one level

            if target_attr and vis_utils.hasattr_recursive(target_object, target_attr):
                params[to_param_name] = vis_utils.getattr_recursive(target_object, target_attr)

            if assign:
                params[to_param_name] = assign

        # NOTE!: don't expose raw ids: encode id, _id
        # TODO: double encodes if from config
        if params:
            params = trans.security.encode_dict_ids(params)
        return params
