"""
Lower level of visualization framework which does three main things:
    - associate visualizations with objects
    - create urls to visualizations based on some target object(s)
    - unpack a query string into the desired objects needed for rendering
"""
import os
import weakref

from galaxy.web import url_for
import galaxy.exceptions

from galaxy.web.base import pluginframework
from galaxy.visualization.plugins import config_parser
from galaxy.visualization.plugins import plugin as vis_plugins
from galaxy.visualization.plugins import utils as vis_utils


import logging
log = logging.getLogger( __name__ )


# -------------------------------------------------------------------
class VisualizationsRegistry( pluginframework.PageServingPluginManager ):
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

    def __str__( self ):
        return self.__class__.__name__

    def __init__( self, app, skip_bad_plugins=True, **kwargs ):
        self.app = weakref.ref( app )
        self.config_parser = config_parser.VisualizationsConfigParser()
        super( VisualizationsRegistry, self ).__init__( app, skip_bad_plugins=skip_bad_plugins, **kwargs )

    def is_plugin( self, plugin_path ):
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
        if not os.path.isdir( plugin_path ):
            # super won't work here - different criteria
            return False
        if 'config' not in os.listdir( plugin_path ):
            return False
        expected_config_filename = '%s.xml' % ( os.path.split( plugin_path )[1] )
        if not os.path.isfile( os.path.join( plugin_path, 'config', expected_config_filename ) ):
            return False
        return True

    def load_plugin( self, plugin_path ):
        """
        Create the visualization plugin object, parse its configuration file,
        and return it.

        :type   plugin_path:    string
        :param  plugin_path:    relative or absolute filesystem path to the plugin
        :rtype:                 ``VisualizationPlugin``
        :returns:               the loaded plugin
        """
        plugin_name = os.path.split( plugin_path )[1]
        # TODO: this is the standard/older way to config
        config_file = os.path.join( plugin_path, 'config', ( plugin_name + '.xml' ) )
        config = self.config_parser.parse_file( config_file )
        # config file is required, otherwise skip this visualization
        if not config:
            return None
        plugin = self._build_plugin( plugin_name, plugin_path, config )
        return plugin

    def _build_plugin( self, plugin_name, plugin_path, config ):
        # TODO: as builder not factory

        # default class
        plugin_class = vis_plugins.VisualizationPlugin
        # jupyter, etc
        if config[ 'plugin_type' ] == 'interactive_environment':
            plugin_class = vis_plugins.InteractiveEnvironmentPlugin
        # js only
        elif config[ 'entry_point' ][ 'type' ] == 'script':
            plugin_class = vis_plugins.ScriptVisualizationPlugin
        # from a static file (html, etc)
        elif config[ 'entry_point' ][ 'type' ] == 'html':
            plugin_class = vis_plugins.StaticFileVisualizationPlugin

        plugin = plugin_class( self.app(), plugin_path, plugin_name, config, context=dict(
            base_url=self.base_url,
            template_cache_dir=self.template_cache_dir,
            additional_template_paths=self.additional_template_paths
        ))
        return plugin

    def get_plugin( self, key ):
        """
        Wrap to throw error if plugin not in registry.
        """
        if key not in self.plugins:
            raise galaxy.exceptions.ObjectNotFound( 'Unknown or invalid visualization: ' + key )
        return self.plugins[ key ]

    # -- building links to visualizations from objects --
    def get_visualizations( self, trans, target_object ):
        """
        Get the names of visualizations usable on the `target_object` and
        the urls to call in order to render the visualizations.
        """
        # TODO:?? a list of objects? YAGNI?
        applicable_visualizations = []
        for vis_name in self.plugins:
            url_data = self.get_visualization( trans, vis_name, target_object )
            if url_data:
                applicable_visualizations.append( url_data )
        return applicable_visualizations

    def get_visualization( self, trans, visualization_name, target_object ):
        """
        Return data to build a url to the visualization with the given
        `visualization_name` if it's applicable to `target_object` or
        `None` if it's not.
        """
        # log.debug( 'VisReg.get_visualization: %s, %s', visualization_name, target_object )
        visualization = self.plugins.get( visualization_name, None )
        if not visualization:
            return None

        data_sources = visualization.config[ 'data_sources' ]
        for data_source in data_sources:
            # log.debug( 'data_source: %s', data_source )
            # currently a model class is required
            model_class = data_source[ 'model_class' ]
            # log.debug( '\t model_class: %s', model_class )
            if not isinstance( target_object, model_class ):
                continue
            # log.debug( '\t passed model_class' )

            # TODO: not true: must have test currently
            tests = data_source[ 'tests' ]
            if tests and not self.is_object_applicable( trans, target_object, tests ):
                continue
            # log.debug( '\t passed tests' )

            param_data = data_source[ 'to_params' ]
            url = self.get_visualization_url( trans, target_object, visualization, param_data )
            display_name = visualization.config.get( 'name', None )
            render_target = visualization.config.get( 'render_target', 'galaxy_main' )
            embeddable = visualization.config.get( 'embeddable', False )
            # remap some of these vars for direct use in ui.js, PopupMenu (e.g. text->html)
            return {
                'href'      : url,
                'html'      : display_name,
                'target'    : render_target,
                'embeddable': embeddable
            }

        return None

    def is_object_applicable( self, trans, target_object, data_source_tests ):
        """
        Run a visualization's data_source tests to find out if
        it can be applied to the target_object.
        """
        # log.debug( 'is_object_applicable( self, trans, %s, %s )', target_object, data_source_tests )
        for test in data_source_tests:
            test_type = test[ 'type' ]
            result_type = test[ 'result_type' ]
            test_result = test[ 'result' ]
            test_fn = test[ 'fn' ]
            # log.debug( '%s %s: %s, %s, %s, %s', str( target_object ), 'is_object_applicable',
            #           test_type, result_type, test_result, test_fn )

            if test_type == 'isinstance':
                # parse test_result based on result_type (curr: only datatype has to do this)
                if result_type == 'datatype':
                    # convert datatypes to their actual classes (for use with isinstance)
                    datatype_class_name = test_result
                    test_result = trans.app.datatypes_registry.get_datatype_class_by_name( datatype_class_name )
                    if not test_result:
                        # but continue (with other tests) if can't find class by that name
                        # if self.debug:
                        #    log.warning( 'visualizations_registry cannot find class (%s)' +
                        #              ' for applicability test on: %s, id: %s', datatype_class_name,
                        #              target_object, getattr( target_object, 'id', '' ) )
                        continue

            # NOTE: tests are OR'd, if any test passes - the visualization can be applied
            if test_fn( target_object, test_result ):
                # log.debug( '\t test passed' )
                return True

        return False

    def get_visualization_url( self, trans, target_object, visualization, param_data ):
        """
        Generates a url for the visualization with `visualization`
        for use with the given `target_object` with a query string built
        from the configuration data in `param_data`.
        """
        # precondition: the target_object should be usable by the visualization (accrd. to data_sources)
        # convert params using vis.data_source.to_params
        params = self.get_url_params( trans, target_object, param_data )

        # we want existing visualizations to work as normal but still be part of the registry (without mod'ing)
        #   so generate their urls differently
        url = None
        if visualization.name in self.BUILT_IN_VISUALIZATIONS:
            url = url_for( controller='visualization', action=visualization.name, **params )
        # TODO: needs to be split off as it's own registry
        elif isinstance( visualization, vis_plugins.InteractiveEnvironmentPlugin ):
            url = url_for( 'interactive_environment_plugin', visualization_name=visualization.name, **params )
        else:
            url = url_for( self.NAMED_ROUTE, visualization_name=visualization.name, **params )

        # TODO:?? not sure if embedded would fit/used here? or added in client...
        return url

    def get_url_params( self, trans, target_object, param_data ):
        """
        Convert the applicable objects and assoc. data into a param dict
        for a url query string to add to the url that loads the visualization.
        """
        params = {}
        for to_param_name, to_param_data in param_data.items():
            # TODO??: look into params as well? what is required, etc.
            target_attr = to_param_data.get( 'param_attr', None )
            assign = to_param_data.get( 'assign', None )
            # one or the other is needed
            # assign takes precedence (goes last, overwrites)?
            # NOTE this is only one level

            if target_attr and vis_utils.hasattr_recursive( target_object, target_attr ):
                params[ to_param_name ] = vis_utils.getattr_recursive( target_object, target_attr )

            if assign:
                params[ to_param_name ] = assign

        # NOTE!: don't expose raw ids: encode id, _id
        # TODO: double encodes if from config
        if params:
            params = trans.security.encode_dict_ids( params )
        return params
