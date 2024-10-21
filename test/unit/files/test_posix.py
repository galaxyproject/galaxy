import os
import tempfile
from typing import (
    Any,
    Dict,
    Tuple,
)

import pytest

from galaxy.exceptions import (
    ItemAccessibilityException,
    RequestParameterInvalidException,
)
from galaxy.files import (
    ConfiguredFileSources,
    ConfiguredFileSourcesConf,
)
from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.files.unittest_utils import (
    setup_root,
    TestConfiguredFileSources,
    write_file_fixtures,
)
from ._util import (
    assert_realizes_as,
    assert_realizes_throws_exception,
    find,
    find_file_a,
    list_dir,
    list_root,
    serialize_and_recover,
    user_context_fixture,
    write_from,
)

EMAIL = "alice@galaxyproject.org"


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
    e = assert_realizes_throws_exception(file_sources, "gxfiles://test1/unsafe")
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
    assert_realizes_as(file_sources, "gxfiles://test1/unsafe", "b\n")


def test_posix_link_security_allowlist_write():
    file_sources = _configured_file_sources(include_allowlist=True, writable=True)
    write_from(file_sources, "gxfiles://test1/unsafe_dir/foo", "my test content")
    with open(os.path.join(file_sources.test_root, "subdir1", "foo")) as f:
        assert f.read() == "my test content"


def test_posix_disable_link_security():
    file_sources = _configured_file_sources(plugin_extra_config={"enforce_symlink_security": False})
    assert_realizes_as(file_sources, "gxfiles://test1/unsafe", "b\n")


def test_posix_nonexistent_parent_write():
    file_sources = _configured_file_sources(
        include_allowlist=True, writable=True, plugin_extra_config={"allow_subdir_creation": False}
    )
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
    file_sources_config = FileSourcePluginsConfig(
        ftp_upload_purge=False,
    )
    plugin = {
        "type": "gxftp",
    }
    tmp, root = setup_root()
    file_sources = ConfiguredFileSources(file_sources_config, ConfiguredFileSourcesConf(conf_dict=[plugin]))
    user_context = user_context_fixture(user_ftp_dir=root)
    write_file_fixtures(tmp, root)

    assert_realizes_as(file_sources, "gxftp://a", "a\n", user_context=user_context)

    file_sources_remote = serialize_and_recover(file_sources, user_context=user_context)
    assert_realizes_as(file_sources_remote, "gxftp://a", "a\n")

    as_dict = file_sources.to_dict()
    assert len(as_dict["file_sources"]) == 1
    file_source_as_dict = as_dict["file_sources"][0]
    assert file_source_as_dict["uri_root"] == "gxftp://"
    assert file_source_as_dict["id"] == "_ftp"


def test_user_ftp_implicit_config():
    tmp, root = setup_root()
    file_sources_config = FileSourcePluginsConfig(
        ftp_upload_dir=root,
        ftp_upload_purge=False,
    )
    file_sources = ConfiguredFileSources(
        file_sources_config, ConfiguredFileSourcesConf(conf_dict=[]), load_stock_plugins=True
    )
    user_context = user_context_fixture(user_ftp_dir=root)
    write_file_fixtures(tmp, root)
    assert os.path.exists(os.path.join(root, "a"))

    assert_realizes_as(file_sources, "gxftp://a", "a\n", user_context=user_context)

    file_sources_remote = serialize_and_recover(file_sources, user_context=user_context)
    assert_realizes_as(file_sources_remote, "gxftp://a", "a\n")
    assert os.path.exists(os.path.join(root, "a"))


def test_user_ftp_respects_upload_purge_off():
    tmp, root = setup_root()
    file_sources_config = FileSourcePluginsConfig(
        ftp_upload_dir=root,
        ftp_upload_purge=True,
    )
    file_sources = ConfiguredFileSources(
        file_sources_config, ConfiguredFileSourcesConf(conf_dict=[]), load_stock_plugins=True
    )
    user_context = user_context_fixture(user_ftp_dir=root)
    write_file_fixtures(tmp, root)
    assert_realizes_as(file_sources, "gxftp://a", "a\n", user_context=user_context)
    assert not os.path.exists(os.path.join(root, "a"))


