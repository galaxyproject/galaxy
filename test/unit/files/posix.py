import os
import tempfile

from galaxy.datatypes import sniff
from galaxy.files import (
    ConfiguredFileSources,
    ConfiguredFileSourcesConfig,
)
from ._util import (
    assert_realizes_as,
    find,
    find_file_a,
    list_dir,
    list_root,
    serialize_and_recover,
    user_context_fixture,
    write_from,
)

EMAIL = 'alice@galaxyproject.org'


def test_posix():
    file_sources = _configured_file_sources()
    as_dict = file_sources.to_dict()
    assert len(as_dict["file_sources"]) == 1
    file_source_as_dict = as_dict["file_sources"][0]
    assert file_source_as_dict["uri_root"] == "gxfiles://test1"

    _download_and_check_file(file_sources)

    res = list_root(file_sources, "gxfiles://test1", recursive=False)
    file_a = find_file_a(res)
    assert file_a
    assert file_a["uri"] == "gxfiles://test1/a"
    assert file_a["name"] == "a"

    subdir1 = find(res, name="subdir1")
    assert subdir1["class"] == "Directory"
    assert subdir1["uri"] == "gxfiles://test1/subdir1"

    res = list_dir(file_sources, "gxfiles://test1/subdir1", recursive=False)
    subdir2 = find(res, name="subdir2")
    assert subdir2, res
    assert subdir2["uri"] == "gxfiles://test1/subdir1/subdir2"

    file_c = find(res, name="c")
    assert file_c, res
    assert file_c["uri"] == "gxfiles://test1/subdir1/c"

    res = list_root(file_sources, "gxfiles://test1", recursive=True)
    subdir1 = find(res, name="subdir1")
    subdir2 = find(res, name="subdir2")
    assert subdir1["class"] == "Directory"
    assert subdir1["uri"] == "gxfiles://test1/subdir1"
    assert subdir2["uri"] == "gxfiles://test1/subdir1/subdir2"
    assert subdir2["class"] == "Directory"


def test_posix_link_security():
    file_sources = _configured_file_sources()
    e = None
    try:
        sniff.stream_url_to_file("gxfiles://test1/unsafe", file_sources=file_sources)
    except Exception as ex:
        e = ex
    _assert_access_prohibited(e)


def test_posix_link_security_write():
    file_sources = _configured_file_sources(writable=True)
    e = None
    try:
        write_from(file_sources, "gxfiles://test1/unsafe", "my test content")
    except Exception as ex:
        e = ex
    _assert_access_prohibited(e)


def test_posix_link_security_allowlist():
    file_sources = _configured_file_sources(include_allowlist=True)
    tmp_name = sniff.stream_url_to_file("gxfiles://test1/unsafe", file_sources=file_sources)
    try:
        with open(tmp_name) as f:
            assert f.read() == "b\n"
    finally:
        os.remove(tmp_name)


def test_posix_link_security_allowlist_write():
    file_sources = _configured_file_sources(include_allowlist=True, writable=True)
    write_from(file_sources, "gxfiles://test1/unsafe", "my test content")
    with open(os.path.join(file_sources.test_root, "unsafe")) as f:
        assert f.read() == "my test content"


def test_posix_disable_link_security():
    file_sources = _configured_file_sources(plugin_extra_config={"enforce_symlink_security": False})
    tmp_name = sniff.stream_url_to_file("gxfiles://test1/unsafe", file_sources=file_sources)
    try:
        with open(tmp_name) as f:
            assert f.read() == "b\n"
    finally:
        os.remove(tmp_name)


def test_posix_nonexistent_parent_write():
    file_sources = _configured_file_sources(include_allowlist=True, writable=True)
    e = None
    try:
        write_from(file_sources, "gxfiles://test1/notreal/myfile", "my test content")
    except Exception as ex:
        e = ex
    assert e is not None
    assert "Parent" in str(e)


