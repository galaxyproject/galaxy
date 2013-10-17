import tempfile
import os.path
from os import makedirs, symlink
from shutil import rmtree
from galaxy.tools.deps import DependencyManager
from galaxy.util.bunch import Bunch
from contextlib import contextmanager


def test_tool_dependencies():
    # Setup directories

    with __test_base_path() as base_path:
        for name, version, sub in [ ( "dep1", "1.0", "env.sh" ), ( "dep1", "2.0", "bin" ), ( "dep2", "1.0", None ) ]:
            if sub == "bin":
                p = os.path.join( base_path, name, version, "bin" )
            else:
                p = os.path.join( base_path, name, version )
            try:
                makedirs( p )
            except:
                pass
            if sub == "env.sh":
                __touch( os.path.join( p, "env.sh" ) )

        dm = DependencyManager( default_base_path=base_path )
        d1_script, d1_path, d1_version = dm.find_dep( "dep1", "1.0" )
        assert d1_script == os.path.join( base_path, 'dep1', '1.0', 'env.sh' )
        assert d1_path == os.path.join( base_path, 'dep1', '1.0' )
        assert d1_version == "1.0"
        d2_script, d2_path, d2_version = dm.find_dep( "dep1", "2.0" )
        assert d2_script == None
        assert d2_path == os.path.join( base_path, 'dep1', '2.0' )
        assert d2_version == "2.0"

        ## Test default versions
        symlink( os.path.join( base_path, 'dep1', '2.0'), os.path.join( base_path, 'dep1', 'default' ) )
        default_script, default_path, default_version = dm.find_dep( "dep1", None )
        assert default_version == "2.0"

        ## Test default will not be fallen back upon by default
        default_script, default_path, default_version = dm.find_dep( "dep1", "2.1" )
        assert default_script == None
        assert default_version == None


TEST_REPO_USER = "devteam"
TEST_REPO_NAME = "bwa"
TEST_REPO_CHANGESET = "12abcd41223da"
TEST_VERSION = "0.5.9"


def test_toolshed_set_enviornment_requiremetns():
    with __test_base_path() as base_path:
        test_repo = __build_test_repo('set_environment')
        dm = DependencyManager( default_base_path=base_path )
        env_settings_dir = os.path.join(base_path, "environment_settings", TEST_REPO_NAME, TEST_REPO_USER, TEST_REPO_NAME, TEST_REPO_CHANGESET)
        os.makedirs(env_settings_dir)
        d1_script, d1_path, d1_version = dm.find_dep( TEST_REPO_NAME, version=None, type='set_environment', installed_tool_dependencies=[test_repo] )
        assert d1_version == None
        assert d1_script == os.path.join(env_settings_dir, "env.sh"), d1_script


def test_toolshed_package_requirements():
    with __test_base_path() as base_path:
        test_repo = __build_test_repo('package', version=TEST_VERSION)
        dm = DependencyManager( default_base_path=base_path )
        package_dir = __build_ts_test_package(base_path)
        d1_script, d1_path, d1_version = dm.find_dep( TEST_REPO_NAME, version=TEST_VERSION, type='package', installed_tool_dependencies=[test_repo] )
        assert d1_version == TEST_VERSION, d1_version
        assert d1_script == os.path.join(package_dir, "env.sh"), d1_script


def test_toolshed_tools_fallback_on_manual_dependencies():
    with __test_base_path() as base_path:
        dm = DependencyManager( default_base_path=base_path )
        test_repo = __build_test_repo('package', version=TEST_VERSION)
        env_path = __setup_galaxy_package_dep(base_path, "dep1", "1.0")
        d1_script, d1_path, d1_version = dm.find_dep( "dep1", version="1.0", type='package', installed_tool_dependencies=[test_repo] )
        assert d1_version == "1.0"
        assert d1_script == env_path


def test_toolshed_greater_precendence():
    with __test_base_path() as base_path:
        dm = DependencyManager( default_base_path=base_path )
        test_repo = __build_test_repo('package', version=TEST_VERSION)
        ts_package_dir = __build_ts_test_package(base_path)
        gx_env_path = __setup_galaxy_package_dep(base_path, TEST_REPO_NAME, TEST_VERSION)
        ts_env_path = os.path.join(ts_package_dir, "env.sh")
        d1_script, d1_path, d1_version = dm.find_dep( TEST_REPO_NAME, version=TEST_VERSION, type='package', installed_tool_dependencies=[test_repo] )
        assert d1_script != gx_env_path  # Not the galaxy path, it should be the tool shed path used.
        assert d1_script == ts_env_path


def __build_ts_test_package(base_path, script_contents=''):
    package_dir = os.path.join(base_path, TEST_REPO_NAME, TEST_VERSION, TEST_REPO_USER, TEST_REPO_NAME, TEST_REPO_CHANGESET)
    __touch(os.path.join(package_dir, 'env.sh'), script_contents)
    return package_dir


def __setup_galaxy_package_dep(base_path, name, version, contents=""):
    dep_directory = os.path.join( base_path, name, version )
    env_path = os.path.join( dep_directory, "env.sh" )
    __touch( env_path, contents )
    return env_path


def __touch( fname, data=None ):
    dirname = os.path.dirname( fname )
    if not os.path.exists( dirname ):
        makedirs( dirname )
    f = open( fname, 'w' )
    try:
        if data:
            f.write( data )
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
  <tool_shed_package />
  <galaxy_package />
</dependency_resolvers>
''') as dependency_resolvers:
        assert 'ToolShed' in dependency_resolvers[0].__class__.__name__
        assert 'Galaxy' in dependency_resolvers[1].__class__.__name__

    with __parse_resolvers('''<dependency_resolvers>
  <galaxy_package />
  <tool_shed_package />
</dependency_resolvers>
''') as dependency_resolvers:
        assert 'Galaxy' in dependency_resolvers[0].__class__.__name__
        assert 'ToolShed' in dependency_resolvers[1].__class__.__name__

    with __parse_resolvers('''<dependency_resolvers>
  <galaxy_package />
  <tool_shed_package />
  <galaxy_package versionless="true" />
</dependency_resolvers>
''') as dependency_resolvers:
        assert not dependency_resolvers[0].versionless
        assert dependency_resolvers[2].versionless


@contextmanager
def __parse_resolvers(xml_content):
    with __test_base_path() as base_path:
        f = tempfile.NamedTemporaryFile()
        f.write(xml_content)
        f.flush()
        dm = DependencyManager( default_base_path=base_path, conf_file=f.name )
        yield dm.dependency_resolvers

