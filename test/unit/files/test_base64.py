import base64
import os

from galaxy import util
from ._util import (
    assert_realizes_as,
    configured_file_sources,
    user_context_fixture,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "base64_file_sources_conf.yml")


def test_file_source():
    ORIGINAL_STRING = "I'm a b64 encoded string"
    test_url = f"base64://{util.unicodify(base64.b64encode(util.smart_str(ORIGINAL_STRING)))}"
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test1"

    assert_realizes_as(file_sources, test_url, ORIGINAL_STRING, user_context=user_context)