def test_posix_per_user():
    file_sources = _configured_file_sources(per_user=True)
    user_context = user_context_fixture()
    assert_realizes_as(file_sources, "gxfiles://test1/a", "a\n", user_context=user_context)

    res = list_root(file_sources, "gxfiles://test1", recursive=False, user_context=user_context)
    assert find_file_a(res)


def test_posix_per_user_writable():
    file_sources = _configured_file_sources(per_user=True, writable=True)
    user_context = user_context_fixture()

    res = list_root(file_sources, "gxfiles://test1", recursive=False, user_context=user_context)
    b = find(res, name="b")
    assert b is None

    write_from(file_sources, "gxfiles://test1/b", "my test content", user_context=user_context)

    res = list_root(file_sources, "gxfiles://test1", recursive=False, user_context=user_context)
    b = find(res, name="b")
    assert b is not None, b

    assert_realizes_as(file_sources, "gxfiles://test1/b", "my test content", user_context=user_context)


def test_posix_per_user_serialized():
    user_context = user_context_fixture()
    file_sources = serialize_and_recover(_configured_file_sources(per_user=True), user_context=user_context)

    # After serialization and recovery - no need to for user context.
    assert_realizes_as(file_sources, "gxfiles://test1/a", "a\n", user_context=None)


def test_user_ftp_explicit_config():
    file_sources_config = ConfiguredFileSourcesConfig(
        ftp_upload_purge=False,
    )
    plugin = {
        'type': 'gxftp',
    }
    tmp, root = _setup_root()
    file_sources = ConfiguredFileSources(file_sources_config, conf_dict=[plugin])
    user_context = user_context_fixture(user_ftp_dir=root)
    _write_file_fixtures(tmp, root)

    assert_realizes_as(file_sources, "gxftp://a", "a\n", user_context=user_context)

    file_sources_remote = serialize_and_recover(file_sources, user_context=user_context)
    assert_realizes_as(file_sources_remote, "gxftp://a", "a\n")

    as_dict = file_sources.to_dict()
    assert len(as_dict["file_sources"]) == 1
    file_source_as_dict = as_dict["file_sources"][0]
    assert file_source_as_dict["uri_root"] == "gxftp://"
    assert file_source_as_dict["id"] == "_ftp"


def test_user_ftp_implicit_config():
    tmp, root = _setup_root()
    file_sources_config = ConfiguredFileSourcesConfig(
        ftp_upload_dir=root,
        ftp_upload_purge=False,
    )
    file_sources = ConfiguredFileSources(file_sources_config, conf_dict=[], load_stock_plugins=True)
    user_context = user_context_fixture(user_ftp_dir=root)
    _write_file_fixtures(tmp, root)
    assert os.path.exists(os.path.join(root, "a"))

    assert_realizes_as(file_sources, "gxftp://a", "a\n", user_context=user_context)

    file_sources_remote = serialize_and_recover(file_sources, user_context=user_context)
    assert_realizes_as(file_sources_remote, "gxftp://a", "a\n")
    assert os.path.exists(os.path.join(root, "a"))


def test_user_ftp_respects_upload_purge_off():
    tmp, root = _setup_root()
    file_sources_config = ConfiguredFileSourcesConfig(
        ftp_upload_dir=root,
        ftp_upload_purge=True,
    )
    file_sources = ConfiguredFileSources(file_sources_config, conf_dict=[], load_stock_plugins=True)
    user_context = user_context_fixture(user_ftp_dir=root)
    _write_file_fixtures(tmp, root)
    assert_realizes_as(file_sources, "gxftp://a", "a\n", user_context=user_context)
    assert not os.path.exists(os.path.join(root, "a"))


