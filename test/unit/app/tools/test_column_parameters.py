"""Tests for tool parameters, more tests exist in test_data_parameters.py and
test_select_parameters.py.
"""

import pytest

from galaxy import model
from galaxy.app_unittest_utils.tools_support import datatypes_registry
from galaxy.tools.parameters.basic import ParameterValueError
from galaxy.tools.parameters.workflow_utils import RuntimeValue
from galaxy.util import bunch
from .util import BaseParameterTestCase


class TestDataColumnParameter(BaseParameterTestCase):
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

    def test_from_json_rejects_non_numeric_column_for_empty_dataset(self):
        for value in ["1;id", "c1;id", "-1", "1.5", "\u00b2", "B"]:
            with pytest.raises(ParameterValueError):
                self.param.from_json(value, self.trans, {"input_tsv": self.build_ready_hda()})

    def test_multiple_from_json_rejects_non_numeric_column_for_empty_dataset(self):
        self.multiple = True
        for value in ["1,2;id", ["1", "2;id"], "1\n$(id)"]:
            with pytest.raises(ParameterValueError):
                self.param.from_json(value, self.trans, {"input_tsv": self.build_ready_hda()})

    def test_from_json_resolves_label_for_empty_dataset(self):
        value = self.param.from_json("c3: header", self.trans, {"input_tsv": self.build_ready_hda()})
        assert value == "3"

    def test_multiple_from_json_resolves_labels_for_empty_dataset(self):
        self.multiple = True
        value = self.param.from_json(["c1: a b", "3", "c2: $(id)"], self.trans, {"input_tsv": self.build_ready_hda()})
        assert value == ["1", "3", "2"]

    def test_from_json_rejects_malformed_label_for_empty_dataset(self):
        for value in ["c: header", "c1:header", "x1: header", "c1;id: header"]:
            with pytest.raises(ParameterValueError):
                self.param.from_json(value, self.trans, {"input_tsv": self.build_ready_hda()})

    def test_multiple_from_json_newline_separated(self):
        self.multiple = True
        value = self.param.from_json("c1\n3", self.trans, {"input_tsv": self.build_ready_hda()})
        assert value == ["1", "3"]

    def test_from_json_runtime_data_ref(self):
        assert self.param.from_json("3", self.trans, {"input_tsv": RuntimeValue()}) == "3"

    def test_from_json_rejects_non_numeric_column_for_runtime_data_ref(self):
        with pytest.raises(ParameterValueError):
            self.param.from_json("1;id", self.trans, {"input_tsv": RuntimeValue()})

    def test_from_json_rejects_non_numeric_column_for_deferred_dataset(self):
        deferred_hda = self.build_hda(extension="tabular", state="deferred")
        with pytest.raises(ParameterValueError):
            self.param.from_json("B", self.trans, {"input_tsv": deferred_hda})

    def test_from_json_rejects_non_numeric_column_while_other_input_is_running(self):
        empty_hda = self.build_hda(extension="tabular", state="ok")
        running_hda = self.build_hda(extension="tabular", state="running")
        with pytest.raises(ParameterValueError):
            self.param.from_json("B", self.trans, {"input_tsv": empty_hda, "other": running_hda})

    def test_from_json_accepts_column_number_for_deferred_dataset(self):
        deferred_hda = self.build_hda(extension="tabular", state="deferred")
        assert self.param.from_json("2", self.trans, {"input_tsv": deferred_hda}) == "2"

    def test_from_json_workflow_building_mode(self):
        self.trans["workflow_building_mode"] = True
        assert self.param.from_json("3", self.trans, {"input_tsv": RuntimeValue()}) == "3"
        self.multiple = True
        self._param = None
        assert self.param.from_json("1,3", self.trans, {"input_tsv": RuntimeValue()}) == ["1", "3"]

    def test_get_initial_value_default(self):
        assert "1" == self.param.get_initial_value(self.trans, {"input_tsv": self.build_ready_hda()})

    def test_get_initial_value_override_legacy(self):
        self.other_attributes = "default_value='2'"
        assert "2" == self.param.get_initial_value(self.trans, {"input_tsv": self.build_ready_hda()})

    def test_get_initial_value_override_newstyle(self):
        self.other_attributes = "value='2'"
        assert "2" == self.param.get_initial_value(self.trans, {"input_tsv": self.build_ready_hda()})

    def test_get_initial_value_override_newstyle_strips_c(self):
        self.other_attributes = "value='c2'"
        assert "2" == self.param.get_initial_value(self.trans, {"input_tsv": self.build_ready_hda()})

    def setUp(self):
        super().setUp()
        self.test_history = model.History()
        session = self.app.model.context
        session.add(self.test_history)
        session.commit()
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
        return self.build_hda(extension="interval", state="ok")

    def build_hda(self, extension, state):
        hist = model.History()
        self.app.model.context.add(hist)
        hda = hist.add_dataset(
            model.HistoryDatasetAssociation(extension=extension, create_dataset=True, sa_session=self.app.model.context)
        )
        hda.state = state
        return hda

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
            param_str = f"""<param name="my_name" type="{self.type}" {data_ref_text} {multi_text} {optional_text} {self.other_attributes}></param>"""
            self._param = self._parameter_for(xml=param_str)
            self._param.ref_input = bunch.Bunch(formats=[datatypes_registry.get_datatype_by_extension("tabular")])

        return self._param
