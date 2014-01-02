from contextlib import contextmanager
from tool_shed.galaxy_install.tool_dependencies import fabric_util


def test_env_file_builder():
    install_dir = "/opt/galaxy/dependencies/foo/"
    env_file_builder = fabric_util.EnvFileBuilder( install_dir )
    added_lines = []
    mock_return = dict(value=0)

    def mock_file_append( text, file_path, **kwds ):
        added_lines.append(text)
        return mock_return["value"]

    with __mock_fabric_util_method("file_append", mock_file_append):
        env_file_builder.append_line( name="PATH", action="prepend_to", value="/usr/bin/local/R" )
        assert added_lines == [ "PATH=/usr/bin/local/R:$PATH; export PATH" ]
        assert env_file_builder.return_code == 0

        # Reset mock lines
        del added_lines[:]
        # Next time file_append will fail
        mock_return["value"] = 1

        env_file_builder.append_line( action="source", value="/usr/bin/local/R/env.sh" )
        assert added_lines == [ "if [ -f /usr/bin/local/R/env.sh ] ; then . /usr/bin/local/R/env.sh ; fi" ]
        # Check failure
        assert env_file_builder.return_code == 1

        mock_return["value"] = 0
        env_file_builder.append_line( name="LD_LIBRARY_PATH", action="append_to", value="/usr/bin/local/R/lib" )
        # Verify even though last append succeeded, previous failure still recorded.
        assert env_file_builder.return_code == 1


## Poor man's mocking. Need to get a real mocking library as real Galaxy development
## dependnecy.
@contextmanager
def __mock_fabric_util_method(name, mock_method):
    real_method = getattr(fabric_util, name)
    try:
        setattr(fabric_util, name, mock_method)
        yield
    finally:
        setattr(fabric_util, name, real_method)
