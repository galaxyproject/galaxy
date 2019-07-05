import os.path
import tempfile
from contextlib import contextmanager
from os import (
    chmod,
    environ,
    makedirs,
    stat,
    symlink,
)
from shutil import rmtree
from stat import S_IXUSR
from subprocess import PIPE, Popen

from galaxy.tools.deps import DependencyManager
from galaxy.tools.deps.requirements import (
    ToolRequirement,
    ToolRequirements
)
from galaxy.tools.deps.resolvers import NullDependency
from galaxy.tools.deps.resolvers.galaxy_packages import GalaxyPackageDependency
from galaxy.tools.deps.resolvers.lmod import LmodDependency, LmodDependencyResolver
from galaxy.tools.deps.resolvers.modules import ModuleDependency, ModuleDependencyResolver
from galaxy.util.bunch import Bunch


def test_tool_dependencies():
    # Setup directories

    with __test_base_path() as base_path:
        for name, version, sub in [("dep1", "1.0", "env.sh"), ("dep1", "2.0", "bin"), ("dep2", "1.0", None)]:
            if sub == "bin":
                p = os.path.join(base_path, name, version, "bin")
            else:
                p = os.path.join(base_path, name, version)
            try:
                makedirs(p)
            except Exception:
                pass
            if sub == "env.sh":
                __touch(os.path.join(p, "env.sh"))

        dm = __dependency_manager_for_base_path(default_base_path=base_path)
        dependency = dm.find_dep("dep1", "1.0")
        assert dependency.script == os.path.join(base_path, 'dep1', '1.0', 'env.sh')
        assert dependency.path == os.path.join(base_path, 'dep1', '1.0')
        assert dependency.version == "1.0"
        dependency = dm.find_dep("dep1", "2.0")
        assert dependency.script is None
        assert dependency.path == os.path.join(base_path, 'dep1', '2.0')
        assert dependency.version == "2.0"

        # Test default versions
        symlink(os.path.join(base_path, 'dep1', '2.0'), os.path.join(base_path, 'dep1', 'default'))
        dependency = dm.find_dep("dep1", None)
        assert dependency.version == "2.0"

        # Test default resolve will be fall back on default package dependency
        # when using the default resolver.
        dependency = dm.find_dep("dep1", "2.1")
        assert dependency.version == "2.0"  # 2.0 is defined as default_version


TEST_REPO_USER = "devteam"
TEST_REPO_NAME = "bwa"
TEST_REPO_CHANGESET = "12abcd41223da"
TEST_VERSION = "0.5.9"


def test_toolshed_set_enviornment_requiremetns():
    with __test_base_path() as base_path:
        test_repo = __build_test_repo('set_environment')
        dm = __dependency_manager_for_base_path(default_base_path=base_path)
        env_settings_dir = os.path.join(base_path, "environment_settings", TEST_REPO_NAME, TEST_REPO_USER, TEST_REPO_NAME, TEST_REPO_CHANGESET)
        os.makedirs(env_settings_dir)
        dependency = dm.find_dep(TEST_REPO_NAME, version=None, type='set_environment', installed_tool_dependencies=[test_repo])
        assert dependency.version is None
        assert dependency.script == os.path.join(env_settings_dir, "env.sh")


def test_toolshed_package_requirements():
    with __test_base_path() as base_path:
        test_repo = __build_test_repo('package', version=TEST_VERSION)
        dm = __dependency_manager_for_base_path(default_base_path=base_path)
        package_dir = __build_ts_test_package(base_path)
        dependency = dm.find_dep(TEST_REPO_NAME, version=TEST_VERSION, type='package', installed_tool_dependencies=[test_repo])
        assert dependency.version == TEST_VERSION
        assert dependency.script == os.path.join(package_dir, "env.sh")


def test_toolshed_tools_fallback_on_manual_dependencies():
    with __test_base_path() as base_path:
        dm = __dependency_manager_for_base_path(default_base_path=base_path)
        test_repo = __build_test_repo('package', version=TEST_VERSION)
        env_path = __setup_galaxy_package_dep(base_path, "dep1", "1.0")
        dependency = dm.find_dep("dep1", version="1.0", type='package', installed_tool_dependencies=[test_repo])
        assert dependency.version == "1.0"
        assert dependency.script == env_path


