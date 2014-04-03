from unittest import TestCase
from galaxy.util import bunch
from galaxy import model
from galaxy.tools.parameters import basic
from elementtree.ElementTree import XML

import tools_support


class SelectToolParameterTestCase( TestCase, tools_support.UsesApp ):

    def test_dep_dummy_datasets_need_late_validation( self ):
        self.options_xml = '''<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>'''
        assert self.param.need_late_validation( self.trans, { "input_bam": basic.DummyDataset() } )

    def test_dep_runtime_values_need_late_validation( self ):
        self.options_xml = '''<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>'''
        assert self.param.need_late_validation( self.trans, { "input_bam": basic.RuntimeValue() } )

    def test_dep_unvalidated_values_need_late_validation( self ):
        self.options_xml = '''<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>'''
        assert self.param.need_late_validation( self.trans, { "input_bam": basic.UnvalidatedValue( "42" ) } )

    def test_dep_real_datasets_no_late_validation( self ):
        self.options_xml = '''<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>'''
        assert not self.param.need_late_validation( self.trans, { "input_bam": model.HistoryDatasetAssociation() } )

    def test_nested_context_validation_needed( self ):
        self.options_xml = '''<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>'''
        # Data ref currently must be same level, if not at top level.
        assert self.param.need_late_validation( self.trans, { "reference_source": { "my_name": "42", "input_bam": basic.RuntimeValue() } } )

    def test_nested_context_validation_not_needed( self ):
        self.options_xml = '''<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>'''
        # Data ref currently must be same level, if not at top level.
        assert not self.param.need_late_validation( self.trans, { "reference_source": { "my_name": "42", "input_bam": model.HistoryDatasetAssociation() } } )

    def test_filter_param_value( self ):
        self.options_xml = '''<options from_data_table="test_table"><filter type="param_value" ref="input_bam" column="0" /></options>'''
        assert ("testname1", "testpath1", False) in self.param.get_options( self.trans, { "input_bam": "testname1" } )
        assert ("testname2", "testpath2", False) in self.param.get_options( self.trans, { "input_bam": "testname2" } )
        assert len( self.param.get_options( self.trans, { "input_bam": "testname3" } ) ) == 0

    def test_filter_param_value2( self ):
        # Same test as above, but filtering on a different column.
        self.options_xml = '''<options from_data_table="test_table"><filter type="param_value" ref="input_bam" column="1" /></options>'''
        assert ("testname1", "testpath1", False) in self.param.get_options( self.trans, { "input_bam": "testpath1" } )
        assert ("testname2", "testpath2", False) in self.param.get_options( self.trans, { "input_bam": "testpath2" } )
        assert len( self.param.get_options( self.trans, { "input_bam": "testpath3" } ) ) == 0

    # TODO: Good deal of overlap here with DataToolParameterTestCase,
    # refactor.
    def setUp( self ):
        self.setup_app( mock_model=False )
        self.mock_tool = bunch.Bunch(
            app=self.app,
            tool_type="default",
        )
        self.test_history = model.History()
        self.app.model.context.add( self.test_history )
        self.app.model.context.flush()
        self.app.tool_data_tables[ "test_table" ] = MockToolDataTable()
        self.trans = bunch.Bunch(
            app=self.app,
            get_history=lambda: self.test_history,
            get_current_user_roles=lambda: [],
            workflow_building_mode=False,
            webapp=bunch.Bunch( name="galaxy" ),
        )
        self.type = "select"
        self.set_data_ref = False
        self.multiple = False
        self.optional = False
        self.options_xml = ""
        self._param = None

    @property
    def param( self ):
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
            template_xml = '''<param name="my_name" type="%s" %s %s %s>%s</param>'''
            self.param_xml = XML( template_xml % ( self.type, data_ref_text, multi_text, optional_text, options_text ) )
            self._param = basic.SelectToolParameter( self.mock_tool, self.param_xml )

        return self._param


class MockToolDataTable( object ):

    def __init__( self ):
        self.columns = dict(
            name=0,
            value=1,
        )
        self.missing_index_file = None

    def get_fields( self ):
        return [ [ "testname1", "testpath1" ], [ "testname2", "testpath2" ] ]
