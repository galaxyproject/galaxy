"""
Base class for plugins - frameworks or systems that may:
 * serve static content
 * serve templated html
 * have some configuration at startup
"""

import os.path
import glob
import sys

import pkg_resources
pkg_resources.require( 'MarkupSafe' )
pkg_resources.require( 'Mako' )
import mako

import logging
log = logging.getLogger( __name__ )

# ============================================================================= exceptions
class PluginFrameworkException( Exception ):
    """Base exception for plugin frameworks.
    """
    pass
class PluginFrameworkConfigException( PluginFrameworkException ):
    """Exception for plugin framework configuration errors.
    """
    pass
class PluginFrameworkStaticException( PluginFrameworkException ):
    """Exception for plugin framework static directory set up errors.
    """
    pass
class PluginFrameworkTemplateException( PluginFrameworkException ):
    """Exception for plugin framework template directory
    and template rendering errors.
    """
    pass


# ============================================================================= base
class PluginFramework( object ):
    """
    Plugins are files/directories living outside the Galaxy ``lib`` directory
    that serve static files (css, js, images, etc.), use and serve mako templates,
    and have some configuration to control the rendering.

    A plugin framework sets up all the above components.
    """
    #: does the class need a config file(s) to be parsed?
    has_config             = True
    #: does the class need static files served?
    serves_static          = True
    #: does the class need template files served?
    serves_templates       = True
    #TODO: allow plugin mako inheritance from existing ``/templates`` files
    #uses_galaxy_templates  = True
    #TODO: possibly better as instance var (or a combo)
    #: the directories in ``plugin_directory`` with basenames listed here will
    #:  be ignored for config, static, and templates
    non_plugin_directories = []

    # ------------------------------------------------------------------------- setup
    @classmethod
    def from_config( cls, config_plugin_directory, config ):
        """
        Set up the framework based on data from some config object by:
        * constructing it's absolute plugin_directory filepath
        * getting a template_cache
        * and appending itself to the config object's ``plugin_frameworks`` list

        .. note::
            precondition: config obj should have attributes:
                root, template_cache, and (list) plugin_frameworks
        """
        # currently called from (base) app.py - defined here to allow override if needed
        if not config_plugin_directory:
            return None
        try:
            # create the plugin path and if plugin dir begins with '/' assume absolute path
            full_plugin_filepath = os.path.join( config.root, config_plugin_directory )
            if config_plugin_directory.startswith( os.path.sep ):
                full_plugin_filepath = config_plugin_directory
            if not os.path.exists( full_plugin_filepath ):
                raise PluginFrameworkException( 'Plugin path not found: %s' %( full_plugin_filepath ) )

            template_cache = config.template_cache if cls.serves_static else None
            plugin = cls( full_plugin_filepath, template_cache )

            config.plugin_frameworks.append( plugin )
            return plugin

        except PluginFrameworkException, plugin_exc:
            log.exception( "Error loading framework %s. Skipping...", cls.__class__.__name__ )
            return None

    def __str__( self ):
        return '%s(%s)' %( self.__class__.__name__, self.plugin_directory )

    def __init__( self, plugin_directory, name=None, template_cache_dir=None, debug=False ):
        """
        :type   plugin_directory:   string
        :param  plugin_directory:   the base directory where plugin code is kept
        :type   name:               (optional) string (default: None)
        :param  name:               the name of this plugin
            (that will appear in url pathing, etc.)
        :type   template_cache_dir: (optional) string (default: None)
        :param  template_cache_dir: the cache directory to store compiled mako
        """
        if not os.path.isdir( plugin_directory ):
            raise PluginFrameworkException( 'Framework plugin directory not found: %s, %s'
                                            %( self.__class__.__name__, plugin_directory ) )
        self.plugin_directory = plugin_directory
        #TODO: or pass in from config
        self.name = name or os.path.basename( self.plugin_directory )

        if self.has_config:
            self.load_configuration()
        # set_up_static_urls will be called during the static middleware creation (if serves_static)
        if self.serves_templates:
            self.set_up_templates( template_cache_dir )

    def get_plugin_directories( self ):
        """
        Return the plugin directory paths for this plugin.

        Gets any directories within ``plugin_directory`` that are directories
        themselves and whose ``basename`` is not in ``plugin_directory``.
        """
        # could instead explicitly list on/off in master config file
        for plugin_path in glob.glob( os.path.join( self.plugin_directory, '*' ) ):
            if not os.path.isdir( plugin_path ):
                continue

            if os.path.basename( plugin_path ) in self.non_plugin_directories:
                continue

            yield plugin_path

    # ------------------------------------------------------------------------- config
    def load_configuration( self ):
        """
        Override to load some framework/plugin specifc configuration.
        """
        # Abstract method
        return True

    # ------------------------------------------------------------------------- serving static files
    def get_static_urls_and_paths( self ):
        """
        For each plugin, return a 2-tuple where the first element is a url path
        to the plugin's static files and the second is a filesystem path to those
        same files.

        Meant to be passed to a Static url map.
        """
        url_and_paths = []
        # called during the static middleware creation (buildapp.py, wrap_in_static)

        # NOTE: this only searches for static dirs two levels deep (i.e. <plugin_directory>/<plugin-name>/static)
        for plugin_path in self.get_plugin_directories():
            # that path is a plugin, search for subdirs named static in THAT dir
            plugin_static_path = os.path.join( plugin_path, 'static' )
            if not os.path.isdir( plugin_static_path ):
                continue

            # build a url for that static subdir and create a Static urlmap entry for it
            plugin_name = os.path.splitext( os.path.basename( plugin_path ) )[0]
            plugin_url = self.name + '/' + plugin_name + '/static'
            url_and_paths.append( ( plugin_url, plugin_static_path ) )

        return url_and_paths

    # ------------------------------------------------------------------------- templates
    def set_up_templates( self, template_cache_dir ):
        """
        Add a ``template_lookup`` attribute to the framework that can be passed
        to the mako renderer to find templates.
        """
        if not template_cache_dir:
            raise PluginFrameworkTemplateException( 'Plugins that serve templates require a template_cache_dir' )
        self.template_lookup = self._create_mako_template_lookup( template_cache_dir, self._get_template_paths() )
        return self.template_lookup

    def _get_template_paths( self ):
        """
        Get the paths that will be searched for templates.
        """
        return [ self.plugin_directory ]

    def _create_mako_template_lookup( self, cache_dir, paths, collection_size=500, output_encoding='utf-8' ):
        """
        Create a ``TemplateLookup`` with defaults.
        """
        return mako.lookup.TemplateLookup(
            directories      = paths,
            module_directory = cache_dir,
            collection_size  = collection_size,
            output_encoding  = output_encoding )

    #TODO: do we want to remove trans and app from the plugin template context?
    def fill_template( self, trans, template_filename, **kwargs ):
        """
        Pass control over to trans and render the ``template_filename``.
        """
        # defined here to be overridden
        return trans.fill_template( template_filename, template_lookup=self.template_lookup, **kwargs )

    def fill_template_with_plugin_imports( self, trans, template_filename, **kwargs ):
        """
        Returns a rendered plugin template but allows importing modules from inside
        the plugin directory within the template.

        ..example:: I.e. given this layout for a plugin:
        bler/
            template/
                bler.mako
            static/
            conifg/
            my_script.py
        this version of `fill_template` allows `bler.mako` to call `import my_script`.
        """
        try:
            plugin_base_path = os.path.split( os.path.dirname( template_filename ) )[0]
            plugin_path = os.path.join( self.plugin_directory, plugin_base_path )
            sys.path.append( plugin_path )
            filled_template = self.fill_template( trans, template_filename, **kwargs )

        finally:
            sys.path.remove( plugin_path )

        return filled_template

    #TODO: could add plugin template helpers here