def test_toolshed_greater_precendence():
    with __test_base_path() as base_path:
        dm = __dependency_manager_for_base_path(default_base_path=base_path)
        test_repo = __build_test_repo('package', version=TEST_VERSION)
        ts_package_dir = __build_ts_test_package(base_path)
        gx_env_path = __setup_galaxy_package_dep(base_path, TEST_REPO_NAME, TEST_VERSION)
        ts_env_path = os.path.join(ts_package_dir, "env.sh")
        dependency = dm.find_dep(TEST_REPO_NAME, version=TEST_VERSION, type='package', installed_tool_dependencies=[test_repo])
        assert dependency.script != gx_env_path  # Not the galaxy path, it should be the tool shed path used.
        assert dependency.script == ts_env_path


def __build_ts_test_package(base_path, script_contents=''):
    package_dir = os.path.join(base_path, TEST_REPO_NAME, TEST_VERSION, TEST_REPO_USER, TEST_REPO_NAME, TEST_REPO_CHANGESET)
    __touch(os.path.join(package_dir, 'env.sh'), script_contents)
    return package_dir


REQUIREMENT_A = {'name': 'gnuplot',
                 'type': 'package',
                 'version': '4.6'}
REQUIREMENT_B = REQUIREMENT_A.copy()
REQUIREMENT_B['version'] = '4.7'


def test_tool_requirement_equality():
    a = ToolRequirement.from_dict(REQUIREMENT_A)
    assert a == ToolRequirement(**REQUIREMENT_A)
    b = ToolRequirement(**REQUIREMENT_B)
    assert a != b


def test_tool_requirements():
    tool_requirements_ab = ToolRequirements([REQUIREMENT_A, REQUIREMENT_B])
    tool_requirements_ab_dup = ToolRequirements([REQUIREMENT_A, REQUIREMENT_B])
    tool_requirements_b = ToolRequirements([REQUIREMENT_A])
    assert tool_requirements_ab == ToolRequirements([REQUIREMENT_B, REQUIREMENT_A])
    assert tool_requirements_ab == ToolRequirements([REQUIREMENT_B, REQUIREMENT_A, REQUIREMENT_A])
    assert tool_requirements_ab != tool_requirements_b
    assert len(set([tool_requirements_ab, tool_requirements_ab_dup])) == 1


def test_module_dependency_resolver():
    with __test_base_path() as temp_directory:
        module_script = _setup_module_command(temp_directory, '''
-------------------------- /soft/modules/modulefiles ---------------------------
JAGS/3.2.0-gcc45
JAGS/3.3.0-gcc4.7.2
ProbABEL/0.1-3
ProbABEL/0.1-9e
R/2.12.2
R/2.13.1
R/2.14.1
R/2.15.0
R/2.15.1
R/3.0.1(default)
abokia-blast/2.0.2-130524/ompi_intel
abokia-blast/2.0.2-130630/ompi_intel

--------------------------- /soft/intel/modulefiles ----------------------------
advisor/2013/update1    intel/11.1.075          mkl/10.2.1.017
advisor/2013/update2    intel/11.1.080          mkl/10.2.5.035
advisor/2013/update3    intel/12.0              mkl/10.2.7.041
''')
        resolver = ModuleDependencyResolver(_SimpleDependencyManager(), modulecmd=module_script)
        module = resolver.resolve(ToolRequirement(name="R", version=None, type="package"))
        assert module.module_name == "R"
        assert module.module_version is None

        module = resolver.resolve(ToolRequirement(name="R", version="3.0.1", type="package"))
        assert module.module_name == "R"
        assert module.module_version == "3.0.1"

        module = resolver.resolve(ToolRequirement(name="R", version="3.0.4", type="package"))
        assert isinstance(module, NullDependency)


def test_module_resolver_with_mapping():
    with __test_base_path() as temp_directory:
        module_script = _setup_module_command(temp_directory, '''
-------------------------- /soft/modules/modulefiles ---------------------------
blast/2.24
''')
        mapping_file = os.path.join(temp_directory, "mapping")
        with open(mapping_file, "w") as f:
            f.write('''
- from: blast+
  to: blast
''')

        resolver = ModuleDependencyResolver(_SimpleDependencyManager(), modulecmd=module_script, mapping_files=mapping_file)
        module = resolver.resolve(ToolRequirement(name="blast+", version="2.24", type="package"))
        assert module.module_name == "blast"
        assert module.module_version == "2.24", module.module_version


