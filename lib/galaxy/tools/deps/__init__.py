"""
Dependency management for tools.
"""

import os.path

import logging
log = logging.getLogger( __name__ )

from xml.etree import ElementTree

from .resolvers import INDETERMINATE_DEPENDENCY
from .resolvers.galaxy_packages import GalaxyPackageDependencyResolver
from .resolvers.tool_shed_packages import ToolShedPackageDependencyResolver
from galaxy.util.submodules import submodules


def build_dependency_manager( config ):
    if config.use_tool_dependencies:
        dependency_manager_kwds = {
            'default_base_path': config.tool_dependency_dir,
            'conf_file': config.dependency_resolvers_config_file,
        }
        dependency_manager = DependencyManager( **dependency_manager_kwds )
    else:
        dependency_manager = NullDependencyManager()

    return dependency_manager


class NullDependencyManager( object ):

    def uses_tool_shed_dependencies(self):
        return False

    def dependency_shell_commands( self, requirements, **kwds ):
        return []

    def find_dep( self, name, version=None, type='package', **kwds ):
        return INDETERMINATE_DEPENDENCY


class DependencyManager( object ):
    """
    A DependencyManager attempts to resolve named and versioned dependencies by
    searching for them under a list of directories. Directories should be
    of the form:

        $BASE/name/version/...

    and should each contain a file 'env.sh' which can be sourced to make the
    dependency available in the current shell environment.
    """
    def __init__( self, default_base_path, conf_file=None ):
        """
        Create a new dependency manager looking for packages under the paths listed
        in `base_paths`.  The default base path is app.config.tool_dependency_dir.
        """
        if not os.path.exists( default_base_path ):
            log.warn( "Path '%s' does not exist, ignoring", default_base_path )
        if not os.path.isdir( default_base_path ):
            log.warn( "Path '%s' is not directory, ignoring", default_base_path )
        self.default_base_path = os.path.abspath( default_base_path )
        self.resolver_classes = self.__resolvers_dict()
        self.dependency_resolvers = self.__build_dependency_resolvers( conf_file )

    def dependency_shell_commands( self, requirements, **kwds ):
        commands = []
        for requirement in requirements:
            log.debug( "Building dependency shell command for dependency '%s'", requirement.name )
            dependency = INDETERMINATE_DEPENDENCY
            if requirement.type in [ 'package', 'set_environment' ]:
                dependency = self.find_dep( name=requirement.name,
                                            version=requirement.version,
                                            type=requirement.type,
                                            **kwds )
            dependency_commands = dependency.shell_commands( requirement )
            if not dependency_commands:
                log.warn( "Failed to resolve dependency on '%s', ignoring", requirement.name )
            else:
                commands.append( dependency_commands )
        return commands

    def uses_tool_shed_dependencies(self):
        return any( map( lambda r: isinstance( r, ToolShedPackageDependencyResolver ), self.dependency_resolvers ) )

    def find_dep( self, name, version=None, type='package', **kwds ):
        for resolver in self.dependency_resolvers:
            dependency = resolver.resolve( name, version, type, **kwds )
            if dependency != INDETERMINATE_DEPENDENCY:
                return dependency
        return INDETERMINATE_DEPENDENCY

    def __build_dependency_resolvers( self, conf_file ):
        if not conf_file or not os.path.exists( conf_file ):
            return self.__default_dependency_resolvers()
        root = ElementTree.parse( conf_file ).getroot()
        return self.__parse_resolver_conf_xml( root )

    def __default_dependency_resolvers( self ):
        return [
            ToolShedPackageDependencyResolver(self),
            GalaxyPackageDependencyResolver(self),
            GalaxyPackageDependencyResolver(self, versionless=True),
        ]

    def __parse_resolver_conf_xml(self, root):
        """

        :param root: Object representing the root ``<dependency_resolvers>`` object in the file.
        :type root: ``xml.etree.ElementTree.Element``
        """
        resolvers = []
        resolvers_element = root
        for resolver_element in resolvers_element.getchildren():
            resolver_type = resolver_element.tag
            resolver_kwds = dict(resolver_element.items())
            resolver = self.resolver_classes[resolver_type](self, **resolver_kwds)
            resolvers.append(resolver)
        return resolvers

    def __resolvers_dict( self ):
        resolver_dict = {}
        for resolver_module in self.__resolver_modules():
            for clazz in resolver_module.__all__:
                resolver_type = getattr(clazz, 'resolver_type', None)
                if resolver_type:
                    resolver_dict[resolver_type] = clazz
        return resolver_dict

    def __resolver_modules( self ):
        import galaxy.tools.deps.resolvers
        return submodules( galaxy.tools.deps.resolvers )
