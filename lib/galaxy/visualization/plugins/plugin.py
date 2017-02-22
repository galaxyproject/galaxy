"""
Visualization plugins: instantiate/deserialize data and models
from a query string and render a webpage based on those data.
"""

import os
import copy

import mako

from galaxy.managers import api_keys
from galaxy.web.base import pluginframework
from galaxy.web.base import interactive_environments

from galaxy.visualization.plugins import resource_parser
from galaxy.visualization.plugins import utils

import logging
log = logging.getLogger( __name__ )


# =============================================================================
# TODO:
# move mixins to facade'd objects
# allow config to override static/template settings
# allow config detection in alternate places: galaxy-visualization.xml
# =============================================================================
class ServesStaticPluginMixin( object ):
    """
    An object that serves static files from the server.
    """

    def _set_up_static_plugin( self, **kwargs ):
        """
        Detect and set up static paths and urls if needed.
        """
        # TODO: allow config override
        self.serves_static = False
        if self._is_static_plugin():
            self.static_path = self._build_static_path()
            self.static_url = self._build_static_url()
            self.serves_static = True
        return self.serves_static

    def _is_static_plugin( self ):
        """
        Detect whether this plugin should serve static resources.
        """
        return os.path.isdir( self._build_static_path() )

    def _build_static_path( self ):
        return os.path.join( self.path, 'static' )

    def _build_static_url( self ):
        return '/'.join([ self.base_url, 'static' ])


# =============================================================================
class ServesTemplatesPluginMixin( object ):
    """
    An object that renders (mako) template files from the server.
    """

    #: default number of templates to search for plugin template lookup
    DEFAULT_TEMPLATE_COLLECTION_SIZE = 10
    #: default encoding of plugin templates
    DEFAULT_TEMPLATE_ENCODING = 'utf-8'

    def _set_up_template_plugin( self, template_cache_dir, additional_template_paths=None, **kwargs ):
        """
        Detect and set up template paths if the plugin serves templates.
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
        Build a mako template filename lookup for the plugin.
        """
        template_lookup_paths = self.template_path
        if additional_template_paths:
            template_lookup_paths = [ template_lookup_paths ] + additional_template_paths
        return mako.lookup.TemplateLookup(
            directories=template_lookup_paths,
            module_directory=template_cache_dir,
            collection_size=collection_size,
            output_encoding=output_encoding )


# =============================================================================
class VisualizationPlugin( pluginframework.Plugin, ServesStaticPluginMixin, ServesTemplatesPluginMixin ):
    """
    A plugin that instantiates resources, serves static files, and uses mako
    templates to render web pages.
    """
    # AKA: MakoVisualizationPlugin
    # config[ 'entry_point' ][ 'type' ] == 'mako'
# TODO: concept/name collision between plugin config and visualization config

    def __init__( self, app, path, name, config, context=None, **kwargs ):
        super( VisualizationPlugin, self ).__init__( app, path, name, config, context=None, **kwargs )
        context = context or {}
        self.config = config

        base_url = context.get( 'base_url', '' )
        self.base_url = '/'.join([ base_url, self.name ]) if base_url else self.name
        self._set_up_static_plugin()

        template_cache_dir = context.get( 'template_cache_dir', None )
        additional_template_paths = context.get( 'additional_template_paths', [] )
        self._set_up_template_plugin( template_cache_dir, additional_template_paths=additional_template_paths )

        self.resource_parser = resource_parser.ResourceParser( app )

    def render( self, trans=None, embedded=None, **kwargs ):
        """
        Render and return the text of the non-saved plugin webpage/fragment.
        """
        # not saved - no existing config
        config = {}
        # set up render vars based on plugin.config and kwargs
        render_vars = self._build_render_vars( config, trans=trans, **kwargs )
        return self._render( render_vars, trans=trans, embedded=embedded )

    def render_saved( self, visualization, trans=None, embedded=None, **kwargs ):
        """
        Render and return the text of the plugin webpage/fragment using the
        config/data of a saved visualization.
        """
        config = self._get_saved_visualization_config( visualization, **kwargs )
        # pass the saved visualization config for parsing into render vars
        render_vars = self._build_render_vars( config, trans=trans, **kwargs )
        # update any values that were loaded from the saved Visualization
        render_vars.update( dict(
            title=visualization.latest_revision.title,
            saved_visualization=visualization,
            visualization_id=trans.security.encode_id( visualization.id ),
        ))
        return self._render( render_vars, trans=trans, embedded=embedded )

    def _get_saved_visualization_config( self, visualization, revision=None, **kwargs ):
        """
        Return the config of a saved visualization and revision.

        If no revision given, default to latest revision.
        """
        # TODO: allow loading a specific revision - should be part of UsesVisualization
        return copy.copy( visualization.latest_revision.config )

    # ---- non-public
    def _build_render_vars( self, config, trans=None, **kwargs ):
        """
        Build all the variables that will be passed into the renderer.
        """
        render_vars = {}
        # Meta variables passed to the template/renderer to describe the visualization being rendered.
        render_vars.update(
            visualization_name=self.name,
            visualization_display_name=self.config[ 'name' ],
            title=kwargs.get( 'title', None ),
            saved_visualization=None,
            visualization_id=None,
            # NOTE: passing *unparsed* kwargs as query
            query=kwargs,
        )
        # config based on existing or kwargs
        config = self._build_config( config, trans=trans, **kwargs )
        render_vars[ 'config' ] = config
        # further parse config to resources (models, etc.) used in template based on registry config
        resources = self._config_to_resources( trans, config )
        render_vars.update( resources )

        return render_vars

    def _build_config( self, config, trans=None, **kwargs ):
        """
        Build the configuration for this new/saved visualization by combining
        any existing config and the kwargs (gen. from the url query).
        """
        # first, pull from any existing config
        if config:
            config = copy.copy( config )
        else:
            config = {}
        # then, overwrite with keys/values from kwargs (gen. a query string)
        config_from_kwargs = self._kwargs_to_config( trans, kwargs )
        config.update( config_from_kwargs )
        # to object format for easier querying
        config = utils.OpenObject( **config )
        return config

    # TODO: the difference between config & resources is unclear in this section - is it needed?
    def _kwargs_to_config( self, trans, kwargs ):
        """
        Given a kwargs dict (gen. a query string dict from a controller action), parse
        and return any key/value pairs found in the plugin's `params` section.
        """
        expected_params = self.config.get( 'params', {} )
        config = self.resource_parser.parse_config( trans, expected_params, kwargs )
        return config

    def _config_to_resources( self, trans, config ):
        """
        Instantiate/deserialize the resources (HDAs, LDDAs, etc.) given in a
        visualization config into models/variables a visualization renderer can use.
        """
        expected_params = self.config.get( 'params', {} )
        param_modifiers = self.config.get( 'param_modifiers', {} )
        resources = self.resource_parser.parse_parameter_dictionary( trans, expected_params, config, param_modifiers )
        return resources

    def _render( self, render_vars, trans=None, embedded=None, **kwargs ):
        """
        Render the visualization via Mako and the plugin's template file.
        """
        render_vars[ 'embedded' ] = self._parse_embedded( embedded )
        # NOTE: (mako specific) vars is a dictionary for shared data in the template
        #   this feels hacky to me but it's what mako recommends:
        #   http://docs.makotemplates.org/en/latest/runtime.html
        render_vars.update( vars={} )
        template_filename = self.config[ 'entry_point' ][ 'file' ]
        return trans.fill_template( template_filename, template_lookup=self.template_lookup, **render_vars )

    def _parse_embedded( self, embedded ):
        """
        Parse information on dimensions, readonly, etc. from the embedded query val.
        """
        # as is for now
        return embedded