def test_module_resolver_with_mapping_specificity_rules():
    # If a requirement demands a specific version,
    # do not map to a different version when the version
    # has not been specified explicitly
    with __test_base_path() as temp_directory:
        module_script = _setup_module_command(temp_directory, '''
-------------------------- /soft/modules/modulefiles ---------------------------
blast/2.24
''')
        mapping_file = os.path.join(temp_directory, "mapping")
        with open(mapping_file, "w") as f:
            f.write('''
- from:
    name: blast
    unversioned: true
  to:
    name: blast
    version: 2.24
''')

        resolver = ModuleDependencyResolver(_SimpleDependencyManager(), modulecmd=module_script, mapping_files=mapping_file)
        module = resolver.resolve(ToolRequirement(name="blast", type="package"))
        assert module.module_name == "blast"
        assert module.module_version == "2.24", module.module_version  # successful resolution, because Requirement does not ask for a specific version
        module = resolver.resolve(ToolRequirement(name="blast", version="2.22", type="package"))
        assert isinstance(module, NullDependency)  # NullDependency, because we don't map `version: Null` over a Requirement that asks for a specific version


def test_module_resolver_with_mapping_versions():
    with __test_base_path() as temp_directory:
        module_script = _setup_module_command(temp_directory, '''
-------------------------- /soft/modules/modulefiles ---------------------------
blast/2.22.0-mpi
blast/2.23
blast/2.24.0-mpi
''')
        mapping_file = os.path.join(temp_directory, "mapping")
        with open(mapping_file, "w") as f:
            f.write('''
- from:
    name: blast+
    version: 2.24
  to:
    name: blast
    version: 2.24.0-mpi
- from:
    name: blast
    version: 2.22
  to:
    version: 2.22.0-mpi
''')

        resolver = ModuleDependencyResolver(_SimpleDependencyManager(), modulecmd=module_script, mapping_files=mapping_file)
        module = resolver.resolve(ToolRequirement(name="blast+", version="2.24", type="package"))
        assert module.module_name == "blast"
        assert module.module_version == "2.24.0-mpi", module.module_version

        resolver = ModuleDependencyResolver(_SimpleDependencyManager(), modulecmd=module_script, mapping_files=mapping_file)
        module = resolver.resolve(ToolRequirement(name="blast+", version="2.23", type="package"))
        assert isinstance(module, NullDependency)

        module = resolver.resolve(ToolRequirement(name="blast", version="2.22", type="package"))
        assert module.module_name == "blast"
        assert module.module_version == "2.22.0-mpi", module.module_version


def _setup_module_command(temp_directory, contents):
    module_script = os.path.join(temp_directory, "modulecmd")
    __write_script(module_script, '''#!/bin/sh
cat %s/example_output 1>&2;
''' % temp_directory)
    with open(os.path.join(temp_directory, "example_output"), "w") as f:
        # Subset of module avail from MSI cluster.
        f.write(contents)
    return module_script


def test_module_dependency():
    with __test_base_path() as temp_directory:
        # Create mock modulecmd script that just exports a variable
        # the way modulecmd sh load would, but also validate correct
        # module name and version are coming through.
        mock_modulecmd = os.path.join(temp_directory, 'modulecmd')
        __write_script(mock_modulecmd, '''#!/bin/sh
if [ $3 != "foomodule/1.0" ];
then
    exit 1
fi
echo 'FOO="bar"'
''')
        resolver = Bunch(modulecmd=mock_modulecmd, modulepath='/something')
        dependency = ModuleDependency(resolver, "foomodule", "1.0")
        __assert_foo_exported(dependency.shell_commands())


