"""The NOMAD file source against a fake nomad-fsspec, so CI needs neither the package nor NOMAD."""

import errno
import ipaddress
import os

import pytest

from galaxy.exceptions import (
    AuthenticationRequired,
    ConfigDoesNotAllowException,
    MessageException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.files.sources import nomad
from ._util import (
    configured_file_sources,
    user_context_fixture,
)

# an Oasis on Galaxy's own network, which the allowlist lets through without a DNS lookup
OASIS = "http://10.1.2.3/nomad-oasis"

TREE: dict[str, list[tuple[str, str | None]]] = {
    "/": [("/datasets", "Public datasets"), ("/uploads", "My uploads")],
    "/datasets": [("/datasets/ds1", "demo example data")],
    "/datasets/ds1": [("/datasets/ds1/up1", None), ("/datasets/ds1/up2", None)],
    "/datasets/ds1/up1": [("/datasets/ds1/up1/sub", None)],
    "/uploads": [("/uploads/up9", "My draft")],
}
FILES = {"/datasets/ds1/up1/a.txt": b"abc"}
UPLOAD_NAMES = {"up1": "nomad-demo-data.zip"}


class FakeNomadFileSystem:
    instances: list[dict] = []

    def __init__(self, **kwargs):
        self.instances.append(kwargs)

    def ls(self, path, detail=True):
        if path not in TREE:
            raise FileNotFoundError(errno.ENOENT, "No such file or directory", path)
        return [
            {"name": name, "size": 0, "type": "directory", "display_name": display_name or name.rsplit("/", 1)[-1]}
            for name, display_name in TREE[path]
        ]

    def get_file(self, rpath, lpath):
        if any(name == rpath for listing in TREE.values() for name, _ in listing):
            raise IsADirectoryError(errno.EISDIR, "Is a directory", rpath)
        if rpath.endswith("slow.txt"):
            raise RuntimeError("NOMAD at 10.1.2.3 did not answer in time")
        if rpath not in FILES:
            raise FileNotFoundError(errno.ENOENT, "No such file or directory", rpath)
        with open(lpath, "wb") as f:
            f.write(FILES[rpath])

    def upload_names(self, upload_ids):
        return {upload_id: UPLOAD_NAMES[upload_id] for upload_id in upload_ids if upload_id in UPLOAD_NAMES}

    def search_uploads(self, dataset_id, text):
        if text == "gone":
            raise FileNotFoundError("/entries/query: Not Found")
        return [upload_id for upload_id, name in UPLOAD_NAMES.items() if text.casefold() in name.casefold()]


@pytest.fixture(autouse=True)
def fake_nomad(monkeypatch):
    FakeNomadFileSystem.instances = []
    monkeypatch.setattr(nomad, "NomadFileSystem", FakeNomadFileSystem)
    monkeypatch.setattr(nomad.NomadFilesSource, "required_module", FakeNomadFileSystem)


def _source(**config):
    allowlist = [ipaddress.ip_network("10.0.0.0/8")]
    conf = {"type": "nomad", "id": "nomad", "label": "NOMAD", "base_url": OASIS, **config}
    file_sources = configured_file_sources([conf], FileSourcePluginsConfig(fetch_url_allowlist=allowlist))
    return file_sources.get_file_source_path("gxfiles://nomad").file_source


def _list(source, path, **kwargs):
    entries, _ = source.list(path, user_context=user_context_fixture(), **kwargs)
    return [(entry.name, entry.path) for entry in entries]


def test_a_dataset_names_the_page_shown_and_searches_names_in_nomad(monkeypatch):
    source = _source()
    assert _list(source, "/") == [("Public datasets", "/datasets"), ("My uploads", "/uploads")]
    assert _list(source, "/datasets/ds1", limit=25, offset=0) == [
        ("nomad-demo-data.zip", "/datasets/ds1/up1"),
        ("up2", "/datasets/ds1/up2"),
    ]
    assert _list(source, "/datasets/ds1", query=" DEMO-data ") == [("nomad-demo-data.zip", "/datasets/ds1/up1")]
    assert len(_list(source, "/datasets/ds1", query="  ")) == 2
    assert _list(source, "/datasets", query="EXAMPLE") == [("demo example data", "/datasets/ds1")]
    monkeypatch.setattr(nomad, "MAX_NAMED", 1)
    assert _list(source, "/datasets/ds1") == [("up1", "/datasets/ds1/up1"), ("up2", "/datasets/ds1/up2")]


def test_my_uploads_need_a_token_whose_instance_is_not_cached():
    with pytest.raises(AuthenticationRequired, match="needs a NOMAD token"):
        _list(_source(), "/uploads")
    _list(_source(), "/")
    assert _list(_source(token="secret\n"), "/uploads") == [("My draft", "/uploads/up9")]
    assert [kwargs["skip_instance_cache"] for kwargs in FakeNomadFileSystem.instances] == [False, True]
    assert FakeNomadFileSystem.instances[-1]["token"] == "secret"


def test_refusals_keep_their_status():
    with pytest.raises(ConfigDoesNotAllowException, match="fetch_url_allowlist") as refused:
        _list(_source(base_url="HTTP://169.254.169.254"), "/")
    assert refused.value.status_code == 403
    with pytest.raises(ObjectNotFound, match=r"no-such-dataset was not found in NOMAD\.$"):
        _list(_source(), "/datasets/no-such-dataset")
    with pytest.raises(ObjectNotFound, match="Reason: /entries/query: Not Found"):
        _list(_source(), "/datasets/ds1", query="gone")
    for path in ("/", "/datasets/ds1", "/datasets/ds1/up1", "/uploads"):
        with pytest.raises(RequestParameterInvalidException, match="Recursive listing is not supported"):
            _list(_source(token="secret"), path, recursive=True)


def test_only_files_inside_an_upload_are_imported(tmp_path):
    source = _source()
    target = tmp_path / "a.txt"
    source.realize_to("/datasets/ds1/up1/a.txt", str(target), user_context=user_context_fixture())
    assert target.read_bytes() == b"abc"
    for folder in ("/datasets/ds1", "/datasets/ds1/up1", "/uploads/up9", "/datasets/ds1/up1/sub"):
        with pytest.raises(RequestParameterInvalidException, match="is a folder in NOMAD"):
            source.realize_to(folder, os.path.join(tmp_path, "x"), user_context=user_context_fixture())
    with pytest.raises(MessageException, match="did not answer in time"):
        source.realize_to("/datasets/ds1/up1/slow.txt", str(target), user_context=user_context_fixture())
