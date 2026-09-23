from unittest.mock import (
    MagicMock,
    patch,
)

from galaxy.files.models import (
    FilesSourceRuntimeContext,
    UserData,
)
from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.files.sources import BaseFilesSource
from galaxy.files.sources.ipfs import (
    IPFSFileSourceConfiguration,
    IPFSFilesSource,
)

ROOT = "bafy-root"


def _source_and_context() -> tuple[IPFSFilesSource, FilesSourceRuntimeContext[IPFSFileSourceConfiguration]]:
    source = object.__new__(IPFSFilesSource)
    config = IPFSFileSourceConfiguration(
        id="test",
        type="ipfs",
        root=f"/{ROOT}/",
        gateway_url="https://gateway.example",
        file_sources_config=FileSourcePluginsConfig(),
    )
    BaseFilesSource.__init__(source, IPFSFilesSource.build_template_config(**config.model_dump()))
    return source, FilesSourceRuntimeContext(UserData(), config)


def test_list_paths_are_scoped_to_configured_root():
    source, context = _source_and_context()
    fs = MagicMock()
    fs.ls.side_effect = [
        [{"name": f"{ROOT}/nested", "type": "directory"}],
        [{"name": f"{ROOT}/nested/hello.txt", "type": "file", "size": 5}],
    ]
    with patch.object(source, "_open_fs", return_value=fs):
        root_entries, _ = source._list(context, "/")
        nested_entries, _ = source._list(context, "/nested")

    assert root_entries[0].path == "/nested"
    assert nested_entries[0].path == "/nested/hello.txt"
    assert nested_entries[0].uri == "ipfs://test/nested/hello.txt"
    assert [call.args[0] for call in fs.ls.call_args_list] == [ROOT, f"{ROOT}/nested"]


def test_realize_path_is_scoped_to_configured_root():
    source, context = _source_and_context()
    fs = MagicMock()
    with patch.object(source, "_open_fs", return_value=fs):
        source._realize_to("/nested/hello.txt", "/tmp/hello.txt", context)

    fs.get_file.assert_called_once_with(f"{ROOT}/nested/hello.txt", "/tmp/hello.txt")