def test_lmod_dependency_resolver():
    with __test_base_path() as temp_directory:
        lmod_script = _setup_lmod_command(temp_directory, '''
/opt/apps/modulefiles:
BlastPlus/
BlastPlus/2.2.31+
BlastPlus/2.4.0+
Infernal/
Infernal/1.1.2
Mothur/
Mothur/1.33.3
Mothur/1.36.1
Mothur/1.38.1.1
''')
        resolver = LmodDependencyResolver(_SimpleDependencyManager(), lmodexec=lmod_script, modulepath='/path/to/modulefiles')

        lmod = resolver.resolve(ToolRequirement(name="Infernal", version=None, type="package"))
        assert lmod.module_name == "Infernal"
        assert lmod.module_version is None

        lmod = resolver.resolve(ToolRequirement(name="BlastPlus", version="2.4.0+", type="package"))
        assert lmod.module_name == "BlastPlus"
        assert lmod.module_version == "2.4.0+"

        lmod = resolver.resolve(ToolRequirement(name="Mothur", version="1.39", type="package"))
        assert isinstance(lmod, NullDependency)


def test_lmod_dependency_resolver_versionless():
    with __test_base_path() as temp_directory:
        lmod_script = _setup_lmod_command(temp_directory, '''
/opt/apps/modulefiles:
BlastPlus/2.4.0+
Infernal/1.1.2
Mothur/1.36.1
''')
        resolver = LmodDependencyResolver(_SimpleDependencyManager(), lmodexec=lmod_script, versionless='true', modulepath='/path/to/modulefiles')

        lmod = resolver.resolve(ToolRequirement(name="Infernal", version=None, type="package"))
        assert lmod.module_name == "Infernal"
        assert lmod.module_version is None

        lmod = resolver.resolve(ToolRequirement(name="Mothur", version="1.36.1", type="package"))
        assert lmod.module_name == "Mothur"
        assert lmod.module_version == "1.36.1"

        lmod = resolver.resolve(ToolRequirement(name="BlastPlus", version="2.3", type="package"))
        assert lmod.module_name == "BlastPlus"
        assert lmod.module_version is None

        lmod = resolver.resolve(ToolRequirement(name="Foo", version="0.1", type="package"))
        assert isinstance(lmod, NullDependency)


def test_lmod_dependency_resolver_with_mapping_file():
    with __test_base_path() as temp_directory:
        lmod_script = _setup_lmod_command(temp_directory, '''
/opt/apps/modulefiles:
BlastPlus/
BlastPlus/2.2.31+
BlastPlus/2.4.0+
Infernal/
Infernal/1.1.2
Mothur/
Mothur/1.33.3
Mothur/1.36.1
Mothur/1.38.1.1
''')
        mapping_file = os.path.join(temp_directory, "mapping")
        with open(mapping_file, "w") as f:
            f.write('''
- from:
    name: blast+
    unversioned: true
  to:
    name: BlastPlus
    version: 2.4.0+
- from:
    name: Mothur
    version: 1.38
  to:
    version: 1.38.1.1
''')

        resolver = LmodDependencyResolver(_SimpleDependencyManager(), lmodexec=lmod_script, mapping_files=mapping_file, modulepath='/path/to/modulefiles')

        lmod = resolver.resolve(ToolRequirement(name="BlastPlus", version="2.2.31+", type="package"))
        assert lmod.module_name == "BlastPlus"
        assert lmod.module_version == "2.2.31+", lmod.module_version

        lmod = resolver.resolve(ToolRequirement(name="blast+", type="package"))
        assert lmod.module_name == "BlastPlus"
        assert lmod.module_version == "2.4.0+", lmod.module_version

        lmod = resolver.resolve(ToolRequirement(name="blast+", version="2.23", type="package"))
        assert isinstance(lmod, NullDependency)

        lmod = resolver.resolve(ToolRequirement(name="Infernal", version="1.2", type="package"))
        assert isinstance(lmod, NullDependency)

        lmod = resolver.resolve(ToolRequirement(name="Mothur", version="1.38", type="package"))
        assert lmod.module_name == "Mothur"
        assert lmod.module_version == "1.38.1.1", lmod.module_version


def _setup_lmod_command(temp_directory, contents):
    lmod_script = os.path.join(temp_directory, "lmod")
    __write_script(lmod_script, '''#!/bin/sh
cat %s/lmod_example_output 1>&2;
''' % temp_directory)
    with open(os.path.join(temp_directory, "lmod_example_output"), "w") as f:
        # Subset of a "lmod -t avail" command of the LMOD environment module system.
        f.write(contents)
    return lmod_script