def test_user_ftp_respects_upload_purge_on_by_default():
    tmp, root = _setup_root()
    file_sources_config = ConfiguredFileSourcesConfig(
        ftp_upload_dir=root,
    )
    file_sources = ConfiguredFileSources(file_sources_config, conf_dict=[], load_stock_plugins=True)
    user_context = user_context_fixture(user_ftp_dir=root)
    _write_file_fixtures(tmp, root)
    assert_realizes_as(file_sources, "gxftp://a", "a\n", user_context=user_context)
    assert not os.path.exists(os.path.join(root, "a"))


def test_import_dir_explicit_config():
    tmp, root = _setup_root()
    file_sources_config = ConfiguredFileSourcesConfig(
        library_import_dir=root,
    )
    plugin = {
        'type': 'gximport',
    }
    file_sources = ConfiguredFileSources(file_sources_config, conf_dict=[plugin])
    _write_file_fixtures(tmp, root)

    assert_realizes_as(file_sources, "gximport://a", "a\n")


def test_import_dir_implicit_config():
    tmp, root = _setup_root()
    file_sources_config = ConfiguredFileSourcesConfig(
        library_import_dir=root,
    )
    file_sources = ConfiguredFileSources(file_sources_config, conf_dict=[], load_stock_plugins=True)
    _write_file_fixtures(tmp, root)

    assert_realizes_as(file_sources, "gximport://a", "a\n")


def test_user_import_dir_implicit_config():
    tmp, root = _setup_root()
    file_sources_config = ConfiguredFileSourcesConfig(
        user_library_import_dir=root,
    )
    file_sources = ConfiguredFileSources(file_sources_config, conf_dict=[], load_stock_plugins=True)

    _write_file_fixtures(tmp, os.path.join(root, EMAIL))

    user_context = user_context_fixture()
    assert_realizes_as(file_sources, "gxuserimport://a", "a\n", user_context=user_context)


def _configured_file_sources(include_allowlist=False, plugin_extra_config=None, per_user=False, writable=None):
    tmp, root = _setup_root()
    config_kwd = {}
    if include_allowlist:
        config_kwd["symlink_allowlist"] = [tmp]
    file_sources_config = ConfiguredFileSourcesConfig(**config_kwd)
    plugin = {
        'type': 'posix',
        'id': 'test1',
    }
    if writable is not None:
        plugin['writable'] = writable
    if per_user:
        plugin['root'] = "%s/${user.username}" % root
        # setup files just for alice
        root = os.path.join(root, "alice")
        os.mkdir(root)
    else:
        plugin['root'] = root
    plugin.update(plugin_extra_config or {})
    _write_file_fixtures(tmp, root)
    file_sources = ConfiguredFileSources(file_sources_config, conf_dict=[plugin])
    file_sources.test_root = root
    return file_sources


def _setup_root():
    tmp = os.path.realpath(tempfile.mkdtemp())
    root = os.path.join(tmp, "root")
    os.mkdir(root)
    return tmp, root


def _write_file_fixtures(tmp, root):
    if not os.path.exists(root):
        os.mkdir(root)
    os.symlink(os.path.join(tmp, "b"), os.path.join(root, "unsafe"))
    with open(os.path.join(root, "a"), "w") as f:
        f.write("a\n")
    with open(os.path.join(tmp, "b"), "w") as f:
        f.write("b\n")

    subdir1 = os.path.join(root, "subdir1")
    os.mkdir(subdir1)
    with open(os.path.join(subdir1, "c"), "w") as f:
        f.write("c\n")

    subdir2 = os.path.join(subdir1, "subdir2")
    os.mkdir(subdir2)
    with open(os.path.join(subdir2, "d"), "w") as f:
        f.write("d\n")

    return tmp, root


def _download_and_check_file(file_sources):
    tmp_name = sniff.stream_url_to_file("gxfiles://test1/a", file_sources=file_sources)
    try:
        a_contents = open(tmp_name).read()
        assert a_contents == "a\n"
    finally:
        os.remove(tmp_name)


def _assert_access_prohibited(e):
    assert e is not None
    assert "Operation not allowed" in str(e)
