from unittest.mock import Mock

import pytest

from galaxy import model
from galaxy.model.base import transaction
from galaxy.tools.parameters.options import ParameterOption
from galaxy.tools.parameters.workflow_utils import RuntimeValue
from .util import BaseParameterTestCase


class TestSelectToolParameter(BaseParameterTestCase):
    def test_validated_values(self):
        self.options_xml = """<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>"""
        with pytest.raises(ValueError) as exc_info:
            self.param.from_json("42", self.trans, {"input_bam": model.HistoryDatasetAssociation()})
            assert str(exc_info.value) == "parameter 'my_name': requires a value, but no legal values defined"

    def test_validated_values_missing_dependency(self):
        self.options_xml = """<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>"""
        with pytest.raises(ValueError) as exc_info:
            self.param.from_json("42", self.trans)
            assert str(exc_info.value) == "parameter 'my_name': requires a value, but no legal values defined"

    def test_unvalidated_values(self):
        self.options_xml = """<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>"""
        self.trans.workflow_building_mode = True
        assert self.param.from_json("42", self.trans) == "42"

    def test_validated_datasets(self):
        self.options_xml = """<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>"""
        with pytest.raises(ValueError) as exc_info:
            self.param.from_json(model.HistoryDatasetAssociation(), self.trans, {"input_bam": None})
            assert str(exc_info.value) == "parameter 'my_name': requires a value, but no legal values defined"

    def test_unvalidated_datasets(self):
        self.options_xml = """<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>"""
        self.trans.workflow_building_mode = True
        assert isinstance(
            self.param.from_json(model.HistoryDatasetAssociation(), self.trans, {"input_bam": RuntimeValue()}),
            model.HistoryDatasetAssociation,
        )

    def test_filter_param_value(self):
        self.options_xml = """<options from_data_table="test_table"><filter type="param_value" ref="input_bam" column="0" /></options>"""
        assert ParameterOption("testname1", "testpath1", False) in self.param.get_options(
            self.trans, {"input_bam": "testname1"}
        )
        assert ParameterOption("testname2", "testpath2", False) in self.param.get_options(
            self.trans, {"input_bam": "testname2"}
        )
        assert len(self.param.get_options(self.trans, {"input_bam": "testname3"})) == 0

    def test_filter_param_value2(self):
        # Same test as above, but filtering on a different column.
        self.options_xml = """<options from_data_table="test_table"><filter type="param_value" ref="input_bam" column="1" /></options>"""
        assert ParameterOption("testname1", "testpath1", False) in self.param.get_options(
            self.trans, {"input_bam": "testpath1"}
        )
        assert ParameterOption("testname2", "testpath2", False) in self.param.get_options(
            self.trans, {"input_bam": "testpath2"}
        )
        assert len(self.param.get_options(self.trans, {"input_bam": "testpath3"})) == 0

    # TODO: Good deal of overlap here with TestDataToolParameter, refactor.
    def setUp(self):
        super().setUp()
        self.test_history = model.History()
        self.app.model.context.add(self.test_history)
        session = self.app.model.context
        with transaction(session):
            session.commit()
        self.app.tool_data_tables["test_table"] = MockToolDataTable()
        self.trans = Mock(
            app=self.app,
            get_history=lambda: self.test_history,
            get_current_user_roles=lambda: [],
            workflow_building_mode=False,
            webapp=Mock(name="galaxy"),
            user=None,
        )
        self.type = "select"
        self.set_data_ref = False
        self.multiple = False
        self.optional = False
        self.options_xml = ""
        self._param = None

    @property
    def param(self):
        if not self._param:
            multi_text = ""
            if self.multiple:
                multi_text = 'multiple="True"'
            optional_text = ""
            if self.optional:
                optional_text = 'optional="True"'
            options_text = self.options_xml
            data_ref_text = ""
            if self.set_data_ref:
                data_ref_text = 'data_ref="input_bam"'
            param_str = f"""<param name="my_name" type="{self.type}" {data_ref_text} {multi_text} {optional_text}>{options_text}</param>"""
            self._param = self._parameter_for(xml=param_str)

        return self._param


class MockToolDataTable:
    def __init__(self):
        self.columns = dict(
            name=0,
            value=1,
        )
        self.missing_index_file = None

    def get_fields(self):
        return [["testname1", "testpath1"], ["testname2", "testpath2"]]