def test_lmod_dependency():
    with __test_base_path() as temp_directory:
        # Create mock lmod script that just exports a variable
        # the way "lmod load" would, but also validate correct
        # module name and version are coming through.
        mock_lmodexec = os.path.join(temp_directory, 'pouet')
        __write_script(mock_lmodexec, '''#!/bin/sh
if [ "$2" != "foomodule/1.0" ]; then
    exit 1
fi
echo 'FOO="bar"'
''')
        resolver = Bunch(lmodexec=mock_lmodexec, settargexec=None, modulepath='/path/to/modulefiles')
        dependency = LmodDependency(resolver, "foomodule", "1.0")
        __assert_foo_exported(dependency.shell_commands())


def __write_script(path, contents):
    with open(path, 'w') as f:
        f.write(contents)
    st = stat(path)
    chmod(path, st.st_mode | S_IXUSR)


def test_galaxy_dependency_object_script():
    with __test_base_path() as base_path:
        # Create env.sh file that just exports variable FOO and verify it
        # shell_commands export it correctly.
        env_path = __setup_galaxy_package_dep(base_path, TEST_REPO_NAME, TEST_VERSION, "export FOO=\"bar\"")
        dependency = GalaxyPackageDependency(env_path, os.path.dirname(env_path), TEST_REPO_NAME, 'package', TEST_VERSION)
        __assert_foo_exported(dependency.shell_commands())


def test_shell_commands_built():
    # Test that dependency manager builds valid shell commands for a list of
    # requirements.
    with __test_base_path() as base_path:
        dm = __dependency_manager_for_base_path(default_base_path=base_path)
        __setup_galaxy_package_dep(base_path, TEST_REPO_NAME, TEST_VERSION, contents="export FOO=\"bar\"")
        mock_requirements = ToolRequirements([{'type': 'package', 'version': TEST_VERSION, 'name': TEST_REPO_NAME}])
        commands = dm.dependency_shell_commands(mock_requirements)
        __assert_foo_exported(commands)


def __assert_foo_exported(commands):
    command = ["bash", "-c", "%s; echo \"$FOO\"" % "".join(commands)]
    process = Popen(command, stdout=PIPE)
    output = process.communicate()[0].strip()
    assert output == b'bar', "Command %s exports FOO as %s, not bar" % (command, output)


def __setup_galaxy_package_dep(base_path, name, version, contents=""):
    dep_directory = os.path.join(base_path, name, version)
    env_path = os.path.join(dep_directory, "env.sh")
    __touch(env_path, contents)
    return env_path


def __touch(fname, data=None):
    dirname = os.path.dirname(fname)
    if not os.path.exists(dirname):
        makedirs(dirname)
    f = open(fname, 'w')
    try:
        if data:
            f.write(data)
    finally:
        f.close()


def __build_test_repo(type, version=None):
    return Bunch(
        owner=TEST_REPO_USER,
        name=TEST_REPO_NAME,
        type=type,
        version=version,
        tool_shed_repository=Bunch(
            owner=TEST_REPO_USER,
            name=TEST_REPO_NAME,
            installed_changeset_revision=TEST_REPO_CHANGESET
        )
    )


@contextmanager
def __test_base_path():
    base_path = tempfile.mkdtemp()
    try:
        yield base_path
    finally:
        rmtree(base_path)


def test_parse():
    with __parse_resolvers('''<dependency_resolvers>
  <tool_shed_packages />
  <galaxy_packages />
</dependency_resolvers>
''') as dependency_resolvers:
        assert 'ToolShed' in dependency_resolvers[0].__class__.__name__
        assert 'Galaxy' in dependency_resolvers[1].__class__.__name__

    with __parse_resolvers('''<dependency_resolvers>
  <galaxy_packages />
  <tool_shed_packages />
</dependency_resolvers>
''') as dependency_resolvers:
        assert 'Galaxy' in dependency_resolvers[0].__class__.__name__
        assert 'ToolShed' in dependency_resolvers[1].__class__.__name__

    with __parse_resolvers('''<dependency_resolvers>
  <galaxy_packages />
  <tool_shed_packages />
  <galaxy_packages versionless="true" />
</dependency_resolvers>
''') as dependency_resolvers:
        assert not dependency_resolvers[0].versionless
        assert dependency_resolvers[2].versionless

    with __parse_resolvers('''<dependency_resolvers>
  <galaxy_packages />
  <tool_shed_packages />
  <galaxy_packages base_path="/opt/galaxy/legacy/"/>
</dependency_resolvers>
''') as dependency_resolvers:
        # Unspecified base_paths are both default_base_paths
        assert dependency_resolvers[0].base_path == dependency_resolvers[1].base_path
        # Can specify custom base path...
        assert dependency_resolvers[2].base_path == "/opt/galaxy/legacy"
        # ... that is different from the default.
        assert dependency_resolvers[0].base_path != dependency_resolvers[2].base_path


