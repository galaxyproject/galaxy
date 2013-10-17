"""
This file contains the outline of an implementation to load environment modules
(http://modules.sourceforge.net/).

This is a community contributed feature and the core Galaxy team does utilize
it, hence support for it will be minimal. The Galaxy team eagerly welcomes
community contribution and maintenance however.
"""
from os.path import exists, isdir, join
from StringIO import StringIO
from subprocess import Popen, PIPE

from ..resolvers import DependencyResolver, INDETERMINATE_DEPENDENCY, Dependency
from galaxy.util import string_as_bool

import logging
log = logging.getLogger( __name__ )


DEFAULT_MODULE_COMMAND = 'module'
DEFAULT_MODULE_DIRECTORY = '/usr/share/modules/modulefiles'
DEFAULT_INDICATOR = '(default)'
DEFAULT_MODULE_PREFETCH = "true"
UNKNOWN_FIND_BY_MESSAGE = "ModuleDependencyResolver does not know how to find modules by [%s], find_by should be one of %s"


class ModuleDependencyResolver(DependencyResolver):
    resolver_type = "modules"

    def __init__(self, dependency_manager, **kwds):
        self.module_command = kwds.get('command', DEFAULT_MODULE_COMMAND)
        self.versionless = string_as_bool(kwds.get('versionless', 'false'))
        find_by = kwds.get('find_by', 'avail')
        prefetch = string_as_bool(kwds.get('prefetch', DEFAULT_MODULE_PREFETCH))
        if find_by == 'directory':
            directory = kwds.get('directory', DEFAULT_MODULE_DIRECTORY)
            self.module_checker = DirectoryModuleChecker(self, directory, prefetch)
        elif find_by == 'avail':
            self.module_checker = AvailModuleChecker(self, prefetch)
        else:
            raise Exception(UNKNOWN_FIND_BY_MESSAGE % (find_by, ["avail", "directory"]))

    def resolve( self, name, version, type, **kwds ):
        if type != "package":
            return INDETERMINATE_DEPENDENCY

        if self.versionless:
            version = None

        if self.__has_module(name, version):
            return ModuleDependency(self, name, version)

        return INDETERMINATE_DEPENDENCY

    def __has_module(self, name, version):
        return self.module_checker.has_module(name, version)


class DirectoryModuleChecker(object):

    def __init__(self, module_dependency_resolver, directory, prefetch):
        self.module_dependency_resolver = module_dependency_resolver
        self.directory = directory
        if prefetch:
            log.warn("Created module dependency resolver with prefetch enabled, but directory module checker does not support this.")
            pass

    def has_module(self, module, version):
        module_directory = join(self.directory, module)
        has_module_directory = isdir( join( self.directory, module ) )
        if not version:
            has_module = has_module_directory
        else:
            modulefile = join(  module_directory, version )
            has_modulefile = exists( modulefile )
            has_module = has_module_directory and has_modulefile
        return has_module


class AvailModuleChecker(object):

    def __init__(self, module_dependency_resolver, prefetch):
        self.module_dependency_resolver = module_dependency_resolver
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
            module_match = names_match and (version == None or module_version == version)
            if module_match:
                return True
        return False

    def __modules(self):
        raw_output = self.__module_avail_ouptut()
        for line in StringIO(raw_output):
            line = line and line.strip()
            if not line or line.startswith("-"):
                continue

            line_modules = line.split()
            for module in line_modules:
                if module.endswith(DEFAULT_INDICATOR):
                    module = module[0:-len(DEFAULT_INDICATOR)].strip()
                module_parts = module.split('/')
                module_version = None
                if len(module_parts) == 2:
                    module_version = module_parts[1]
                module_name = module_parts[0]
                yield module_name, module_version

    def __module_avail_ouptut(self):
        avail_command = '%s avail' % self.module_dependency_resolver.module_command
        return Popen([avail_command], shell=True, stderr=PIPE).communicate()[1]


class ModuleDependency(Dependency):

    def __init__(self, module_dependency_resolver, module_name, module_version=None):
        self.module_dependency_resolver = module_dependency_resolver
        self.module_name = module_name
        self.module_version = module_version

    def shell_commands(self, requirement):
        command = '%s load %s' % (self.module_dependency_resolver.module_command, self.module_name)
        if self.module_version:
            command = '%s/%s' % self.module_version
        return command

__all__ = [ModuleDependencyResolver]
