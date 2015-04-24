import os

import pkg_resources
pkg_resources.require( 'MarkupSafe' )
pkg_resources.require( 'Mako' )
import mako

from galaxy.managers import api_keys
from galaxy.web.base import pluginframework
from galaxy.web.base import interactive_environments

from galaxy.visualization.plugins import resource_parser
from galaxy.visualization.plugins import utils


import logging
log = logging.getLogger( __name__ )


# =============================================================================
class ServesStaticPluginMixin( object ):

    def _set_up_static_plugin( self, **kwargs ):
        """
        """
        self.serves_static = False
        if self._is_static_plugin():
            self.static_path = self._build_static_path()
            self.static_url = self._build_static_url()
            self.serves_static = True
        return self.serves_static

    def _is_static_plugin( self ):
        """
        """
        return os.path.isdir( self._build_static_path() )

    def _build_static_path( self ):
        return os.path.join( self.path, 'static' )

    def _build_static_url( self ):
        return '/'.join([ self.base_url, 'static' ])


# =============================================================================
class ServesTemplatesPluginMixin( object ):

    #: default number of templates to search for plugin template lookup
    DEFAULT_TEMPLATE_COLLECTION_SIZE = 10
    #: default encoding of plugin templates
    DEFAULT_TEMPLATE_ENCODING = 'utf-8'

    def _set_up_template_plugin( self, template_cache_dir, additional_template_paths=None, **kwargs ):
        """
        """
        self.serves_templates = False
        if self._is_template_plugin():
            self.template_path = self._build_template_path()
            self.template_lookup = self._build_template_lookup( template_cache_dir,
                additional_template_paths=additional_template_paths )
            self.serves_templates = True
        return self.serves_templates

    def _is_template_plugin( self ):
        return os.path.isdir( self._build_template_path() )

    def _build_template_path( self ):
        return os.path.join( self.path, 'templates' )

    def _build_template_lookup( self, template_cache_dir, additional_template_paths=None,
            collection_size=DEFAULT_TEMPLATE_COLLECTION_SIZE, output_encoding=DEFAULT_TEMPLATE_ENCODING ):
        """
        """
        template_lookup_paths = self.template_path
        if additional_template_paths:
            template_lookup_paths = [ template_lookup_paths ] + additional_template_paths
        return mako.lookup.TemplateLookup(
            directories=template_lookup_paths,
            module_directory=template_cache_dir,
            collection_size=collection_size,
            output_encoding=output_encoding )

    def _fill_template( self, trans, template_filename, **kwargs ):
        """
        Pass control over to trans and render ``template_filename``.

        :type   trans:              ``galaxy.web.framework.webapp.GalaxyWebTransaction``
        :param  trans:              transaction doing the rendering
        :type   template_filename:  string
        :param  template_filename:  the path of the template to render relative to
            ``plugin.template_path``
        :returns:       rendered template
        """
        return trans.fill_template( template_filename, template_lookup=self.template_lookup, **kwargs )


# =============================================================================
class VisualizationPlugin( pluginframework.Plugin, ServesStaticPluginMixin, ServesTemplatesPluginMixin ):
    """
    """
    # AKA: MakoVisualizationPlugin

    def __init__( self, app, path, name, config, context=None, **kwargs ):
        super( VisualizationPlugin, self ).__init__( app, path, name, config, context=None, **kwargs )
        context = context or {}
        self.config = config

        base_url = context.get( 'base_url', '' )
        self.base_url = '/'.join([ base_url, self.name ])

        self._set_up_static_plugin()

        template_cache_dir = context.get( 'template_cache_dir', None )
        additional_template_paths = context.get( 'additional_template_paths', [] )
        self._set_up_template_plugin( template_cache_dir, additional_template_paths=additional_template_paths )

        self.resource_parser = resource_parser.ResourceParser()

    def render( self, controller=None, trans=None, visualization=None, config=None, embedded=None, **kwargs ):
        if visualization:
            return self._render_saved( visualization, config,
                controller=controller, trans=trans, embedded=embedded, **kwargs )

        # get the config for passing to the template from the kwargs dict, parsed using the plugin's params setting
        config_from_kwargs = self._query_dict_to_config( trans, controller, kwargs )
        config = utils.OpenObject( **config_from_kwargs )

        # further parse config to resources (models, etc.) used in template based on registry config
        resources = self._query_dict_to_resources( trans, controller, config )

        # if a saved visualization, pass in the encoded visualization id or None if a new render
        encoded_visualization_id = None

        visualization_display_name = self.config[ 'name' ]
        title = kwargs.get( 'title', None )

        return self._fill_template( trans,

            visualization_name=self.name,
            visualization_display_name=visualization_display_name,
            title=title,
            saved_visualization=visualization,
            visualization_id=encoded_visualization_id,

            embedded=embedded,
            # NOTE: passing *unparsed* kwargs as query
            query=kwargs,
            # NOTE: vars is a dictionary for shared data in the template
            #   this feels hacky to me but it's what mako recommends:
            #   http://docs.makotemplates.org/en/latest/runtime.html
            vars={},
            config=config,
            **resources
        )

    def _render_saved( self, visualization, config, controller=None, trans=None, embedded=None, **kwargs ):
        config = config or {}

        # get the config for passing to the template from the kwargs dict, parsed using the plugin's params setting
        config_from_kwargs = self._query_dict_to_config( trans, controller, kwargs )
        config.update( config_from_kwargs )
        config = utils.OpenObject( **config )

        # further parse config to resources (models, etc.) used in template based on registry config
        resources = self._query_dict_to_resources( trans, controller, config )

        # if a saved visualization, pass in the encoded visualization id or None if a new render
        encoded_visualization_id = trans.security.encode_id( visualization.id )

        visualization_display_name = self.config[ 'name' ]
        title = visualization.latest_revision.title

        return self._fill_template( trans,
            visualization_name=self.name,
            visualization_display_name=visualization_display_name,
            title=title,
            saved_visualization=visualization,
            visualization_id=encoded_visualization_id,
            embedded=embedded,
            # NOTE: passing *unparsed* kwargs as query
            query=kwargs,
            # NOTE: vars is a dictionary for shared data in the template
            #   this feels hacky to me but it's what mako recommends:
            #   http://docs.makotemplates.org/en/latest/runtime.html
            vars={},
            config=config,
            **resources
        )

    # ---------------- getting resources for visualization templates from link query strings
    def _fill_template( self, trans, **kwargs ):
        template_filename = self.config[ 'entry_point' ][ 'file' ]
        return trans.fill_template( template_filename, template_lookup=self.template_lookup, **kwargs )

    def _get_resource_params_and_modifiers( self ):
        """
        Get params and modifiers for the given visualization as a 2-tuple.

        Both `params` and `param_modifiers` default to an empty dictionary.
        """
        expected_params = self.config.get( 'params', {} )
        param_modifiers = self.config.get( 'param_modifiers', {} )
        return ( expected_params, param_modifiers )

    def _query_dict_to_resources( self, trans, controller, query_dict ):
        """
        Use a resource parser, controller, and a visualization's param configuration
        to convert a query string into the resources and variables a visualization
        template needs to start up.
        """
        param_confs, param_modifiers = self._get_resource_params_and_modifiers()
        resources = self.resource_parser.parse_parameter_dictionary(
            trans, controller, param_confs, query_dict, param_modifiers )
        return resources

    def _query_dict_to_config( self, trans, controller, query_dict ):
        """
        Given a query string dict (i.e. kwargs) from a controller action, parse
        and return any key/value pairs found in the plugin's `params` section.
        """
        param_confs = self.config.get( 'params', {} )
        config = self.resource_parser.parse_config( trans, controller, param_confs, query_dict )
        return config


