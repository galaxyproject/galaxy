import copy

from galaxy import model
from .test_galaxy_mapping import BaseModelTestCase


class MutableColumnTest(BaseModelTestCase):

    def persist_and_reload(self, item):
        item_id = item.id
        self.model.session.flush()
        self.model.session.expunge_all()
        return self.model.session.query(model.Workflow).get(item_id)

    def test_metadata_mutable_column(self):
        w = model.Workflow()
        self.model.session.add(w)
        self.model.session.flush()
        w.reports_config = {'x': 'z'}
        persisted = self.persist_and_reload(w)
        assert persisted.reports_config == {'x': 'z'}
        persisted.reports_config['x'] = '1'
        persisted = self.persist_and_reload(persisted)
        assert persisted.reports_config['x'] == '1'
        # test string
        persisted.reports_config = 'abcdefg'
        persisted = self.persist_and_reload(persisted)
        assert persisted.reports_config == 'abcdefg'
        # test int
        persisted.reports_config = 1
        persisted = self.persist_and_reload(persisted)
        assert persisted.reports_config == 1
        # test float
        persisted.reports_config = 1.1
        persisted = self.persist_and_reload(persisted)
        assert persisted.reports_config == 1.1
        # test bool
        persisted.reports_config = True
        persisted = self.persist_and_reload(persisted)
        assert persisted.reports_config is True
        # Test nested dict/list
        persisted.reports_config = {'list': [[1, 2, 3]]}
        persisted = self.persist_and_reload(persisted)
        assert persisted.reports_config == {'list': [[1, 2, 3]]}
        copy.deepcopy(persisted.reports_config)
        assert persisted.reports_config.pop('list') == [[1, 2, 3]]
        persisted = self.persist_and_reload(persisted)
        assert persisted.reports_config == {}
        persisted.reports_config.update({'x': 'z'})
        persisted = self.persist_and_reload(persisted)
        assert persisted.reports_config == {'x': 'z'}
        del persisted.reports_config['x']
        persisted = self.persist_and_reload(persisted)
        assert persisted.reports_config == {}
        persisted.reports_config = {'x': {'y': 'z'}}
        persisted = self.persist_and_reload(persisted)
        assert persisted.reports_config == {'x': {'y': 'z'}}
        # These tests are failing ... at least since 20.09,
        # but nested mutable change tracking might have
        # never worked

        # persisted.reports_config['x']['y'] = 'x'
        # persisted = self.persist_and_reload(persisted)
        # assert persisted.reports_config == {'x': {'y': 'x'}}
        # persisted.reports_config[0].append(2)
        # persisted = self.persist_and_reload(persisted)
        # assert persisted.reports_config[0] == [1, 2]
        # persisted.reports_config[0].extend([3, 4])
        # persisted = self.persist_and_reload(persisted)
        # assert persisted.reports_config[0] == [1, 2, 3, 4]
        # persisted.reports_config[0].remove(4)
        # persisted = self.persist_and_reload(persisted)
        # assert persisted.reports_config[0] == [1, 2, 3]
