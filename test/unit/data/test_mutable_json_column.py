import copy

from galaxy import model
from .test_galaxy_mapping import BaseModelTestCase


class TestMutableColumn(BaseModelTestCase):
    def persist_and_reload(self, item):
        item_id = item.id
        session = self.model.session
        session.commit()
        session.expunge_all()
        return session.get(model.DynamicTool, item_id)

    def test_metadata_mutable_column(self):
        w = model.DynamicTool()
        session = self.model.session
        session.add(w)
        session.commit()
        w.value = {"x": "z"}
        persisted = self.persist_and_reload(w)
        assert persisted.value == {"x": "z"}
        persisted.value["x"] = "1"
        persisted = self.persist_and_reload(persisted)
        assert persisted.value["x"] == "1"
        # test string
        persisted.value = "abcdefg"
        persisted = self.persist_and_reload(persisted)
        assert persisted.value == "abcdefg"
        # test int
        persisted.value = 1
        persisted = self.persist_and_reload(persisted)
        assert persisted.value == 1
        # test float
        persisted.value = 1.1
        persisted = self.persist_and_reload(persisted)
        assert persisted.value == 1.1
        # test bool
        persisted.value = True
        persisted = self.persist_and_reload(persisted)
        assert persisted.value is True
        # Test nested dict/list
        persisted.value = {"list": [[1, 2, 3]]}
        persisted = self.persist_and_reload(persisted)
        assert persisted.value == {"list": [[1, 2, 3]]}
        copy.deepcopy(persisted.value)
        assert persisted.value.pop("list") == [[1, 2, 3]]
        persisted = self.persist_and_reload(persisted)
        assert persisted.value == {}
        persisted.value.update({"x": "z"})
        persisted = self.persist_and_reload(persisted)
        assert persisted.value == {"x": "z"}
        del persisted.value["x"]
        persisted = self.persist_and_reload(persisted)
        assert persisted.value == {}
        persisted.value = {"x": {"y": "z"}}
        persisted = self.persist_and_reload(persisted)
        assert persisted.value == {"x": {"y": "z"}}
        # These tests are failing ... at least since 20.09,
        # but nested mutable change tracking might have
        # never worked

        # persisted.value['x']['y'] = 'x'
        # persisted = self.persist_and_reload(persisted)
        # assert persisted.value == {'x': {'y': 'x'}}
        # persisted.value[0].append(2)
        # persisted = self.persist_and_reload(persisted)
        # assert persisted.value[0] == [1, 2]
        # persisted.value[0].extend([3, 4])
        # persisted = self.persist_and_reload(persisted)
        # assert persisted.value[0] == [1, 2, 3, 4]
        # persisted.value[0].remove(4)
        # persisted = self.persist_and_reload(persisted)
        # assert persisted.value[0] == [1, 2, 3]
