import pytest

from galaxy.config import GalaxyAppConfiguration, get_reloadable_config_options


@pytest.fixture
def mock_configuration_init(monkeypatch):
    def mock_init(self, **kwargs):
        self._set_reloadable_properties(kwargs)

    monkeypatch.setattr(GalaxyAppConfiguration, '__init__', mock_init)


def test_load_default_values(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    reloadable_config_options = get_reloadable_config_options()
    assert len(reloadable_config_options) == 14
    assert appconfig.message_box_content == reloadable_config_options['message_box_content']
    assert appconfig.welcome_url == reloadable_config_options['welcome_url']
    assert appconfig.tool_name_boost == reloadable_config_options['tool_name_boost']
    assert appconfig.tool_section_boost == reloadable_config_options['tool_section_boost']
    assert appconfig.tool_description_boost == reloadable_config_options['tool_description_boost']
    assert appconfig.tool_label_boost == reloadable_config_options['tool_label_boost']
    assert appconfig.tool_stub_boost == reloadable_config_options['tool_stub_boost']
    assert appconfig.tool_help_boost == reloadable_config_options['tool_help_boost']
    assert appconfig.tool_search_limit == reloadable_config_options['tool_search_limit']
    assert appconfig.tool_enable_ngram_search == reloadable_config_options['tool_enable_ngram_search']
    assert appconfig.tool_ngram_minsize == reloadable_config_options['tool_ngram_minsize']
    assert appconfig.tool_ngram_maxsize == reloadable_config_options['tool_ngram_maxsize']
    assert appconfig.admin_users == reloadable_config_options['admin_users']
    assert appconfig.cleanup_job == reloadable_config_options['cleanup_job']


def test_load_value_from_kwargs(mock_configuration_init):
    appconfig = GalaxyAppConfiguration(welcome_url='foo')
    assert appconfig.welcome_url == 'foo'


def test_update_reloadable_property__message_box_content(mock_configuration_init):
    appconfig = GalaxyAppConfiguration()
    appconfig.update_reloadable_property('welcome_url', 'foo')
    appconfig.update_reloadable_property('message_box_content', 'bar')
    appconfig.update_reloadable_property('tool_name_boost', 1)
    appconfig.update_reloadable_property('tool_section_boost', 2)
    appconfig.update_reloadable_property('tool_description_boost', 3)
    appconfig.update_reloadable_property('tool_label_boost', 4)
    appconfig.update_reloadable_property('tool_stub_boost', 5)
    appconfig.update_reloadable_property('tool_help_boost', 6)
    appconfig.update_reloadable_property('tool_search_limit', 7)
    appconfig.update_reloadable_property('tool_enable_ngram_search', True)
    appconfig.update_reloadable_property('tool_ngram_minsize', 8)
    appconfig.update_reloadable_property('tool_ngram_maxsize', 9)
    appconfig.update_reloadable_property('admin_users', 'tuor@gondolin.net, ulmo@valinor.gov')
    appconfig.update_reloadable_property('cleanup_job', 'never')

    assert appconfig.welcome_url == 'foo'
    assert appconfig.message_box_content == 'bar'
    assert appconfig.tool_name_boost == 1
    assert appconfig.tool_section_boost == 2
    assert appconfig.tool_description_boost == 3
    assert appconfig.tool_label_boost == 4
    assert appconfig.tool_stub_boost == 5
    assert appconfig.tool_help_boost == 6
    assert appconfig.tool_search_limit == 7
    assert appconfig.tool_enable_ngram_search is True
    assert appconfig.tool_ngram_minsize == 8
    assert appconfig.tool_ngram_maxsize == 9
    assert appconfig.admin_users == 'tuor@gondolin.net, ulmo@valinor.gov'
    assert appconfig.admin_users_list == ['tuor@gondolin.net', 'ulmo@valinor.gov']
    assert appconfig.cleanup_job == 'never'