# =============================================================================
class InteractiveEnvironmentPlugin( VisualizationPlugin ):
    """
    Serves web-based REPLs such as Jupyter and RStudio.
    """
    INTENV_REQUEST_FACTORY = interactive_environments.InteractiveEnvironmentRequest

    def __init__( self, app, path, name, config, context=None, **kwargs ):
        # TODO: this is a hack until we can get int envs seperated from the vis reg and into their own framework
        context[ 'base_url' ] = 'interactive_environments'
        super( InteractiveEnvironmentPlugin, self ).__init__( app, path, name, config, context=context, **kwargs )

    def _render( self, render_vars, trans=None, embedded=None, **kwargs ):
        """
        Override to add interactive environment specific template vars.
        """
        render_vars[ 'embedded' ] = self._parse_embedded( embedded )
        # NOTE: (mako specific) vars is a dictionary for shared data in the template
        #   this feels hacky to me but it's what mako recommends:
        #   http://docs.makotemplates.org/en/latest/runtime.html
        render_vars.update( vars={} )
        # No longer needed but being left around for a few releases as jupyter-galaxy
        # as an external visualization plugin is deprecated in favor of core interactive
        # environment plugin.
        if 'get_api_key' not in render_vars:
            def get_api_key():
                return api_keys.ApiKeyManager( trans.app ).get_or_create_api_key( trans.user )
            render_vars[ 'get_api_key' ] = get_api_key

        if 'plugin_path' not in render_vars:
            render_vars[ 'plugin_path' ] = os.path.abspath( self.path )

        if self.config.get( 'plugin_type', 'visualization' ) == "interactive_environment":
            request = self.INTENV_REQUEST_FACTORY( trans, self )
            render_vars[ "ie_request" ] = request

        template_filename = self.config[ 'entry_point' ][ 'file' ]
        return trans.fill_template( template_filename, template_lookup=self.template_lookup, **render_vars )


# =============================================================================
class ScriptVisualizationPlugin( VisualizationPlugin ):
    """
    A visualization plugin that starts by loading a single (js) script.

    The script is loaded into a pre-defined mako template:
        `config/plugins/visualizations/common/templates/script_entry_point.mako`
    """
    MAKO_TEMPLATE = 'script_entry_point.mako'

    def _is_template_plugin( self ):
        """
        Override to always yield true since this plugin type always uses the
        pre-determined mako template.
        """
        return True

    def _render( self, render_vars, trans=None, embedded=None, **kwargs ):
        """
        Override to add script attributes and point mako at the script entry point
        template.
        """
        render_vars[ 'embedded' ] = self._parse_embedded( embedded )
        render_vars.update( vars={} )
        render_vars.update({
            "script_tag_attributes" : self.config[ 'entry_point' ][ 'attr' ]
        })
        template_filename = os.path.join( self.MAKO_TEMPLATE )
        return trans.fill_template( template_filename, template_lookup=self.template_lookup, **render_vars )


# =============================================================================
class StaticFileVisualizationPlugin( VisualizationPlugin ):
    """
    A visualiztion plugin that starts by loading a static html file defined
    in the visualization's config file.
    """
    # TODO: these are not embeddable by their nature - update config
    # TODO: should do render/render_saved here since most of the calc done there is unneeded in this case
    def _render( self, render_vars, trans=None, embedded=None, **kwargs ):
        """
        Render the static file simply by reading and returning it.
        """
        render_vars[ 'embedded' ] = self._parse_embedded( embedded )
        render_vars.update( vars={} )

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
