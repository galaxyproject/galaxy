from unittest import TestCase

from galaxy import model
from galaxy.util import bunch
from galaxy.tools.parameters import basic

from elementtree.ElementTree import XML

import tools_support


class DataToolParameterTestCase( TestCase, tools_support.UsesApp ):

    def test_to_python_none_values( self ):
        assert None is self.param.to_python( None, self.app )
        assert 'None' == self.param.to_python( 'None', self.app )
        assert '' == self.param.to_python( '', self.app )

    def test_to_python_hda( self ):
        hda = self._new_hda()
        as_python = self.param.to_python( hda.id, self.app )
        assert hda == as_python

    def test_to_python_multi_hdas( self ):
        hda1 = self._new_hda()
        hda2 = self._new_hda()
        as_python = self.param.to_python( "%s,%s" % ( hda1.id, hda2.id ), self.app )
        assert as_python == [ hda1, hda2 ]

    def test_to_python_multi_none( self ):
        self.multiple = True
        hda = self._new_hda()
        # Selection is Optional. may be selected with other stuff,
        # not sure the UI should really allow this but easy enough
        # to just filter it out.
        assert [hda] == self.param.to_python( '%s,None' % hda.id, self.app )

    def test_field_filter_on_types( self ):
        hda1 = MockHistoryDatasetAssociation( name="hda1", id=1 )
        hda2 = MockHistoryDatasetAssociation( name="hda2", id=2 )
        self.stub_active_datasets( hda1, hda2 )
        field = self._simple_field()
        assert len( field.options ) == 2
        assert field.options[ 0 ][ 0 ] == "1: hda1"
        assert field.options[ 1 ][ 0 ] == "2: hda2"

        assert field.options[ 1 ][ 2 ]  # Last one selected
        assert not field.options[ 0 ][ 2 ]  # Others not selected

        hda2.datatype_matches = False
        field = self._simple_field()
        assert len( field.options ) == 1
        assert field.options[ 0 ][ 2 ] is True  # Last one selected

    def test_field_display_hidden_hdas_only_if_selected( self ):
        hda1 = MockHistoryDatasetAssociation( name="hda1", id=1 )
        hda2 = MockHistoryDatasetAssociation( name="hda2", id=2 )
        self.stub_active_datasets( hda1, hda2 )
        hda1.visible = False
        hda2.visible = False
        field = self._simple_field( value=hda2 )
        self.assertEquals( len( field.options ), 1 )  # hda1 not an option, not visible or selected
        assert field.options[ 0 ][ 0 ] == "2: (hidden) hda2"

    def test_field_implicit_conversion_new( self ):
        hda1 = MockHistoryDatasetAssociation( name="hda1", id=1 )
        hda1.datatype_matches = False
        hda1.conversion_destination = ( "tabular", None )
        self.stub_active_datasets( hda1 )
        field = self._simple_field()
        assert len( field.options ) == 1
        assert field.options[ 0 ][ 0 ] == "1: (as tabular) hda1"
        assert field.options[ 0 ][ 1 ] == 1

    def test_field_implicit_conversion_existing( self ):
        hda1 = MockHistoryDatasetAssociation( name="hda1", id=1 )
        hda1.datatype_matches = False
        hda1.conversion_destination = ( "tabular", MockHistoryDatasetAssociation( name="hda1converted", id=2 ) )
        self.stub_active_datasets( hda1 )
        field = self._simple_field()
        assert len( field.options ) == 1
        assert field.options[ 0 ][ 0 ] == "1: (as tabular) hda1"
        # This is difference with previous test, value is existing
        # hda id not new one.
        assert field.options[ 0 ][ 1 ] == 2

    def test_field_multiple( self ):
        self.multiple = True
        field = self._simple_field()
        assert field.multiple

    def test_field_empty_selection( self ):
        field = self._simple_field()
        assert len( field.options ) == 0

    def test_field_empty_selection_optional( self ):
        self.optional = True
        field = self._simple_field()
        assert len( field.options ) == 1
        option = field.options[ 0 ]
        assert option[ 0 ] == "Selection is Optional"
        assert option[ 1 ] == "None"
        assert option[ 2 ] is True

    def test_get_initial_value_prevents_repeats( self ):
        hda1 = MockHistoryDatasetAssociation( name="hda1", id=1 )
        hda2 = MockHistoryDatasetAssociation( name="hda2", id=2 )
        self.stub_active_datasets( hda1, hda2 )
        already_used = []
        assert hda2 == self.param.get_initial_value_from_history_prevent_repeats( self.trans, {}, already_used )
        assert hda1 == self.param.get_initial_value_from_history_prevent_repeats( self.trans, {}, already_used )

    def test_get_initial_value_is_empty_string_if_no_match( self ):
        hda1 = MockHistoryDatasetAssociation( name="hda1", id=1 )
        hda1.visible = False
        hda2 = MockHistoryDatasetAssociation( name="hda2", id=2 )
        hda2.visible = False
        self.stub_active_datasets( hda1, hda2 )
        assert '' == self.param.get_initial_value( self.trans, {} )

    def test_get_initial_none_when_optional( self ):
        self.optional = True
        hda1 = MockHistoryDatasetAssociation( name="hda1", id=1 )
        hda2 = MockHistoryDatasetAssociation( name="hda2", id=2 )
        self.stub_active_datasets( hda1, hda2 )
        assert self.param.get_initial_value( self.trans, {} ) is None

    def test_get_initial_with_previously_converted_data( self ):
        hda1 = MockHistoryDatasetAssociation( name="hda1", id=1 )
        hda1.datatype_matches = False
        converted = MockHistoryDatasetAssociation( name="hda1converted", id=2 )
        hda1.conversion_destination = ( "tabular", converted )
        self.stub_active_datasets( hda1 )
        assert converted == self.param.get_initial_value( self.trans, {} )

    def test_get_initial_with_to_be_converted_data( self ):
        hda1 = MockHistoryDatasetAssociation( name="hda1", id=1 )
        hda1.datatype_matches = False
        hda1.conversion_destination = ( "tabular", None )
        self.stub_active_datasets( hda1 )
        assert hda1 == self.param.get_initial_value( self.trans, {} )

    def _new_hda( self ):
        hda = model.HistoryDatasetAssociation()
        hda.visible = True
        hda.dataset = model.Dataset()
        self.app.model.context.add( hda )
        self.app.model.context.flush( )
        return hda

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
        self.multiple = False
        self.optional = False
        self._param = None

    def stub_active_datasets( self, *hdas ):
        self.test_history._active_datasets_children_and_roles = hdas

    def _simple_field( self, **kwds ):
        field = self.param.get_html_field( trans=self.trans, **kwds )
        if hasattr( field, "primary_field" ):
            field = field.primary_field
        return field

    @property
    def param( self ):
        if not self._param:
            multi_text = ""
            if self.multiple:
                multi_text = 'multiple="True"'
            optional_text = ""
            if self.optional:
                optional_text = 'optional="True"'
            template_xml = '''<param name="data2" type="data" ext="txt" %s %s></param>'''
            self.param_xml = XML( template_xml % ( multi_text, optional_text ) )
            self._param = basic.DataToolParameter( self.mock_tool, self.param_xml )

        return self._param


class MockHistoryDatasetAssociation( object ):
    """ Fake HistoryDatasetAssociation stubbed out for testing matching and
    stuff like that.
    """

    def __init__( self, test_dataset=None, name="Test Dataset", id=1 ):
        if not test_dataset:
            test_dataset = model.Dataset()
        self.states = model.HistoryDatasetAssociation.states
        self.deleted = False
        self.dataset = test_dataset
        self.visible = True
        self.datatype_matches = True
        self.conversion_destination = ( None, None )
        self.datatype = bunch.Bunch(
            matches_any=lambda formats: self.datatype_matches,
        )
        self.dbkey = "hg19"
        self.implicitly_converted_parent_datasets = False

        self.name = name
        self.hid = id
        self.id = id
        self.children = []

    @property
    def state( self ):
        return self.dataset.state

    def get_dbkey( self ):
        return self.dbkey

    def find_conversion_destination( self, formats ):
        return self.conversion_destination