def test_user_ftp_respects_upload_purge_on_by_default():
    tmp, root = setup_root()
    file_sources_config = FileSourcePluginsConfig(
        ftp_upload_dir=root,
    )
    file_sources = ConfiguredFileSources(
        file_sources_config, ConfiguredFileSourcesConf(conf_dict=[]), load_stock_plugins=True
    )
    user_context = user_context_fixture(user_ftp_dir=root)
    write_file_fixtures(tmp, root)
    assert_realizes_as(file_sources, "gxftp://a", "a\n", user_context=user_context)
    assert not os.path.exists(os.path.join(root, "a"))


def test_import_dir_explicit_config():
    tmp, root = setup_root()
    file_sources_config = FileSourcePluginsConfig(
        library_import_dir=root,
    )
    plugin = {
        "type": "gximport",
    }
    file_sources = ConfiguredFileSources(file_sources_config, ConfiguredFileSourcesConf(conf_dict=[plugin]))
    write_file_fixtures(tmp, root)

    assert_realizes_as(file_sources, "gximport://a", "a\n")


def test_import_dir_implicit_config():
    tmp, root = setup_root()
    file_sources_config = FileSourcePluginsConfig(
        library_import_dir=root,
    )
    file_sources = ConfiguredFileSources(
        file_sources_config, ConfiguredFileSourcesConf(conf_dict=[]), load_stock_plugins=True
    )
    write_file_fixtures(tmp, root)

    assert_realizes_as(file_sources, "gximport://a", "a\n")


def test_user_import_dir_implicit_config():
    tmp, root = setup_root()
    file_sources_config = FileSourcePluginsConfig(
        user_library_import_dir=root,
    )
    file_sources = ConfiguredFileSources(
        file_sources_config, ConfiguredFileSourcesConf(conf_dict=[]), load_stock_plugins=True
    )

    write_file_fixtures(tmp, os.path.join(root, EMAIL))

    user_context = user_context_fixture()
    assert_realizes_as(file_sources, "gxuserimport://a", "a\n", user_context=user_context)


def test_posix_user_access_requires_role():
    allowed_role_name = "role1"
    plugin_extra_config = {
        "requires_roles": allowed_role_name,
    }
    file_sources = _configured_file_sources(writable=True, plugin_extra_config=plugin_extra_config)

    user_context = user_context_fixture()
    _assert_user_access_prohibited(file_sources, user_context)

    user_context = user_context_fixture(role_names={allowed_role_name})
    _assert_user_access_granted(file_sources, user_context)


def test_posix_user_access_requires_group():
    allowed_group_name = "group1"
    plugin_extra_config = {
        "requires_groups": allowed_group_name,
    }
    file_sources = _configured_file_sources(writable=True, plugin_extra_config=plugin_extra_config)

    user_context = user_context_fixture()
    _assert_user_access_prohibited(file_sources, user_context)

    user_context = user_context_fixture(group_names={allowed_group_name})
    _assert_user_access_granted(file_sources, user_context)


def test_posix_admin_user_has_access():
    plugin_extra_config = {
        "requires_roles": "role1",
        "requires_groups": "group1",
    }
    file_sources = _configured_file_sources(writable=True, plugin_extra_config=plugin_extra_config)

    user_context = user_context_fixture()
    _assert_user_access_prohibited(file_sources, user_context)

    user_context = user_context_fixture(is_admin=True)
    _assert_user_access_granted(file_sources, user_context)