# =============================================================================
class InteractiveEnvironmentPlugin( VisualizationPlugin ):
    """
    Serves web-based REPLs such as IPython and RStudio.
    """
    INTENV_REQUEST_FACTORY = interactive_environments.InteractiveEnviornmentRequest

    def _fill_template( self, trans, **kwargs ):
        # No longer needed but being left around for a few releases as ipython-galaxy
        # as an external visualization plugin is deprecated in favor of core interactive
        # environment plugin.
        if 'get_api_key' not in kwargs:
            def get_api_key():
                return api_keys.ApiKeyManager( trans.app ).get_or_create_api_key( trans.user )
            kwargs[ 'get_api_key' ] = get_api_key

        if 'plugin_path' not in kwargs:
            kwargs[ 'plugin_path' ] = os.path.abspath( self.path )

        if self.config.get( 'plugin_type', 'visualization' ) == "interactive_environment":
            request = self.INTENV_REQUEST_FACTORY( trans, self )
            kwargs[ "ie_request" ] = request

        template_filename = self.config[ 'entry_point' ][ 'file' ]
        return trans.fill_template( template_filename, template_lookup=self.template_lookup, **kwargs )


# =============================================================================
class ScriptVisualizationPlugin( VisualizationPlugin ):
    """
    A visualization plugin that starts by loading a single (js) script.

    The script is loaded into a pre-defined mako template:
        `config/plugins/visualizations/common/templates/script_entry_point.mako`
    """
    MAKO_TEMPLATE = 'script_entry_point.mako'

    def _set_up_template_plugin( self, template_cache_dir, additional_template_paths=None, **kwargs ):
        """
        Override to build template lookup despite not having a `template/` directory.
        """
        self.serves_templates = True
        self.template_path = self._build_template_path()
        self.template_lookup = self._build_template_lookup( template_cache_dir,
            additional_template_paths=additional_template_paths )
        return self.serves_templates

    def _fill_template( self, trans, **kwargs ):
        """
        Return the script entry point mako rendering with the script attributes sent in.
        """
        template_filename = os.path.join( self.MAKO_TEMPLATE )
        kwargs.update({
            "script_tag_attributes" : self.config[ 'entry_point' ][ 'attr' ]
        })
        return trans.fill_template( template_filename, template_lookup=self.template_lookup, **kwargs )


# =============================================================================
class StaticFileVisualizationPlugin( VisualizationPlugin ):
    """
    A visualiztion plugin that starts by loading a static html file defined
    in the visualization's config file.
    """
    def _fill_template( self, trans, **kwargs ):
        static_file_path = self.config[ 'entry_point' ][ 'file' ]
        static_file_path = os.path.join( self.path, static_file_path )
        with open( static_file_path, 'r' ) as outfile:
            return outfile.read()


# # =============================================================================
# class PyGeneratedVisualizationPlugin( VisualizationPlugin ):
#     """
#     Selectively import one module and call a specified fn within it to generate the
#     HTML served.
#     """
#     pass
