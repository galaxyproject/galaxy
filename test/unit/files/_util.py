"""Utilities for unit test suite for galaxy.files."""

import os
import tempfile
from typing import Optional

from galaxy.files import (
    ConfiguredFileSources,
    ConfiguredFileSourcesConf,
    DictFileSourcesUserContext,
    OptionalUserContext,
)
from galaxy.files.plugins import FileSourcePluginsConfig

TEST_USERNAME = "alice"
TEST_EMAIL = "alice@galaxyproject.org"


def serialize_and_recover(file_sources_o: ConfiguredFileSources, user_context: OptionalUserContext = None):
    as_dict = file_sources_o.to_dict(for_serialization=True, user_context=user_context)
    file_sources = ConfiguredFileSources.from_dict(as_dict)
    return file_sources


def find_file_a(dir_list):
    return find(dir_list, class_="File", name="a")


def find(dir_list, class_=None, name=None):
    for ent in dir_list:
        if class_ is not None and ent["class"] != class_:
            continue
        if name is not None and ent["name"] == name:
            return ent

    return None


def list_root(
    file_sources: ConfiguredFileSources,
    uri: str,
    recursive: bool,
    user_context: OptionalUserContext = None,
):
    file_source_pair = file_sources.get_file_source_path(uri)
    file_source = file_source_pair.file_source
    res, _ = file_source.list("/", recursive=recursive, user_context=user_context)
    return res


def list_dir(
    file_sources: ConfiguredFileSources,
    uri: str,
    recursive: bool,
    user_context: OptionalUserContext = None,
):
    file_source_pair = file_sources.get_file_source_path(uri)
    file_source = file_source_pair.file_source
    print(file_source_pair.path)
    print(uri)
    res, _ = file_source.list(file_source_pair.path, recursive=recursive, user_context=user_context)
    return res


def user_context_fixture(user_ftp_dir=None, role_names=None, group_names=None, is_admin=False, file_sources=None):
    user_context = DictFileSourcesUserContext(
        username=TEST_USERNAME,
        email=TEST_EMAIL,
        user_ftp_dir=user_ftp_dir,
        preferences={
            "webdav|password": "secret1234",
            "dropbox|access_token": os.environ.get("GALAXY_TEST_DROPBOX_ACCESS_TOKEN"),
            "googledrive|client_id": os.environ.get("GALAXY_TEST_GOOGLE_DRIVE_CLIENT_ID"),
            "googledrive|client_secret": os.environ.get("GALAXY_TEST_GOOGLE_DRIVE_CLIENT_SECRET"),
            "googledrive|access_token": os.environ.get("GALAXY_TEST_GOOGLE_DRIVE_ACCESS_TOKEN"),
            "googledrive|refresh_token": os.environ.get("GALAXY_TEST_GOOGLE_DRIVE_REFRESH_TOKEN"),
            "googlecloudstorage|project": os.environ.get("GALAXY_TEST_GCS_PROJECT"),
            "googlecloudstorage|bucket_name": os.environ.get("GALAXY_TEST_GCS_BUCKET"),
            "googlecloudstorage|client_id": os.environ.get("GALAXY_TEST_GCS_CLIENT_ID"),
            "googlecloudstorage|client_secret": os.environ.get("GALAXY_TEST_GCS_CLIENT_SECRET"),
            "googlecloudstorage|access_token": os.environ.get("GALAXY_TEST_GCS_ACCESS_TOKEN"),
            "googlecloudstorage|refresh_token": os.environ.get("GALAXY_TEST_GCS_REFRESH_TOKEN"),
            "onedata|provider_host": os.environ.get("GALAXY_TEST_ONEDATA_PROVIDER_HOST"),
            "onedata|access_token": os.environ.get("GALAXY_TEST_ONEDATA_ACCESS_TOKEN"),
            "basespace|client_id": os.environ.get("GALAXY_TEST_ONEDATA_CLIENT_ID"),
            "basespace|client_secret": os.environ.get("GALAXY_TEST_ONEDATA_CLIENT_SECRET"),
            "basespace|access_token": os.environ.get("GALAXY_TEST_ONEDATA_ACCESS_TOKEN"),
            "oidc|bearer_token": "IBearTokens",
        },
        role_names=role_names or set(),
        group_names=group_names or set(),
        is_admin=is_admin,
        file_sources=file_sources,
    )
    return user_context