def test_posix_user_access_requires_role_and_group():
    allowed_group_name = "group1"
    allowed_role_name = "role1"
    plugin_extra_config = {
        "requires_roles": allowed_role_name,
        "requires_groups": allowed_group_name,
    }
    file_sources = _configured_file_sources(writable=True, plugin_extra_config=plugin_extra_config)

    user_context = user_context_fixture(group_names={allowed_group_name})
    _assert_user_access_prohibited(file_sources, user_context)

    user_context = user_context_fixture(role_names={allowed_role_name})
    _assert_user_access_prohibited(file_sources, user_context)

    user_context = user_context_fixture(role_names={allowed_role_name}, group_names={allowed_group_name})
    _assert_user_access_granted(file_sources, user_context)


def test_posix_user_access_using_boolean_rules():
    plugin_extra_config = {
        "requires_roles": "role1 and (role2 or role3)",
        "requires_groups": "group1 and group2 and not group3",
    }
    file_sources = _configured_file_sources(writable=True, plugin_extra_config=plugin_extra_config)

    user_context = user_context_fixture(role_names=set(), group_names=set())
    _assert_user_access_prohibited(file_sources, user_context)

    user_context = user_context_fixture(role_names={"role1"}, group_names={"group1", "group2"})
    _assert_user_access_prohibited(file_sources, user_context)

    user_context = user_context_fixture(role_names={"role1", "role3"}, group_names={"group1", "group2", "group3"})
    _assert_user_access_prohibited(file_sources, user_context)

    user_context = user_context_fixture(role_names={"role1", "role2"}, group_names={"group3", "group5"})
    _assert_user_access_prohibited(file_sources, user_context)

    user_context = user_context_fixture(role_names={"role1", "role3"}, group_names={"group1", "group2"})
    _assert_user_access_granted(file_sources, user_context)


def test_posix_file_url_only_mode_non_admin_cannot_retrieve():
    with tempfile.NamedTemporaryFile(mode="w") as tf:
        tf.write("File content returned from a file:// location")
        tf.flush()
        test_url = f"file://{tf.name}"
        user_context = user_context_fixture()
        file_sources = _configured_file_sources(empty_root=True)
        file_source_pair = file_sources.get_file_source_path(test_url)

        assert file_source_pair.path == tf.name
        assert file_source_pair.file_source.id == "test1"

        with pytest.raises(ItemAccessibilityException):
            assert_realizes_as(
                file_sources,
                test_url,
                "File content returned from a file:// location",
                user_context=user_context,
            )


def test_posix_file_url_only_mode_admin_can_retrieve():
    with tempfile.NamedTemporaryFile(mode="w") as tf:
        tf.write("File content returned from a file:// location")
        tf.flush()
        test_url = f"file://{tf.name}"
        user_context = user_context_fixture(is_admin=True)
        file_sources = _configured_file_sources(empty_root=True)
        file_source_pair = file_sources.get_file_source_path(test_url)

        assert file_source_pair.path == tf.name
        assert file_source_pair.file_source.id == "test1"

        assert_realizes_as(
            file_sources,
            test_url,
            "File content returned from a file:// location",
            user_context=user_context,
        )


def test_posix_file_url_only_mode_even_admin_cannot_write():
    with tempfile.NamedTemporaryFile(mode="w") as tf:
        tf.write("File content returned from a file:// location")
        tf.flush()
        test_url = f"file://{tf.name}"
        user_context = user_context_fixture(is_admin=True)
        file_sources = _configured_file_sources(empty_root=True)
        file_source_pair = file_sources.get_file_source_path(test_url)

        assert file_source_pair.path == tf.name
        assert file_source_pair.file_source.id == "test1"

        with pytest.raises(Exception, match="Cannot write to a non-writable file source"):
            write_from(file_sources, test_url, "my test content", user_context=user_context)


def test_posix_file_url_only_mode_malformed():
    with tempfile.NamedTemporaryFile(mode="w") as tf:
        tf.write("File content returned from a file://file:// location")
        tf.flush()
        test_url = f"file://file://{tf.name}"
        user_context = user_context_fixture(is_admin=True)
        file_sources = _configured_file_sources(empty_root=True)
        file_source_pair = file_sources.get_file_source_path(test_url)

        assert file_source_pair.path == test_url[7:]
        assert file_source_pair.file_source.id == "test1"

        with pytest.raises(FileNotFoundError, match=r"\[Errno 2\] No such file or directory: '/file:/"):
            assert_realizes_as(
                file_sources,
                test_url,
                "File content returned from a file://file:// location",
                user_context=user_context,
            )


