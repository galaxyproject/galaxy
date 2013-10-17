"""
Dependency management for tools.
"""

import os.path

import logging
log = logging.getLogger( __name__ )

from galaxy.util import parse_xml
from .resolvers import INDETERMINATE_DEPENDENCY
from .resolvers.galaxy_packages import GalaxyPackageDependencyResolver
from .resolvers.tool_shed_packages import ToolShedPackageDependencyResolver
from .resolvers.modules import ModuleDependencyResolver


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
        self.dependency_resolvers = self.__build_dependency_resolvers( conf_file )


    def find_dep( self, name, version=None, type='package', **kwds ):
        for resolver in self.dependency_resolvers:
            dependency = resolver.resolve( name, version, type, **kwds )
            if dependency != INDETERMINATE_DEPENDENCY:
                return dependency
        return INDETERMINATE_DEPENDENCY

    def __build_dependency_resolvers( self, conf_file ):
        if not conf_file or not os.path.exists( conf_file ):
            return self.__default_dependency_resolvers()
        tree = parse_xml( conf_file )
        return self.__parse_resolver_conf_xml( tree )

    def __default_dependency_resolvers( self ):
        return [
            ToolShedPackageDependencyResolver(self),
            GalaxyPackageDependencyResolver(self),
        ]

    def __parse_resolver_conf_xml(self, tree):
        """

        :param tree: Object representing the root ``<dependency_resolvers>`` object in the file.
        :type tree: ``xml.etree.ElementTree.Element``
        """
        resolvers = []
        resolvers_element = tree.getroot()
        for resolver_element in resolvers_element.getchildren():
            resolver_type = resolver_element.tag
            resolver_kwds = dict(resolver_element.items())
            resolver = RESOLVER_CLASSES[resolver_type](self, **resolver_kwds)
            resolvers.append(resolver)
        return resolvers

RESOLVER_CLASSES = {
    'tool_shed_packages': ToolShedPackageDependencyResolver,
    'galaxy_packages': GalaxyPackageDependencyResolver,
    'modules': ModuleDependencyResolver,
}
