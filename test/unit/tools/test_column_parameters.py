""" Tests for tool parameters, more tests exist in test_data_parameters.py and
test_select_parameters.py.
"""
from galaxy import model
from galaxy.util import bunch
from .test_parameter_parsing import BaseParameterTestCase
from ..tools_support import datatypes_registry


class DataColumnParameterTestCase(BaseParameterTestCase):

    def test_not_optional_by_default(self):
        assert not self.__param_optional()

    def test_force_select_disable(self):
        self.other_attributes = 'force_select="false"'
        assert self.__param_optional()

    def test_optional_override(self):
        self.other_attributes = 'optional="true"'
        assert self.__param_optional()

    def __param_optional(self):
        # TODO: don't break abstraction, try setting null value instead
        return self.param.optional

    def test_from_json(self):
        value = self.param.from_json("3", self.trans, {"input_tsv": self.build_ready_hda()})
        assert value == "3"

    def test_from_json_strips_c(self):
        value = self.param.from_json("c1", self.trans, {"input_tsv": self.build_ready_hda()})
        assert value == "1"

    def test_multiple_from_json(self):
        self.multiple = True
        value = self.param.from_json("1,2,3", self.trans, {"input_tsv": self.build_ready_hda()})
        assert value == ["1", "2", "3"]

    def test_multiple_from_json_with_c(self):
        self.multiple = True
        value = self.param.from_json("c1,c2,c3", self.trans, {"input_tsv": self.build_ready_hda()})
        assert value == ["1", "2", "3"]

    def test_get_initial_value_default(self):
        self.assertEqual('1', self.param.get_initial_value(self.trans, {"input_tsv": self.build_ready_hda()}))

    def test_get_initial_value_override_legacy(self):
        self.other_attributes = "default_value='2'"
        self.assertEqual('2', self.param.get_initial_value(self.trans, {"input_tsv": self.build_ready_hda()}))

    def test_get_initial_value_override_newstyle(self):
        self.other_attributes = "value='2'"
        self.assertEqual('2', self.param.get_initial_value(self.trans, {"input_tsv": self.build_ready_hda()}))

    def test_get_initial_value_override_newstyle_strips_c(self):
        self.other_attributes = "value='c2'"
        self.assertEqual('2', self.param.get_initial_value(self.trans, {"input_tsv": self.build_ready_hda()}))

    def setUp(self):
        super(DataColumnParameterTestCase, self).setUp()
        self.test_history = model.History()
        self.app.model.context.add(self.test_history)
        self.app.model.context.flush()
        self.trans = bunch.Bunch(
            app=self.app,
            get_history=lambda: self.test_history,
            get_current_user_roles=lambda: [],
            workflow_building_mode=False,
            webapp=bunch.Bunch(name="galaxy"),
        )

        self.type = "data_column"
        self.other_attributes = ""
        self.set_data_ref = "input_tsv"
        self.multiple = False
        self.optional = False
        self._param = None

    def build_ready_hda(self):
        hist = model.History()
        self.app.model.context.add(hist)
        ready_hda = hist.add_dataset(model.HistoryDatasetAssociation(extension='interval', create_dataset=True, sa_session=self.app.model.context))
        ready_hda.set_dataset_state('ok')
        return ready_hda

    @property
    def param(self):
        if not self._param:
            multi_text = ""
            if self.multiple:
                multi_text = 'multiple="True"'
            optional_text = ""
            if self.optional:
                optional_text = 'optional="True"'
            data_ref_text = ""
            if self.set_data_ref:
                data_ref_text = 'data_ref="input_tsv"'
            template_xml = '''<param name="my_name" type="%s" %s %s %s %s></param>'''
            param_str = template_xml % (self.type, data_ref_text, multi_text, optional_text, self.other_attributes)
            self._param = self._parameter_for(xml=param_str)
            self._param.ref_input = bunch.Bunch(formats=[datatypes_registry.get_datatype_by_extension("tabular")])

        return self._param