def test_posix_file_url_allowed_root():
    file_sources, root = _configured_file_sources_with_root(plugin_extra_config={"enforce_symlink_security": False})
    test_url = f"file://{root}/a"
    assert_realizes_as(file_sources, test_url, "a\n")


def test_posix_file_url_disallowed_root():
    file_sources, root = _configured_file_sources_with_root(plugin_extra_config={"enforce_symlink_security": False})
    with tempfile.NamedTemporaryFile(mode="w") as tf:
        tf.write("some content")
        tf.flush()
        test_url = f"file://{tf.name}"
        with pytest.raises(RequestParameterInvalidException, match="Could not find handler for URI"):
            assert_realizes_as(file_sources, test_url, "some content\n")


def _assert_user_access_prohibited(file_sources, user_context):
    with pytest.raises(ItemAccessibilityException):
        list_root(file_sources, "gxfiles://test1", recursive=False, user_context=user_context)

    with pytest.raises(ItemAccessibilityException):
        write_from(file_sources, "gxfiles://test1/b", "my test content", user_context=user_context)

    with pytest.raises(ItemAccessibilityException):
        assert_realizes_as(file_sources, "gxfiles://test1/a", "a\n", user_context=user_context)


def _assert_user_access_granted(file_sources, user_context):
    res = list_root(file_sources, "gxfiles://test1", recursive=False, user_context=user_context)
    assert res

    write_from(file_sources, "gxfiles://test1/b", "my test content", user_context=user_context)

    res = list_root(file_sources, "gxfiles://test1", recursive=False, user_context=user_context)
    b = find(res, name="b")
    assert b is not None, b

    assert_realizes_as(file_sources, "gxfiles://test1/a", "a\n", user_context=user_context)


def _configured_file_sources_with_root(
    include_allowlist=False,
    plugin_extra_config=None,
    per_user=False,
    writable=None,
    allow_subdir_creation=True,
    empty_root=False,
) -> Tuple[TestConfiguredFileSources, str]:
    if empty_root:
        tmp, root = "/", None
    else:
        tmp, root = setup_root()
    config_kwd = {}
    if include_allowlist:
        config_kwd["symlink_allowlist"] = [tmp]
    file_sources_config = FileSourcePluginsConfig(**config_kwd)
    plugin: Dict[str, Any] = {
        "type": "posix",
    }
    if writable is not None:
        plugin["writable"] = writable
    if per_user and root:
        plugin["root"] = f"{root}/${{user.username}}"
        # setup files just for alice
        root = os.path.join(root, "alice")
        os.mkdir(root)
    else:
        plugin["root"] = root
    plugin.update(plugin_extra_config or {})
    if root:
        write_file_fixtures(tmp, root)
    file_sources = TestConfiguredFileSources(file_sources_config, conf_dict={"test1": plugin}, test_root=root)
    return file_sources, root


def _configured_file_sources(
    include_allowlist=False,
    plugin_extra_config=None,
    per_user=False,
    writable=None,
    allow_subdir_creation=True,
    empty_root=False,
) -> TestConfiguredFileSources:
    file_sources, _ = _configured_file_sources_with_root(
        include_allowlist=include_allowlist,
        plugin_extra_config=plugin_extra_config,
        per_user=per_user,
        writable=writable,
        allow_subdir_creation=allow_subdir_creation,
        empty_root=empty_root,
    )
    return file_sources


def _download_and_check_file(file_sources):
    assert_realizes_as(file_sources, "gxfiles://test1/a", "a\n")


def _assert_access_prohibited(e):
    assert e is not None
    assert "Operation not allowed" in str(e)
