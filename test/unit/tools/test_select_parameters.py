from galaxy import model
from galaxy.tools.parameters import basic
from galaxy.util import bunch

from .test_parameter_parsing import BaseParameterTestCase


class SelectToolParameterTestCase( BaseParameterTestCase ):

    def test_validated_values( self ):
        self.options_xml = '''<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>'''
        try:
            self.param.from_json("42", self.trans, { "input_bam": model.HistoryDatasetAssociation() })
        except ValueError as err:
            assert str(err) == "An invalid option was selected for my_name, '42', please verify."
            return
        assert False

    def test_validated_values_missing_dependency( self ):
        self.options_xml = '''<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>'''
        try:
            self.param.from_json("42", self.trans)
        except ValueError as err:
            assert str(err) == "Parameter my_name requires a value, but has no legal values defined."
            return
        assert False

    def test_unvalidated_values( self ):
        self.options_xml = '''<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>'''
        self.trans.workflow_building_mode = True
        assert self.param.from_json("42", self.trans) == "42"

    def test_validated_datasets( self ):
        self.options_xml = '''<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>'''
        try:
            self.param.from_json( model.HistoryDatasetAssociation(), self.trans, { "input_bam": None } )
        except ValueError as err:
            assert str(err) == "Parameter my_name requires a value, but has no legal values defined."
            return
        assert False

    def test_unvalidated_datasets( self ):
        self.options_xml = '''<options><filter type="data_meta" ref="input_bam" key="dbkey"/></options>'''
        self.trans.workflow_building_mode = True
        assert isinstance( self.param.from_json( model.HistoryDatasetAssociation(), self.trans, { "input_bam": basic.RuntimeValue() } ), model.HistoryDatasetAssociation )

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
        super(SelectToolParameterTestCase, self).setUp()
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
            param_str = template_xml % ( self.type, data_ref_text, multi_text, optional_text, options_text )
            self._param = self._parameter_for( xml=param_str )

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
