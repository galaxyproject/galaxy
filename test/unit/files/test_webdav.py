# docker run -v `pwd`/test/integration/webdav/data:/media  -e WEBDAV_USERNAME=alice -e WEBDAV_PASSWORD=secret1234 -p 7083:7083 jmchilton/webdavdev
# GALAXY_TEST_WEBDAV=1 pytest test/unit/files/test_webdav.py
import importlib.util
import os
from typing import Any

import httpx
import pytest

from galaxy.exceptions import ConfigDoesNotAllowException
from galaxy.files.sources import (
    BaseFilesSource,
    webdav,
)
from galaxy.files.sources.webdav import WebDavFilesSource
from ._util import (
    configured_file_sources,
    find,
    find_file_a,
    list_dir,
    list_root,
    serialize_and_recover,
    user_context_fixture,
)
from .test_posix import _download_and_check_file

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "webdav_file_sources_conf.yml")
USER_FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "webdav_user_file_sources_conf.yml")

skip_if_no_webdav = pytest.mark.skipif(
    not os.environ.get("GALAXY_TEST_WEBDAV") or importlib.util.find_spec("webdav4") is None,
    reason="GALAXY_TEST_WEBDAV not set or webdav4 not installed",
)


@skip_if_no_webdav
def test_file_source():
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path("gxfiles://test1")

    assert file_source_pair.path == "/"
    file_source = file_source_pair.file_source
    res, _ = file_source.list("/", recursive=True)
    a_file = find_file_a(res)
    assert a_file
    assert a_file.uri == "gxfiles://test1/a", a_file

    res, _ = file_source.list("/", recursive=False)
    file_a = find_file_a(res)
    assert file_a
    assert file_a.uri == "gxfiles://test1/a"
    assert file_a.name == "a"

    subdir1 = find(res, name="subdir1")
    assert subdir1
    assert subdir1.class_ == "Directory"
    assert subdir1.uri == "gxfiles://test1/subdir1"

    res = list_dir(file_sources, "gxfiles://test1/subdir1", recursive=False)
    subdir2 = find(res, name="subdir2")
    assert subdir2, res
    assert subdir2.uri == "gxfiles://test1/subdir1/subdir2"

    file_c = find(res, name="c")
    assert file_c, res
    assert file_c.uri == "gxfiles://test1/subdir1/c"


@skip_if_no_webdav
def test_sniff_to_tmp():
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    _download_and_check_file(file_sources)


@skip_if_no_webdav
def test_serialization():
    file_sources_o = configured_file_sources(FILE_SOURCES_CONF)
    original = file_source_as_webdav(file_sources_o._file_sources[0])
    assert original._get_runtime_context().config.base_url == "http://127.0.0.1:7083"

    # serialize the configured file sources and rematerialize them,
    # ensure they still function. This is needed for uploading files.
    file_sources = serialize_and_recover(file_sources_o)
    recovered = file_source_as_webdav(file_sources._file_sources[0])
    assert recovered._get_runtime_context().config.base_url == "http://127.0.0.1:7083"

    res = list_root(file_sources, "gxfiles://test1", recursive=True)
    assert find_file_a(res)

    res = list_root(file_sources, "gxfiles://test1", recursive=False)
    assert find_file_a(res)

    _download_and_check_file(file_sources)


def file_source_as_webdav(file_source: BaseFilesSource) -> WebDavFilesSource:
    if not isinstance(file_source, WebDavFilesSource):
        raise TypeError(f"Expected WebDavFilesSource, got {type(file_source)}")
    return file_source


@skip_if_no_webdav
def test_serialization_user():
    file_sources_o = configured_file_sources(USER_FILE_SOURCES_CONF)
    user_context = user_context_fixture()

    original = file_source_as_webdav(file_sources_o._file_sources[0])
    assert original._get_runtime_context(user_context=user_context).config.base_url == "http://127.0.0.1:7083"

    res = list_root(file_sources_o, "gxfiles://test1", recursive=True, user_context=user_context)
    assert find_file_a(res)

    file_sources = serialize_and_recover(file_sources_o, user_context=user_context)
    recovered = file_source_as_webdav(file_sources._file_sources[0])
    assert recovered._get_runtime_context().config.base_url == "http://127.0.0.1:7083"

    res = list_root(file_sources, "gxfiles://test1", recursive=True, user_context=None)
    assert find_file_a(res)


@skip_if_no_webdav
def test_url_preserved_in_serialization():
    # Regression test: 'url' is in COMMON_FILE_SOURCE_PROP_NAMES and was excluded from
    # _serialize_config, causing WebDAVFS to be initialized with url=None, which led to
    # AttributeError: 'NoneType' object has no attribute 'rstrip' when fetching files.
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    fs = file_source_as_webdav(file_sources._file_sources[0])

    serialized = fs.to_dict(for_serialization=True)
    assert "url" in serialized, "WebDAV url must be preserved in serialized form for job runner reconstruction"
    assert serialized["url"] == "http://127.0.0.1:7083"

    recovered = serialize_and_recover(file_sources)
    recovered_fs = file_source_as_webdav(recovered._file_sources[0])
    assert recovered_fs._get_runtime_context().config.url == "http://127.0.0.1:7083"


def _open_fs(monkeypatch: pytest.MonkeyPatch, **conf: str) -> dict[str, Any]:
    opened: dict[str, Any] = {}

    def fake_filesystem(*args: Any, **kwds: Any) -> None:
        opened.update(kwds)

    monkeypatch.setattr(webdav, "WebdavFileSystem", fake_filesystem)
    monkeypatch.setattr(WebDavFilesSource, "required_module", fake_filesystem)
    file_sources = configured_file_sources(
        [{"type": "webdav", "id": "dav", "base_url": "http://10.0.0.6:2880", **conf}]
    )
    source = file_source_as_webdav(file_sources._file_sources[0])
    source._open_fs(source._get_runtime_context(), {})
    return opened


def test_token_is_sent_instead_of_login_and_password(monkeypatch: pytest.MonkeyPatch) -> None:
    opened = _open_fs(monkeypatch, token=" abc ", login="alice", password="secret")
    assert opened["headers"] == {"Authorization": "Bearer abc"}
    assert opened["auth"] is None


def test_private_addresses_are_refused_unless_an_admin_configured_the_server(monkeypatch: pytest.MonkeyPatch) -> None:
    (admin_check,) = _open_fs(monkeypatch)["event_hooks"]["request"]
    admin_check(httpx.Request("GET", "http://10.0.0.6:2880/f"))
    with pytest.raises(ConfigDoesNotAllowException):
        admin_check(httpx.Request("GET", "http://10.0.0.5:2880/f"))
    (user_check,) = _open_fs(monkeypatch, scheme="gxuserfiles")["event_hooks"]["request"]
    with pytest.raises(ConfigDoesNotAllowException):
        user_check(httpx.Request("GET", "http://10.0.0.6:2880/f"))
