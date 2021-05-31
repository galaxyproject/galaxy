"""
This is a prototype dependency resolver to be able to use the "LMOD environment modules system" from TACC to solve package requirements

LMOD official website: https://www.tacc.utexas.edu/research-development/tacc-projects/lmod

LMOD @ Github: https://github.com/TACC/Lmod

"""
import logging
from io import StringIO
from os import getenv
from os.path import exists
from subprocess import (
    PIPE,
    Popen
)

from . import (
    Dependency,
    DependencyResolver,
    MappableDependencyResolver,
    NullDependency,
)

log = logging.getLogger(__name__)

DEFAULT_LMOD_PATH = getenv('LMOD_CMD')
DEFAULT_SETTARG_PATH = getenv('LMOD_SETTARG_CMD')
DEFAULT_MODULEPATH = getenv('MODULEPATH')
DEFAULT_MAPPING_FILE = 'config/lmod_modules_mapping.yml'
INVALID_LMOD_PATH_MSG = "The following LMOD executable could not be found: %s. Either your LMOD Dependency Resolver is misconfigured or LMOD is improperly installed on your system !"
EMPTY_MODULEPATH_MSG = "No valid LMOD MODULEPATH defined ! Either your LMOD Dependency Resolver is misconfigured or LMOD is improperly installed on your system !"


class LmodDependencyResolver(DependencyResolver, MappableDependencyResolver):
    """Dependency resolver based on the LMOD environment modules system"""

    dict_collection_visible_keys = DependencyResolver.dict_collection_visible_keys + ['base_path', 'modulepath']
    resolver_type = "lmod"

    def __init__(self, dependency_manager, **kwds):
        # Mapping file management
        self._set_default_mapping_file(kwds)
        self._setup_mapping(dependency_manager, **kwds)

        # Other attributes
        self.versionless = _string_as_bool(kwds.get('versionless', 'false'))
        self.lmodexec = kwds.get('lmodexec', DEFAULT_LMOD_PATH)
        self.settargexec = kwds.get('settargexec', DEFAULT_SETTARG_PATH)
        self.modulepath = kwds.get('modulepath', DEFAULT_MODULEPATH)
        self.module_checker = AvailModuleChecker(self, self.modulepath)

    def _set_default_mapping_file(self, resolver_attributes):
        if 'mapping_files' not in resolver_attributes:
            if exists(DEFAULT_MAPPING_FILE):
                resolver_attributes['mapping_files'] = DEFAULT_MAPPING_FILE

    def resolve(self, requirement, **kwds):
        requirement = self._expand_mappings(requirement)
        name, version, type = requirement.name, requirement.version, requirement.type

        if type != "package":
            return NullDependency(version=version, name=name)

        if self.__has_module(name, version):
            return LmodDependency(self, name, version, exact=True, dependency_resolver=self)
        elif self.versionless and self.__has_module(name, None):
            return LmodDependency(self, name, None, exact=False, dependency_resolver=self)

        return NullDependency(version=version, name=name)

    def __has_module(self, name, version):
        return self.module_checker.has_module(name, version)


class AvailModuleChecker:
    """Parses the output of Lmod 'module avail' command to get the list of available modules."""

    def __init__(self, lmod_dependency_resolver, modulepath):
        self.lmod_dependency_resolver = lmod_dependency_resolver
        self.modulepath = modulepath

    def has_module(self, module, version):
        # When version is None (No specific version required by the wrapper -or- versionless is set to 'true'), we only get the list of default modules
        # We get the full list of modules otherwise
        if version is None:
            available_modules = self.__get_list_of_available_modules(True)
        else:
            available_modules = self.__get_list_of_available_modules(False)

        # Is the required module in the list of avaialable modules ?
        for module_name, module_version in available_modules:
            names_match = module == module_name
            module_match = names_match and (version is None or module_version == version)
            if module_match:
                return True
        return False

    def __get_list_of_available_modules(self, default_version_only=False):
        # Get the results of the "module avail" command in an easy to parse format
        # Note that since "module" is actually a bash function, we are directy executing the underlying executable instead
        raw_output = self.__get_module_avail_command_output(default_version_only).decode("utf-8")

        # Parse the result
        for line in StringIO(raw_output):
            # Clean line and discard non-module lines
            line = line and line.strip()
            if not line or line.startswith("/"):
                continue

            # Split module lines by / to separate the module name from the module version
            # Module without version are discarded
            module_parts = line.split('/')
            if len(module_parts) == 2:
                yield module_parts[0], module_parts[1]

    def __get_module_avail_command_output(self, default_version_only=False):
        # Check if the LMOD executable is available (ie. if both LMOD and the lmod dependency resolver are both setup properly)
        lmodexec = self.lmod_dependency_resolver.lmodexec
        if not exists(lmodexec):
            raise Exception(INVALID_LMOD_PATH_MSG % lmodexec)

        # Check if the MODULEPATH environment
        if self.modulepath == "" or self.modulepath is None:
            raise Exception(EMPTY_MODULEPATH_MSG)

        # Build command line
        if default_version_only:
            module_avail_command = [lmodexec, '-t', '-d', 'avail']
        else:
            module_avail_command = [lmodexec, '-t', 'avail']

        # The list of avaialable modules is actually printed on stderr and not stdout for module commands
        return Popen(module_avail_command, stdout=PIPE, stderr=PIPE, env={'MODULEPATH': self.modulepath}, close_fds=True).communicate()[1]


class LmodDependency(Dependency):
    """Prepare the commands required to solve the dependency and add them to the script used to run a tool in Galaxy."""

    dict_collection_visible_keys = Dependency.dict_collection_visible_keys + ['module_name', 'module_version', 'dependency_resolver']
    dependency_type = 'lmod'

    def __init__(self, lmod_dependency_resolver, module_name, module_version=None, exact=True, dependency_resolver=None):
        self.lmod_dependency_resolver = lmod_dependency_resolver
        self.module_name = module_name
        self.module_version = module_version
        self._exact = exact
        self.dependency_resolver = dependency_resolver

    @property
    def name(self):
        return self.module_name

    @property
    def version(self):
        return self.module_version

    @property
    def exact(self):
        return self._exact

    def shell_commands(self):
        # Get the full module name in the form "tool_name/tool_version"
        module_to_load = self.module_name
        if self.module_version:
            module_to_load = f'{self.module_name}/{self.module_version}'

        # Build the list of command to add to run script
        # Note that since "module" is actually a bash function, we are directy executing the underlying executable instead
        # - Set the MODULEPATH environment variable
        command = f'MODULEPATH={self.lmod_dependency_resolver.modulepath}; '
        command += 'export MODULEPATH; '
        # - Execute the "module load" command (or rather the "/path/to/lmod load" command)
        command += f'eval `{self.lmod_dependency_resolver.lmodexec} load {module_to_load}` '
        # - Execute the "settarg" command in addition if needed
        if self.lmod_dependency_resolver.settargexec is not None:
            command += f'&& eval `{self.lmod_dependency_resolver.settargexec} -s sh`'

        return command


def _string_as_bool(value):
    return str(value).lower() == "true"


__all__ = ('LmodDependencyResolver', )
