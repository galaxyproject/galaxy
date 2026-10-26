import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.files.sources._rdm import RDMFilesSource
from galaxy.files.unittest_utils import TestConfiguredFileSources
from ._util import (
    user_context_fixture,
    write_from,
)

RDM_PLUGINS = [
    ("dataverse", "dataverse"),
    ("inveniordm", "invenio"),
    ("zenodo", "zenodo"),
]


def _configured_file_sources(plugin_type: str) -> TestConfiguredFileSources:
    plugin = {"type": plugin_type, "url": "https://repository.example.org", "writable": True}
    return TestConfiguredFileSources(FileSourcePluginsConfig(), {"test1": plugin}, None)


@pytest.mark.parametrize("plugin_type, scheme", RDM_PLUGINS)
def test_write_to_repository_root_is_rejected(plugin_type, scheme):
    file_sources = _configured_file_sources(plugin_type)
    user_context = user_context_fixture(file_sources=file_sources)

    with pytest.raises(RequestParameterInvalidException, match="root"):
        write_from(file_sources, f"{scheme}://test1/data.txt", "data", user_context=user_context)


@pytest.mark.parametrize("plugin_type, scheme", RDM_PLUGINS)
@pytest.mark.parametrize("target_path", ["/123/data.txt", "/doi:10.70122/FK2/ABCDEF/data.txt"])
def test_write_into_container_passes_root_check(plugin_type, scheme, target_path):
    file_sources = _configured_file_sources(plugin_type)
    file_source = file_sources.find_best_match(f"{scheme}://test1/")
    assert isinstance(file_source, RDMFilesSource)

    file_source._ensure_target_in_container(target_path)
