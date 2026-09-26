"""Export callers must return usable URIs for relative and service-assigned paths."""

import runpy
import tarfile
from pathlib import Path

import pytest

from galaxy.files import (
    ConfiguredFileSources,
    ConfiguredFileSourcesConf,
    DictFileSourcesUserContext,
)
from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.model.store import TarModelExportStore

TEST_USERNAME = "alice"
TEST_EMAIL = "alice@galaxyproject.org"


@pytest.fixture(params=["posix", "gxftp", "absolute_result"])
def export_destination(request, tmp_path, monkeypatch):
    source_type = "gxftp" if request.param == "gxftp" else "posix"
    file_sources = ConfiguredFileSources(
        FileSourcePluginsConfig(ftp_upload_purge=False),
        ConfiguredFileSourcesConf(
            conf_dict=[{"type": source_type, "id": "offline", "root": str(tmp_path), "writable": True}]
        ),
    )
    destination = "gxftp:///archive.tgz" if source_type == "gxftp" else "gxfiles://offline/archive.tgz"
    expected = destination
    source = file_sources.get_file_source_path(destination).file_source
    if source_type == "gxftp":
        # The stock source's URI builder uses gxftp://path; both forms resolve.
        expected = "gxftp://archive.tgz"
    if request.param == "absolute_result":
        expected = "gxfiles://offline/assigned.tgz"
        original_write = source._write_from

        def write_to_assigned_path(target_path, native_path, context):
            original_write("/assigned.tgz", native_path, context)
            return expected

        monkeypatch.setattr(source, "_write_from", write_to_assigned_path)
    context = DictFileSourcesUserContext(
        username=TEST_USERNAME,
        email=TEST_EMAIL,
        user_ftp_dir=str(tmp_path),
    )
    return file_sources, destination, expected, context


def test_export_cli_returns_readable_uri(export_destination, tmp_path, monkeypatch):
    file_sources, destination, expected, context = export_destination
    # This is a standalone executable; do not initialize galaxy.tools to load it.
    script = Path(__file__).resolve().parents[3] / "lib/galaxy/tools/imp_exp/export_history.py"
    write_to_destination = runpy.run_path(str(script))["_write_to_destination"]
    monkeypatch.setitem(write_to_destination.__globals__, "get_file_sources", lambda _: file_sources)
    archive = tmp_path / "input.tgz"
    archive.write_bytes(b"archive contents")

    actual_uri = write_to_destination("unused", str(archive), destination)

    assert actual_uri == expected
    source_path = file_sources.get_file_source_path(actual_uri)
    downloaded = tmp_path / "downloaded.tgz"
    source_path.file_source.realize_to(source_path.path, str(downloaded), user_context=context)
    assert downloaded.read_bytes() == archive.read_bytes()


def test_export_store_records_readable_uri(export_destination, tmp_path):
    file_sources, destination, expected, context = export_destination
    export_store = TarModelExportStore(destination, file_sources=file_sources)
    export_store.user_context = context
    export_store._finalize()

    assert export_store.file_source_uri == expected
    source_path = file_sources.get_file_source_path(str(export_store.file_source_uri))
    downloaded = tmp_path / "downloaded.tgz"
    source_path.file_source.realize_to(source_path.path, str(downloaded), user_context=context)
    with tarfile.open(downloaded) as archive:
        assert archive.getnames()


def test_write_from_returns_readable_uri(export_destination, tmp_path):
    file_sources, destination, expected, context = export_destination
    payload = tmp_path / "payload.txt"
    payload.write_text("archive contents")
    source_path = file_sources.get_file_source_path(destination)
    file_source = source_path.file_source

    written = file_source.write_from(source_path.path, str(payload), user_context=context)
    actual_uri = file_source.uri_from_write_result(written)

    assert actual_uri == expected
    realized_path = file_sources.get_file_source_path(actual_uri)
    downloaded = tmp_path / "downloaded.txt"
    realized_path.file_source.realize_to(realized_path.path, str(downloaded), user_context=context)
    assert downloaded.read_text() == "archive contents"