def realize_to_temp_file(
    file_sources: ConfiguredFileSources, uri: str, user_context: OptionalUserContext = None
) -> str:
    file_source_path = file_sources.get_file_source_path(uri)
    with tempfile.NamedTemporaryFile(mode="r") as temp:
        file_source_path.file_source.realize_to(file_source_path.path, temp.name, user_context=user_context)
        with open(temp.name) as f:
            realized_contents = f.read()
            return realized_contents


def assert_realizes_as(
    file_sources: ConfiguredFileSources,
    uri: str,
    expected: str,
    user_context: OptionalUserContext = None,
):
    realized_contents = realize_to_temp_file(file_sources, uri, user_context=user_context)
    if realized_contents != expected:
        raise AssertionError(
            f"Expected to realize contents at [{uri}] as [{expected}], instead found [{realized_contents}]"
        )


def assert_realizes_contains(
    file_sources: ConfiguredFileSources,
    uri: str,
    expected: str,
    user_context: OptionalUserContext = None,
):
    realized_contents = realize_to_temp_file(file_sources, uri, user_context=user_context)
    if expected not in realized_contents:
        raise AssertionError(
            f"Expected to realize contents at [{uri}] to contain [{expected}], instead found [{realized_contents}]"
        )


def assert_realizes_throws_exception(
    file_sources: ConfiguredFileSources, uri: str, user_context: OptionalUserContext = None
) -> Exception:
    exception = None
    try:
        realize_to_temp_file(file_sources, uri, user_context=user_context)
    except Exception as e:
        exception = e
    assert exception
    return exception


def write_from(
    file_sources: ConfiguredFileSources,
    uri: str,
    content: str,
    user_context: OptionalUserContext = None,
) -> str:
    file_source_path = file_sources.get_file_source_path(uri)
    file_source = file_source_path.file_source
    with tempfile.NamedTemporaryFile(mode="w") as f:
        f.write(content)
        f.flush()
        return f"{file_source.get_scheme()}://{file_source.get_prefix()}" + file_source.write_from(
            file_source_path.path, f.name, user_context=user_context
        )


def configured_file_sources(conf_file, file_sources_config: Optional[FileSourcePluginsConfig] = None):
    file_sources_config = file_sources_config or FileSourcePluginsConfig()
    assert file_sources_config
    if isinstance(conf_file, str):
        conf = ConfiguredFileSourcesConf(conf_file=conf_file)
    else:
        conf = ConfiguredFileSourcesConf(conf_dict=conf_file)
    return ConfiguredFileSources(file_sources_config, conf)


def assert_can_write_and_read_to_conf(conf: dict):
    test_filename = "moo.txt"
    test_contents = "Hello World from Files Testing!"

    file_source_id = conf["id"]
    file_sources = configured_file_sources([conf])
    test_uri = f"gxfiles://{file_source_id}/{test_filename}"
    actual_uri = write_from(
        file_sources,
        test_uri,
        test_contents,
    )
    assert_realizes_contains(
        file_sources,
        actual_uri,
        test_contents,
    )


def assert_simple_file_realize(conf_file, recursive=False, filename="a", contents="a\n", contains=False):
    user_context = user_context_fixture()
    file_sources = configured_file_sources(conf_file)
    file_source_pair = file_sources.get_file_source_path("gxfiles://test1")

    assert file_source_pair.path == "/"
    file_source = file_source_pair.file_source
    res, _ = file_source.list("/", recursive=recursive, user_context=user_context)
    a_file = find(res, class_="File", name=filename)
    assert a_file

    if contains:
        assert_realizes_contains(file_sources, f"gxfiles://test1/{filename}", contents, user_context=user_context)
    else:
        assert_realizes_as(file_sources, f"gxfiles://test1/{filename}", contents, user_context=user_context)
