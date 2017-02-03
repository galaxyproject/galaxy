"""
This file contains the outline of an implementation to load environment modules
(http://modules.sourceforge.net/).

This is a community contributed feature and the core Galaxy team does utilize
it, hence support for it will be minimal. The Galaxy team eagerly welcomes
community contribution and maintenance however.
"""
import logging
from os import environ, pathsep
from os.path import exists, isdir, join
from subprocess import PIPE, Popen

from six import StringIO

from ..resolvers import (
    Dependency,
    DependencyResolver,
    MappableDependencyResolver,
    NullDependency,
)

log = logging.getLogger( __name__ )

DEFAULT_MODULECMD_PATH = "modulecmd"  # Just check path
DEFAULT_MODULE_PATH = '/usr/share/modules/modulefiles'
DEFAULT_INDICATOR = '(default)'
DEFAULT_MODULE_PREFETCH = "true"
UNKNOWN_FIND_BY_MESSAGE = "ModuleDependencyResolver does not know how to find modules by [%s], find_by should be one of %s"


class ModuleDependencyResolver(DependencyResolver, MappableDependencyResolver):
    dict_collection_visible_keys = DependencyResolver.dict_collection_visible_keys + ['base_path', 'modulepath']
    resolver_type = "modules"

    def __init__(self, dependency_manager, **kwds):
        self._setup_mapping(dependency_manager, **kwds)
        self.versionless = _string_as_bool(kwds.get('versionless', 'false'))
        find_by = kwds.get('find_by', 'avail')
        prefetch = _string_as_bool(kwds.get('prefetch', DEFAULT_MODULE_PREFETCH))
        self.modulecmd = kwds.get('modulecmd', DEFAULT_MODULECMD_PATH)
        self.modulepath = kwds.get('modulepath', self.__default_modulespath())
        self.default_indicator = kwds.get('default_indicator', DEFAULT_INDICATOR)
        if find_by == 'directory':
            self.module_checker = DirectoryModuleChecker(self, self.modulepath, prefetch)
        elif find_by == 'avail':
            self.module_checker = AvailModuleChecker(self, self.modulepath, prefetch, self.default_indicator)
        else:
            raise Exception(UNKNOWN_FIND_BY_MESSAGE % (find_by, ["avail", "directory"]))

    def __default_modulespath(self):
        if 'MODULEPATH' in environ:
            module_path = environ['MODULEPATH']
        elif 'MODULESHOME' in environ:
            module_path = join(environ['MODULESHOME'], 'modulefiles')
        else:
            module_path = DEFAULT_MODULE_PATH
        return module_path

    def resolve(self, requirement, **kwds):
        requirement = self._expand_mappings(requirement)
        name, version, type = requirement.name, requirement.version, requirement.type

        if type != "package":
            return NullDependency(version=version, name=name)

        if self.__has_module(name, version):
            return ModuleDependency(self, name, version, exact=True)
        elif self.versionless and self.__has_module(name, None):
            return ModuleDependency(self, name, None, exact=False)

        return NullDependency(version=version, name=name)

    def __has_module(self, name, version):
        return self.module_checker.has_module(name, version)


class DirectoryModuleChecker(object):
    """Finds module by path.

    Searches the paths listed in modulepath to for a file or directory matching the module name.
    If the version=True, searches for files named module/version."""
    def __init__(self, module_dependency_resolver, modulepath, prefetch):
        self.module_dependency_resolver = module_dependency_resolver
        self.directories = modulepath.split(pathsep)
        if prefetch:
            log.warning("Created module dependency resolver with prefetch enabled, but directory module checker does not support this.")

    def has_module(self, module, version):
        has_module = False
        for directory in self.directories:
            module_directory = join(directory, module)
            has_module_directory = isdir( module_directory )
            if not version:
                has_module = has_module_directory or exists(module_directory)  # could be a bare modulefile
            else:
                modulefile = join(  module_directory, version )
                has_modulefile = exists( modulefile )
                has_module = has_module_directory and has_modulefile
            if has_module:
                break
        return has_module


class AvailModuleChecker(object):
    """Finds modules by searching output of 'module avail'.

    Parses the Environment Modules 'module avail' output, splitting
    module names into module and version on '/' and discarding a postfix matching default_indicator
    (by default '(default)'. Matching is done using the module and
    (if version=True) the module version."""
    def __init__(self, module_dependency_resolver, modulepath, prefetch, default_indicator=DEFAULT_INDICATOR):
        self.module_dependency_resolver = module_dependency_resolver
        self.modulepath = modulepath
        self.default_indicator = default_indicator
        if prefetch:
            prefetched_modules = []
            for module in self.__modules():
                prefetched_modules.append(module)
        else:
            prefetched_modules = None
        self.prefetched_modules = prefetched_modules

    def has_module(self, module, version):
        module_generator = self.prefetched_modules
        if module_generator is None:
            module_generator = self.__modules()

        for module_name, module_version in module_generator:
            names_match = module == module_name
            module_match = names_match and (version is None or module_version == version)
            if module_match:
                return True
        return False

    def __modules(self):
        raw_output = self.__module_avail_output().decode("utf-8")
        for line in StringIO(raw_output):
            line = line and line.strip()
            if not line or line.startswith("-"):
                continue

            line_modules = line.split()
            for module in line_modules:
                if module.endswith(self.default_indicator):
                    module = module[0:-len(self.default_indicator)].strip()
                module_parts = module.split('/')
                module_version = None
                if len(module_parts) == 2:
                    module_version = module_parts[1]
                module_name = module_parts[0]
                yield module_name, module_version

    def __module_avail_output(self):
        avail_command = [self.module_dependency_resolver.modulecmd, 'sh', 'avail']
        return Popen(avail_command, stderr=PIPE, env={'MODULEPATH': self.modulepath}).communicate()[1]


class ModuleDependency(Dependency):
    """Converts module dependencies into shell expressions using modulecmd.

    Using Environment Modules' 'modulecmd' (specifically 'modulecmd sh load') to
    convert module specifications into shell expressions for inclusion in
    the script used to run a tool in Galaxy."""
    dict_collection_visible_keys = Dependency.dict_collection_visible_keys + ['module_name', 'module_version']
    dependency_type = 'module'

    def __init__(self, module_dependency_resolver, module_name, module_version=None, exact=True):
        self.module_dependency_resolver = module_dependency_resolver
        self.module_name = module_name
        self.module_version = module_version
        self._exact = exact

    @property
    def exact(self):
        return self._exact

    def shell_commands(self, requirement):
        module_to_load = self.module_name
        if self.module_version:
            module_to_load = '%s/%s' % (self.module_name, self.module_version)
        command = 'MODULEPATH=%s; export MODULEPATH; eval `%s sh load %s`' % (self.module_dependency_resolver.modulepath,
                                                                              self.module_dependency_resolver.modulecmd,
                                                                              module_to_load)
        return command


def _string_as_bool( value ):
    return str( value ).lower() == "true"


__all__ = ('ModuleDependencyResolver', )
