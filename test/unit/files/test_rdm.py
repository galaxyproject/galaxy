import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.files.unittest_utils import TestConfiguredFileSources
from ._util import (
    user_context_fixture,
    write_from,
)


@pytest.mark.parametrize(
    "plugin_type, scheme",
    [
        ("dataverse", "dataverse"),
        ("inveniordm", "invenio"),
        ("zenodo", "zenodo"),
    ],
)
def test_write_to_repository_root_is_rejected(plugin_type, scheme):
    plugin = {"type": plugin_type, "url": "https://repository.example.org", "writable": True}
    file_sources = TestConfiguredFileSources(FileSourcePluginsConfig(), {"test1": plugin}, None)
    user_context = user_context_fixture(file_sources=file_sources)

    with pytest.raises(RequestParameterInvalidException, match="root"):
        write_from(file_sources, f"{scheme}://test1/data.txt", "data", user_context=user_context)
