from typing import (
    Any,
    Optional,
    Tuple,
)

from galaxy import model
from galaxy.app_unittest_utils import galaxy_mock
from .util import BaseParameterTestCase


class DataToolParameterTestCase(BaseParameterTestCase):
    def test_to_python_none_values(self):
        assert self.param.to_python(None, self.app) is None
        assert self.param.to_python("None", self.app) is None
        assert self.param.to_python("", self.app) is None

    def test_to_python_hda(self):
        hda = self._new_hda()
        as_python = self.param.to_python(hda.id, self.app)
        assert hda == as_python

    def test_to_python_multi_hdas(self):
        hda1 = self._new_hda()
        hda2 = self._new_hda()
        as_python = self.param.to_python(f"{hda1.id},{hda2.id}", self.app)
        assert as_python == [hda1, hda2]

    def test_to_python_multi_none(self):
        self.multiple = True
        hda = self._new_hda()
        # Selection is Optional. may be selected with other stuff,
        # not sure the UI should really allow this but easy enough
        # to just filter it out.
        self.assertEqual([hda], self.param.to_python("%s,None" % hda.id, self.app))

    def test_field_filter_on_types(self):
        hda1 = MockHistoryDatasetAssociation(name="hda1", id=1)
        hda2 = MockHistoryDatasetAssociation(name="hda2", id=2)
        self.stub_active_datasets(hda1, hda2)
        field = self._simple_field()
        assert len(field["options"]["hda"]) == 2
        assert field["options"]["hda"][0]["name"] == "hda2"
        assert field["options"]["hda"][1]["name"] == "hda1"

        hda2.extension = "data"
        hda2.conversion_destination = (False, None, None)
        field = self._simple_field()
        assert len(field["options"]["hda"]) == 1, field
        assert field["options"]["hda"][0]["name"] == "hda1"

    def test_field_display_hidden_hdas_only_if_selected(self):
        hda1 = MockHistoryDatasetAssociation(name="hda1", id=1)
        hda2 = MockHistoryDatasetAssociation(name="hda2", id=2)
        hda1.visible = False
        hda2.visible = False
        self.stub_active_datasets(hda1, hda2)
        field = self._simple_field(other_values={"data2": hda2})
        assert len(field["options"]["hda"]) == 1  # hda1 not an option, not visible or selected
        assert field["options"]["hda"][0]["name"] == "(hidden) hda2"

    def test_field_display_deleted_hdas_only_if_selected(self):
        hda1 = MockHistoryDatasetAssociation(name="hda1", id=1)
        hda2 = MockHistoryDatasetAssociation(name="hda2", id=2)
        hda1.visible = False
        hda2.deleted = True
        self.stub_active_datasets(hda1, hda2)
        field = self._simple_field(other_values={"data2": hda2})
        assert len(field["options"]["hda"]) == 1  # hda1 not an option, not visible or selected
        assert field["options"]["hda"][0]["name"] == "(deleted) hda2"

    def test_field_implicit_conversion_new(self):
        hda1 = MockHistoryDatasetAssociation(name="hda1", id=1)
        hda1.extension = "data"
        hda1.conversion_destination = (False, "tabular", None)
        self.stub_active_datasets(hda1)
        field = self._simple_field()
        assert len(field["options"]["hda"]) == 1
        assert field["options"]["hda"][0]["name"] == "hda1 (as tabular)"
        assert field["options"]["hda"][0]["hid"] == 1

    def test_field_implicit_conversion_existing(self):
        hda1 = MockHistoryDatasetAssociation(name="hda1", id=1)
        hda1.extension = "data"
        hda1.conversion_destination = (False, "tabular", MockHistoryDatasetAssociation(name="hda1converted", id=2))
        self.stub_active_datasets(hda1)
        field = self._simple_field()
        assert len(field["options"]["hda"]) == 1
        assert field["options"]["hda"][0]["name"] == "hda1 (as tabular)"
        # This is difference with previous test, value is existing
        # hda id not new one.
        assert field["options"]["hda"][0]["hid"] == 2

    def test_field_multiple(self):
        self.multiple = True
        field = self._simple_field()
        assert field["multiple"]

    def test_field_empty_selection(self):
        field = self._simple_field()
        assert len(field["options"]["hda"]) == 0
        assert len(field["options"]["hdca"]) == 0

    def test_field_empty_selection_optional(self):
        self.optional = True
        field = self._simple_field()
        assert field["optional"]

    def test_get_initial_value(self):
        hda1 = MockHistoryDatasetAssociation(name="hda1", id=1)
        hda2 = MockHistoryDatasetAssociation(name="hda2", id=2)
        self.stub_active_datasets(hda1, hda2)
        assert hda2 == self.param.get_initial_value(self.trans, {})

    def test_get_initial_value_is_none_if_no_match(self):
        hda1 = MockHistoryDatasetAssociation(name="hda1", id=1)
        hda1.visible = False
        hda2 = MockHistoryDatasetAssociation(name="hda2", id=2)
        hda2.visible = False
        self.stub_active_datasets(hda1, hda2)
        assert self.param.get_initial_value(self.trans, {}) is None

    def test_get_initial_none_when_optional(self):
        self.optional = True
        hda1 = MockHistoryDatasetAssociation(name="hda1", id=1)
        hda2 = MockHistoryDatasetAssociation(name="hda2", id=2)
        self.stub_active_datasets(hda1, hda2)
        assert self.param.get_initial_value(self.trans, {}) is None

    def test_get_initial_with_previously_converted_data(self):
        hda1 = MockHistoryDatasetAssociation(name="hda1", id=1)
        hda1.extension = "data"
        converted = MockHistoryDatasetAssociation(name="hda1converted", id=2)
        hda1.conversion_destination = (False, "tabular", converted)
        self.stub_active_datasets(hda1)
        assert converted == self.param.get_initial_value(self.trans, {})

    def test_get_initial_with_to_be_converted_data(self):
        hda1 = MockHistoryDatasetAssociation(name="hda1", id=1)
        hda1.extension = "data"
        hda1.conversion_destination = (False, "tabular", None)
        self.stub_active_datasets(hda1)
        assert hda1 == self.param.get_initial_value(self.trans, {}), hda1

    def _new_hda(self):
        hda = model.HistoryDatasetAssociation()
        hda.visible = True
        hda.dataset = model.Dataset()
        self.app.model.context.add(hda)
        self.app.model.context.flush()
        return hda

    def setUp(self):
        super().setUp()
        self.test_history = model.History()
        self.app.model.context.add(self.test_history)
        self.app.model.context.flush()
        self.trans = galaxy_mock.MockTrans(history=self.test_history)
        self.multiple = False
        self.optional = False
        self._param = None

    def stub_active_datasets(self, *hdas):
        self.test_history._active_datasets_and_roles = [h for h in hdas if not h.deleted]
        self.test_history._active_visible_datasets_and_roles = [h for h in hdas if not h.deleted and h.visible]

    def _simple_field(self, **kwds):
        return self.param.to_dict(trans=self.trans, **kwds)

    @property
    def param(self):
        if not self._param:
            multi_text = ""
            if self.multiple:
                multi_text = 'multiple="True"'
            optional_text = ""
            if self.optional:
                optional_text = 'optional="True"'
            template_xml = """<param name="data2" type="data" format="txt" %s %s></param>"""
            param_str = template_xml % (multi_text, optional_text)
            self._param = self._parameter_for(tool=self.mock_tool, xml=param_str)

        return self._param


class MockHistoryDatasetAssociation:
    """Fake HistoryDatasetAssociation stubbed out for testing matching and
    stuff like that.
    """

    def __init__(self, test_dataset=None, name="Test Dataset", id=1):
        if not test_dataset:
            test_dataset = model.Dataset()
            test_dataset.state = model.Dataset.states.OK
        self.states = model.HistoryDatasetAssociation.states
        self.deleted = False
        self.dataset = test_dataset
        self.visible = True
        self.conversion_destination: Tuple[bool, Optional[str], Optional[Any]] = (True, None, None)
        self.extension = "txt"
        self.dbkey = "hg19"
        self.implicitly_converted_parent_datasets = False
        self.name = name
        self.hid = id
        self.id = id
        self.children = []
        self.tags = []
        self.metadata = None

    @property
    def state(self):
        return self.dataset.state

    def get_dbkey(self):
        return self.dbkey

    def find_conversion_destination(self, formats):
        return self.conversion_destination
