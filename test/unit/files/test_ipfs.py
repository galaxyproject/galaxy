from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from galaxy.exceptions import MessageException
from galaxy.files.models import FilesSourceRuntimeContext
from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.files.sources.ipfs import (
    IPFSFileSourceConfiguration,
    IPFSFilesSource,
)

ROOT = "bafy-root"


def _source_and_context() -> tuple[IPFSFilesSource, FilesSourceRuntimeContext[IPFSFileSourceConfiguration]]:
    template = IPFSFilesSource.build_template_config(
        id="test",
        type="ipfs",
        root=f" /{ROOT}/ ",
        gateway_url="https://gateway.example/",
        file_sources_config=FileSourcePluginsConfig(listings_expiry_time=60),
    )
    with patch.object(IPFSFilesSource, "required_module", MagicMock()):
        source = IPFSFilesSource(template)
    return source, source._get_runtime_context()


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


@pytest.mark.parametrize("path", ["/../other-cid/secret", "../secret", "/nested/../../secret", "/.."])
def test_dotdot_does_not_escape_root(path):
    source, context = _source_and_context()
    fs = MagicMock()
    with patch.object(source, "_open_fs", return_value=fs):
        with pytest.raises(MessageException, match="outside configured IPFS root"):
            source._list(context, path)
        with pytest.raises(MessageException, match="outside configured IPFS root"):
            source._realize_to(path, "/tmp/hello.txt", context)
    fs.ls.assert_not_called()
    fs.get_file.assert_not_called()


@pytest.mark.parametrize(
    "path",
    [
        "other-cid/file",
        f"{ROOT}-other/file",
        "/ipfs/other-cid/file",
        f"{ROOT}/../other-cid/file",
        f"/{ROOT}/nested/../../file",
    ],
)
def test_adapt_rejects_outside_root(path):
    source, context = _source_and_context()
    fs = MagicMock()
    fs.ls.return_value = [{"name": path, "type": "file", "size": 5}]
    with patch.object(source, "_open_fs", return_value=fs):
        with pytest.raises(MessageException, match="outside configured .*root"):
            source._list(context, "/")