def test_uses_tool_shed_dependencies():
    with __dependency_manager('''<dependency_resolvers>
  <galaxy_packages />
</dependency_resolvers>
''') as dm:
        assert not dm.uses_tool_shed_dependencies()

    with __dependency_manager('''<dependency_resolvers>
  <tool_shed_packages />
</dependency_resolvers>
''') as dm:
        assert dm.uses_tool_shed_dependencies()


def test_config_module_defaults():
    with __parse_resolvers('''<dependency_resolvers>
  <modules prefetch="false" />
</dependency_resolvers>
''') as dependency_resolvers:
        module_resolver = dependency_resolvers[0]
        assert module_resolver.module_checker.__class__.__name__ == "AvailModuleChecker"


def test_config_modulepath():
    # Test reads and splits MODULEPATH if modulepath is not specified.
    with __parse_resolvers('''<dependency_resolvers>
  <modules find_by="directory" modulepath="/opt/modules/modulefiles:/usr/local/modules/modulefiles" />
</dependency_resolvers>
''') as dependency_resolvers:
        assert dependency_resolvers[0].module_checker.directories == ["/opt/modules/modulefiles", "/usr/local/modules/modulefiles"]


def test_config_MODULEPATH():
    # Test reads and splits MODULEPATH if modulepath is not specified.
    with __environ({"MODULEPATH": "/opt/modules/modulefiles:/usr/local/modules/modulefiles"}):
        with __parse_resolvers('''<dependency_resolvers>
  <modules find_by="directory" />
</dependency_resolvers>
''') as dependency_resolvers:
            assert dependency_resolvers[0].module_checker.directories == ["/opt/modules/modulefiles", "/usr/local/modules/modulefiles"]


def test_config_MODULESHOME():
    # Test fallbacks to read MODULESHOME if modulepath is not specified and
    # neither is MODULEPATH.
    with __environ({"MODULESHOME": "/opt/modules"}, remove="MODULEPATH"):
        with __parse_resolvers('''<dependency_resolvers>
  <modules find_by="directory" />
</dependency_resolvers>
''') as dependency_resolvers:
            assert dependency_resolvers[0].module_checker.directories == ["/opt/modules/modulefiles"]


def test_config_module_directory_searcher():
    with __parse_resolvers('''<dependency_resolvers>
  <modules find_by="directory" modulepath="/opt/Modules/modulefiles" />
</dependency_resolvers>
''') as dependency_resolvers:
        module_resolver = dependency_resolvers[0]
        assert module_resolver.module_checker.directories == ["/opt/Modules/modulefiles"]


@contextmanager
def __environ(values, remove=[]):
    """
    Modify the environment for a test, adding/updating values in dict `values` and
    removing any environment variables mentioned in list `remove`.
    """
    new_keys = set(environ.keys()) - set(values.keys())
    old_environ = environ.copy()
    try:
        environ.update(values)
        for to_remove in remove:
            try:
                del environ[remove]
            except KeyError:
                pass
        yield
    finally:
        environ.update(old_environ)
        for key in new_keys:
            del environ[key]


@contextmanager
def __parse_resolvers(xml_content):
    with __dependency_manager(xml_content) as dm:
        yield dm.dependency_resolvers


@contextmanager
def __dependency_manager(xml_content):
    with __test_base_path() as base_path:
        with tempfile.NamedTemporaryFile('w+') as tmp:
            tmp.write(xml_content)
            tmp.flush()
            dm = __dependency_manager_for_base_path(default_base_path=base_path, conf_file=tmp.name)
            yield dm


def __dependency_manager_for_base_path(default_base_path, conf_file=None):
    return DependencyManager(default_base_path=default_base_path, conf_file=conf_file, app_config={"conda_auto_init": False})


class _SimpleDependencyManager(object):

    def get_resolver_option(self, resolver, key, explicit_resolver_options={}):
        return explicit_resolver_options.get(key)
