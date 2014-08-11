from os.path import join
from contextlib import contextmanager
from galaxy.util import parse_xml_string

from tool_shed.galaxy_install.tool_dependencies.env_manager import EnvManager
from tool_shed.galaxy_install.tool_dependencies.recipe.env_file_builder import EnvFileBuilder

TEST_DEPENDENCIES_DIR = "/opt/galaxy/dependencies"
TEST_INSTALL_DIR = "%s/test_install_dir" % TEST_DEPENDENCIES_DIR


class MockApp( object ):

    def __init__( self ):
        pass

def test_create_or_update_env_shell_file():
    test_path = "/usr/share/R/libs"
    env_file_builder = EnvFileBuilder( test_path )
    line, path = env_file_builder.create_or_update_env_shell_file( TEST_INSTALL_DIR, dict( action="append_to", name="R_LIBS", value=test_path ) )
    assert path == join( TEST_INSTALL_DIR, "env.sh" )
    assert line == "R_LIBS=$R_LIBS:/usr/share/R/libs; export R_LIBS"

    line, path = env_file_builder.create_or_update_env_shell_file( TEST_INSTALL_DIR, dict( action="prepend_to", name="R_LIBS", value=test_path ) )
    assert path == join( TEST_INSTALL_DIR, "env.sh" )
    assert line == "R_LIBS=/usr/share/R/libs:$R_LIBS; export R_LIBS"

    line, path = env_file_builder.create_or_update_env_shell_file( TEST_INSTALL_DIR, dict( action="set_to", name="R_LIBS", value=test_path ) )
    assert path == join( TEST_INSTALL_DIR, "env.sh" )
    assert line == "R_LIBS=/usr/share/R/libs; export R_LIBS"

    line, path = env_file_builder.create_or_update_env_shell_file( TEST_INSTALL_DIR, dict( action="source", value=test_path ) )
    assert path == join( TEST_INSTALL_DIR, "env.sh" )
    assert line == "if [ -f /usr/share/R/libs ] ; then . /usr/share/R/libs ; fi"

def test_get_env_shell_file_paths_from_setup_environment_elem():
    xml = """<action name="setup_r_environment">
        <repository name="package_r_3_0_1" owner="bgruening" toolshed="toolshed.g2.bx.psu.edu" changeset_revision="1234567">
            <package name="R" version="3.0.1" />
        </repository>
    </action>
    """
    mock_app = MockApp()
    action_elem = parse_xml_string( xml )
    required_for_install_env_sh = '/path/to/existing.sh'
    all_env_paths = [ required_for_install_env_sh ]
    action_dict = {}
    env_manager = EnvManager( mock_app )

    r_env_sh = '/path/to/go/env.sh'

    def mock_get_env_shell_file_paths( elem ):
        assert elem.get( 'name' ) == "package_r_3_0_1"
        return [ r_env_sh ]

    with __mock_common_util_method( env_manager, "get_env_shell_file_paths", mock_get_env_shell_file_paths ):
        env_manager.get_env_shell_file_paths_from_setup_environment_elem( all_env_paths, action_elem, action_dict )
        ## Verify old env files weren't deleted.
        assert required_for_install_env_sh in all_env_paths
        ## Verify new ones added.
        assert r_env_sh in all_env_paths
        ## env_shell_file_paths includes everything
        assert all( [ env in action_dict[ 'env_shell_file_paths' ] for env in all_env_paths ] )

        ## action_shell_file_paths includes only env files defined in
        ## inside the setup_ action element.
        assert required_for_install_env_sh not in action_dict[ 'action_shell_file_paths' ]
        assert r_env_sh in action_dict[ 'action_shell_file_paths' ]

## Poor man's mocking. Need to get a real mocking library as real Galaxy development
## dependnecy.
@contextmanager
def __mock_common_util_method( env_manager, name, mock_method ):
    real_method = getattr( env_manager, name )
    try:
        setattr( env_manager, name, mock_method )
        yield
    finally:
        setattr( env_manager, name, real_method )
