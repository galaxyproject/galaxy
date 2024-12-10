# docker run -v `pwd`/test/integration/webdav/data:/media  -e WEBDAV_USERNAME=alice -e WEBDAV_PASSWORD=secret1234 -p 7083:7083 jmchilton/webdavdev
# GALAXY_TEST_WEBDAV=1 pytest test/unit/files/test_webdav.py
import os

import pytest

from galaxy.files.plugins import FileSourcePluginsConfig
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
FILE_SOURCES_CONF_NO_USE_TEMP_FILES = os.path.join(SCRIPT_DIRECTORY, "webdav_file_sources_without_use_temp_conf.yml")
USER_FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "webdav_user_file_sources_conf.yml")

skip_if_no_webdav = pytest.mark.skipif(not os.environ.get("GALAXY_TEST_WEBDAV"), reason="GALAXY_TEST_WEBDAV not set")


@skip_if_no_webdav
@pytest.mark.asyncio
async def test_file_source():
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path("gxfiles://test1")

    assert file_source_pair.path == "/"
    file_source = file_source_pair.file_source
    res, _ = file_source.list("/", recursive=True)
    a_file = find_file_a(res)
    assert a_file
    assert a_file["uri"] == "gxfiles://test1/a", a_file

    res, _ = file_source.list("/", recursive=False)
    file_a = find_file_a(res)
    assert file_a
    assert file_a["uri"] == "gxfiles://test1/a"
    assert file_a["name"] == "a"

    subdir1 = find(res, name="subdir1")
    assert subdir1["class"] == "Directory"
    assert subdir1["uri"] == "gxfiles://test1/subdir1"

    res = await list_dir(file_sources, "gxfiles://test1/subdir1", recursive=False)
    subdir2 = find(res, name="subdir2")
    assert subdir2, res
    assert subdir2["uri"] == "gxfiles://test1/subdir1/subdir2"

    file_c = find(res, name="c")
    assert file_c, res
    assert file_c["uri"] == "gxfiles://test1/subdir1/c"


@skip_if_no_webdav
def test_sniff_to_tmp():
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    _download_and_check_file(file_sources)


@skip_if_no_webdav
@pytest.mark.asyncio
async def test_serialization():
    configs = [FILE_SOURCES_CONF_NO_USE_TEMP_FILES, FILE_SOURCES_CONF]
    for config in configs:
        # serialize the configured file sources and rematerialize them,
        # ensure they still function. This is needed for uploading files.
        file_sources = serialize_and_recover(configured_file_sources(config))

        res = await list_root(file_sources, "gxfiles://test1", recursive=True)
        assert find_file_a(res)

        res = await list_root(file_sources, "gxfiles://test1", recursive=False)
        assert find_file_a(res)

        _download_and_check_file(file_sources)


@skip_if_no_webdav
def test_config_options():
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    fs = file_sources._file_sources[0]
    user_context = user_context_fixture()
    assert fs._open_fs(user_context).use_temp_files

    file_sources = configured_file_sources(FILE_SOURCES_CONF_NO_USE_TEMP_FILES)
    fs = file_sources._file_sources[0]
    user_context = user_context_fixture()
    assert not fs._open_fs(user_context).use_temp_files

    disable_default_use_temp = FileSourcePluginsConfig(
        webdav_use_temp_files=False,
    )
    file_sources = configured_file_sources(FILE_SOURCES_CONF, disable_default_use_temp)
    fs = file_sources._file_sources[0]
    user_context = user_context_fixture()
    assert not fs._open_fs(user_context).use_temp_files


@skip_if_no_webdav
@pytest.mark.asyncio
async def test_serialization_user():
    file_sources_o = configured_file_sources(USER_FILE_SOURCES_CONF)
    user_context = user_context_fixture()

    res = await list_root(file_sources_o, "gxfiles://test1", recursive=True, user_context=user_context)
    assert find_file_a(res)

    file_sources = serialize_and_recover(file_sources_o, user_context=user_context)
    res = await list_root(file_sources, "gxfiles://test1", recursive=True, user_context=None)
    assert find_file_a(res)
