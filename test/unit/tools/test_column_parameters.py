""" Tests for tool parameters, more tests exist in test_data_parameters.py and
test_select_parameters.py.
"""

from unittest import TestCase
from galaxy.tools.parameters import basic
from galaxy.util import bunch
from galaxy import model
from elementtree.ElementTree import XML

import tools_support


class DataColumnParameterTestCase( TestCase, tools_support.UsesApp ):

    def test_from_html(self):
        value = self.param.from_html("3", self.trans, { "input_tsv": self.build_ready_hda()  } )
        assert value == "3"

    def test_from_html_strips_c(self):
        value = self.param.from_html("c1", self.trans, { "input_tsv": self.build_ready_hda()  } )
        assert value == "1"

    def test_multiple_from_html(self):
        self.multiple = True
        value = self.param.from_html("1,2,3", self.trans, { "input_tsv": self.build_ready_hda()  } )
        assert value == ["1", "2", "3"]

    def test_multiple_from_html_with_c(self):
        self.multiple = True
        value = self.param.from_html("c1,c2,c3", self.trans, { "input_tsv": self.build_ready_hda()  } )
        assert value == ["1", "2", "3"]

    def test_get_initial_value_default(self):
        self.assertEqual( '1', self.param.get_initial_value( self.trans, { "input_tsv": self.build_ready_hda()  } ) )

    def test_get_initial_value_override_legacy(self):
        self.other_attributes = "default_value='2'"
        self.assertEqual( '2', self.param.get_initial_value( self.trans, { "input_tsv": self.build_ready_hda() } ) )

    def test_get_initial_value_override_newstyle(self):
        self.other_attributes = "value='2'"
        self.assertEqual( '2', self.param.get_initial_value( self.trans, { "input_tsv": self.build_ready_hda() } ) )

    def test_get_initial_value_override_newstyle_strips_c(self):
        self.other_attributes = "value='c2'"
        self.assertEqual( '2', self.param.get_initial_value( self.trans, { "input_tsv": self.build_ready_hda() } ) )

    def setUp( self ):
        self.setup_app( mock_model=False )
        self.mock_tool = bunch.Bunch(
            app=self.app,
            tool_type="default",
        )
        self.test_history = model.History()
        self.app.model.context.add( self.test_history )
        self.app.model.context.flush()
        self.trans = bunch.Bunch(
            app=self.app,
            get_history=lambda: self.test_history,
            get_current_user_roles=lambda: [],
            workflow_building_mode=False,
            webapp=bunch.Bunch( name="galaxy" ),
        )

        self.type = "data_column"
        self.other_attributes = ""
        self.set_data_ref = "input_tsv"
        self.multiple = False
        self.optional = False
        self._param = None

    def build_ready_hda(self):
        hist = model.History()
        self.app.model.context.add( hist )
        ready_hda = hist.add_dataset( model.HistoryDatasetAssociation( extension='interval', create_dataset=True, sa_session=self.app.model.context ) )
        ready_hda.set_dataset_state( 'ok' )
        return ready_hda

    @property
    def param( self ):
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
            self.param_xml = XML( template_xml % ( self.type, data_ref_text, multi_text, optional_text, self.other_attributes ) )
            self._param = basic.ColumnListParameter( self.mock_tool, self.param_xml )
            self._param.ref_input = bunch.Bunch(formats=[model.datatypes_registry.get_datatype_by_extension("tabular")])

        return self._param
