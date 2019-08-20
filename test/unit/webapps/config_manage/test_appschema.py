from galaxy.webapps.config_manage import AppSchema


def test_get_reloadable_option_defaults(monkeypatch):
    mapping = {
        'item1': {
            'default': 1,
            'reloadable': True,
        },
        'item2': {
            'default': 2,
            'reloadable': True,
        },
        'item3': {
            'default': 3,
            'reloadable': False,
        },
        'item4': {
            'default': 4,
        },
    }

    def mock_init(self):
        self.reloadable_options = self._load_reloadable_options(mapping)

    def mock_get_app_option(self, name):
        return mapping[name]

    monkeypatch.setattr(AppSchema, '__init__', mock_init)
    monkeypatch.setattr(AppSchema, 'get_app_option', mock_get_app_option)

    appschema = AppSchema()

    options = appschema.get_reloadable_option_defaults()

    assert len(options) == 2
    assert options['item1'] == 1
    assert options['item2'] == 2
