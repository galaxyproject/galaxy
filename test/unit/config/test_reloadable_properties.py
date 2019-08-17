import pytest

from galaxy.config import (
    GalaxyAppConfiguration,
    RELOADABLE_CONFIG_OPTIONS,
)


@pytest.fixture
def mock_configuration_init(monkeypatch):
    def mock_init(self, **kwargs):
        self._set_reloadable_properties(kwargs)

    monkeypatch.setattr(GalaxyAppConfiguration, '__init__', mock_init)


def test_load_default_values(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()

    assert len(RELOADABLE_CONFIG_OPTIONS) == 14
    assert appconfig.message_box_content == RELOADABLE_CONFIG_OPTIONS['message_box_content']
    assert appconfig.welcome_url == RELOADABLE_CONFIG_OPTIONS['welcome_url']
    assert appconfig.tool_name_boost == RELOADABLE_CONFIG_OPTIONS['tool_name_boost']
    assert appconfig.tool_section_boost == RELOADABLE_CONFIG_OPTIONS['tool_section_boost']
    assert appconfig.tool_description_boost == RELOADABLE_CONFIG_OPTIONS['tool_description_boost']
    assert appconfig.tool_label_boost == RELOADABLE_CONFIG_OPTIONS['tool_label_boost']
    assert appconfig.tool_stub_boost == RELOADABLE_CONFIG_OPTIONS['tool_stub_boost']
    assert appconfig.tool_help_boost == RELOADABLE_CONFIG_OPTIONS['tool_help_boost']
    assert appconfig.tool_search_limit == RELOADABLE_CONFIG_OPTIONS['tool_search_limit']
    assert appconfig.tool_enable_ngram_search == RELOADABLE_CONFIG_OPTIONS['tool_enable_ngram_search']
    assert appconfig.tool_ngram_minsize == RELOADABLE_CONFIG_OPTIONS['tool_ngram_minsize']
    assert appconfig.tool_ngram_maxsize == RELOADABLE_CONFIG_OPTIONS['tool_ngram_maxsize']
    assert appconfig.admin_users == RELOADABLE_CONFIG_OPTIONS['admin_users']
    assert appconfig.cleanup_job == RELOADABLE_CONFIG_OPTIONS['cleanup_job']


def test_load_value_from_kwargs(mock_configuration_init):
    appconfig = GalaxyAppConfiguration(welcome_url='foo')
    assert appconfig.welcome_url == 'foo'


def test_update_reloadable_property__message_box_content(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('message_box_content', 'foo')
    assert appconfig.message_box_content == 'foo'


def test_update_reloadable_property__welcome_url(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('welcome_url', 'foo')
    assert appconfig.welcome_url == 'foo'


def test_update_reloadable_property__tool_name_boost(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('tool_name_boost', 42)
    assert appconfig.tool_name_boost == 42


def test_update_reloadable_property__tool_section_boost(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('tool_section_boost', 42)
    assert appconfig.tool_section_boost == 42


def test_update_reloadable_property__tool_description_boost(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('tool_description_boost', 42)
    assert appconfig.tool_description_boost == 42


def test_update_reloadable_property__tool_label_boost(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('tool_label_boost', 42)
    assert appconfig.tool_label_boost == 42


def test_update_reloadable_property__tool_stub_boost(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('tool_stub_boost', 42)
    assert appconfig.tool_stub_boost == 42


def test_update_reloadable_property__tool_help_boost(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('tool_help_boost', 42)
    assert appconfig.tool_help_boost == 42


def test_update_reloadable_property__tool_search_limit(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('tool_search_limit', 42)
    assert appconfig.tool_search_limit == 42


def test_update_reloadable_property__tool_enable_ngram_search(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('tool_enable_ngram_search', True)
    assert appconfig.tool_enable_ngram_search is True


def test_update_reloadable_property__tool_ngram_minsize(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('tool_ngram_minsize', 42)
    assert appconfig.tool_ngram_minsize == 42


def test_update_reloadable_property__tool_ngram_maxsize(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('tool_ngram_maxsize', 42)
    assert appconfig.tool_ngram_maxsize == 42


def test_update_reloadable_property__admin_users(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('admin_users', 'tuor@gondolin.net, ulmo@valinor.gov')
    assert appconfig.admin_users == 'tuor@gondolin.net, ulmo@valinor.gov'
    assert appconfig.admin_users_list == ['tuor@gondolin.net', 'ulmo@valinor.gov']


def test_update_reloadable_property__cleanup_job(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('cleanup_job', 'never')
    assert appconfig.cleanup_job == 'never'
