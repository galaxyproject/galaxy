"""
Test lib/galaxy/visualization/plugins/config_parser
"""
from __future__ import print_function

import os
import imp
import unittest

test_utils = imp.load_source( 'test_utils',
    os.path.join( os.path.dirname( __file__), '..', '..', 'unittest_utils', 'utility.py' ) )
import galaxy_mock

from galaxy.util import parse_xml_string
from galaxy.managers import hdas
from galaxy.datatypes import interval

from galaxy.visualization.plugins import config_parser


# -----------------------------------------------------------------------------
class config_parser_TestCase( test_utils.unittest.TestCase ):

    def log( self, *msgs ):
        print( *msgs )


# -----------------------------------------------------------------------------
class DataSourceParser_TestCase( config_parser_TestCase ):

    def test_attribute_test( self ):
        """Data sources can define applicability tests based on a model attribute"""
        app = galaxy_mock.MockApp()
        source_xml = test_utils.clean_multiline_string( """
            <data_source>
                <model_class>HistoryDatasetAssociation</model_class>
                <test test_attr="name">Something something</test>
                <to_param param_attr="id">hda_id</to_param>
            </data_source>
        """ )
        parsed_source_xml = parse_xml_string( source_xml )
        parser = config_parser.DataSourceParser( app )
        data_source = parser.parse( parsed_source_xml )

        hda = hdas.HDAManager( app ).create( name='Something something' )
        self.assertTrue( data_source.is_applicable( hda ) )
        params = data_source.params( galaxy_mock.MockTrans( app=app ), hda )
        self.assertTrue( isinstance( params.get( 'hda_id', None ), str ) )

        hda = hdas.HDAManager( app ).create( name='Something else' )
        self.assertFalse( data_source.is_applicable( hda ) )

    def test_nested_attribute_test( self ):
        """Data sources can define applicability tests based on nested model attributes"""
        app = galaxy_mock.MockApp()
        source_xml = test_utils.clean_multiline_string( """
            <data_source>
                <model_class>HistoryDatasetAssociation</model_class>
                <test test_attr="metadata.dbkey">mm9</test>
                <to_param param_attr="id">mouse_data_id</to_param>
            </data_source>
        """ )
        parsed_source_xml = parse_xml_string( source_xml )
        parser = config_parser.DataSourceParser( app )
        data_source = parser.parse( parsed_source_xml )

        hda = hdas.HDAManager( app ).create( dbkey='mm9' )
        self.assertTrue( data_source.is_applicable( hda ) )
        params = data_source.params( galaxy_mock.MockTrans( app=app ), hda )
        self.assertTrue( isinstance( params.get( 'mouse_data_id', None ), str ) )

        hda = hdas.HDAManager( app ).create( dbkey='mm10' )
        self.assertFalse( data_source.is_applicable( hda ) )

    def test_has_dataprovider( self ):
        """
        Data sources can define applicability tests based on
        whether they or their attributes have a named dataprovider
        """
        app = galaxy_mock.MockApp()
        source_xml = test_utils.clean_multiline_string( """
            <data_source>
                <model_class>HistoryDatasetAssociation</model_class>
                <test test_attr="datatype" type="has_dataprovider">genomic-region</test>
            </data_source>
        """ )
        parsed_source_xml = parse_xml_string( source_xml )
        parser = config_parser.DataSourceParser( app )
        data_source = parser.parse( parsed_source_xml )

        hda = hdas.HDAManager( app ).create( extension='gff' )
        self.assertTrue( data_source.is_applicable( hda ) )

        hda = hdas.HDAManager( app ).create( extension='tabular' )
        self.assertFalse( data_source.is_applicable( hda ) )

    def test_has_attribute( self ):
        """Data sources can define applicability tests based on whether they have attributes"""
        app = galaxy_mock.MockApp()
        # note: testing metadata with hasattr always returns true (bunch?)
        # <test test_attr="metadata" type="has_attribute">chromCol</test>
        source_xml = test_utils.clean_multiline_string( """
            <data_source>
                <model_class>HistoryDatasetAssociation</model_class>
                <test type="has_attribute">annotation</test>
            </data_source>
        """ )
        parsed_source_xml = parse_xml_string( source_xml )
        parser = config_parser.DataSourceParser( app )
        data_source = parser.parse( parsed_source_xml )

        hda = hdas.HDAManager( app ).create()
        hda.annotation = 'We probably shouldn\'t have called these annotations'
        self.assertTrue( data_source.is_applicable( hda ) )

        hda = hdas.HDAManager( app ).create()
        self.assertFalse( data_source.is_applicable( hda ) )

    def test_not_eq( self ):
        """Data sources can define applicability tests based on attributes not equaling a value"""
        app = galaxy_mock.MockApp()
        # note: testing metadata with hasattr always returns true (bunch?)
        # <test test_attr="metadata" type="has_attribute">chromCol</test>
        source_xml = test_utils.clean_multiline_string( """
            <data_source>
                <model_class>HistoryDatasetAssociation</model_class>
                <test test_attr="datatype.track_type" type="not_eq">None</test>
            </data_source>
        """ )
        parsed_source_xml = parse_xml_string( source_xml )
        parser = config_parser.DataSourceParser( app )
        data_source = parser.parse( parsed_source_xml )

        hda = hdas.HDAManager( app ).create( extension='bed' )
        self.assertTrue( data_source.is_applicable( hda ) )

        hda = hdas.HDAManager( app ).create( extension='txt' )
        self.assertFalse( data_source.is_applicable( hda ) )

    def test_datatype_isinstance( self ):
        """Data sources can define applicability tests based on dataset datatype."""
        datatypes = {
            'interval.Gff' : interval.Gff
        }
        app = galaxy_mock.MockApp( datatypes=datatypes )

        source_xml = test_utils.clean_multiline_string( """
            <data_source>
                <model_class>HistoryDatasetAssociation</model_class>
                <test test_attr="datatype" type="isinstance" result_type="datatype">interval.Gff</test>
                <to_param param_attr="id">gff_id</to_param>
            </data_source>
        """ )
        parsed_source_xml = parse_xml_string( source_xml )
        parser = config_parser.DataSourceParser( app )
        data_source = parser.parse( parsed_source_xml )
        self.assertTrue( isinstance( data_source, config_parser.DataSource ) )

        self.log( 'Direct matches of classes should be applicable' )
        gff = hdas.HDAManager( app ).create( extension='gff' )
        self.assertTrue( data_source.is_applicable( gff ) )
        params = data_source.params( galaxy_mock.MockTrans( app=app ), gff )
        self.assertTrue( isinstance( params, dict ) )
        self.assertTrue( isinstance( params.get( 'gff_id', None ), str ) )

        self.log( 'Subclasses should be applicable' )
        gff3 = hdas.HDAManager( app ).create( extension='gff3' )
        self.assertTrue( data_source.is_applicable( gff3 ) )

        self.log( 'Non-subclasses and superclasses should not be applicable' )
        pileup = hdas.HDAManager( app ).create( extension='pileup' )
        self.assertFalse( data_source.is_applicable( pileup ) )
        tabular = hdas.HDAManager( app ).create( extension='tabular' )
        self.assertFalse( data_source.is_applicable( tabular ) )

    def test_OR( self ):
        """Applicability tests are, by default, OR'd"""
        app = galaxy_mock.MockApp()
        # TODO: use this opportunity to test other attributes (these have been done)
        source_xml = test_utils.clean_multiline_string( """
            <data_source>
                <model_class>HistoryDatasetAssociation</model_class>
                <test test_attr="name" type="contains">Nym_</test>
                <test test_attr="metadata.dbkey">mm9</test>
            </data_source>
        """ )
        parsed_source_xml = parse_xml_string( source_xml )
        parser = config_parser.DataSourceParser( app )
        data_source = parser.parse( parsed_source_xml )

        hda = hdas.HDAManager( app ).create( name='Nym_003987' )
        self.assertTrue( data_source.is_applicable( hda ) )
        hda = hdas.HDAManager( app ).create( dbkey='mm9' )
        self.assertTrue( data_source.is_applicable( hda ) )
        hda = hdas.HDAManager( app ).create( name='Nym_003988', dbkey='mm9' )
        self.assertTrue( data_source.is_applicable( hda ) )

        hda = hdas.HDAManager( app ).create( name='Ben', dbkey='rn4' )
        self.assertFalse( data_source.is_applicable( hda ) )

    def test_AND( self ):
        """Applicability tests can be AND'd using the 'and' test type"""
        app = galaxy_mock.MockApp()
        source_xml = test_utils.clean_multiline_string( """
            <data_source>
                <model_class>HistoryDatasetAssociation</model_class>
                <test type="and">
                    <test test_attr="name" type="contains">Nym_</test>
                    <test test_attr="metadata.dbkey">mm9</test>
                </test>
                <to_param param_attr="id">id</to_param>
            </data_source>
        """ )
        parsed_source_xml = parse_xml_string( source_xml )
        parser = config_parser.DataSourceParser( app )
        data_source = parser.parse( parsed_source_xml )

        hda = hdas.HDAManager( app ).create( name='Nym_003988', dbkey='mm9' )
        self.assertTrue( data_source.is_applicable( hda ) )

        hda = hdas.HDAManager( app ).create( name='Nym_003987' )
        self.assertFalse( data_source.is_applicable( hda ) )
        hda = hdas.HDAManager( app ).create( dbkey='mm9' )
        self.assertFalse( data_source.is_applicable( hda ) )
        hda = hdas.HDAManager( app ).create( name='Ben', dbkey='rn4' )
        self.assertFalse( data_source.is_applicable( hda ) )

        params = data_source.params( galaxy_mock.MockTrans( app=app ), hda )
        self.assertTrue( isinstance( params, dict ) )
        self.assertTrue( isinstance( params.get( 'id', None ), str ) )


# -----------------------------------------------------------------------------
class DataSourceGroupParser_TestCase( config_parser_TestCase ):

    def test_datasourcegroup( self ):
        """
        Data sources can be multiple models
        and tests can be made against groups of (potential) sources
        """
        datatypes = {
            'interval.Gff' : interval.Gff,
            'interval.Bed' : interval.Bed,
        }
        app = galaxy_mock.MockApp( datatypes=datatypes )
        source_xml = test_utils.clean_multiline_string( """
            <data_source_group>
                <data_source>
                    <model_class>HistoryDatasetAssociation</model_class>
                    <test test_attr="datatype" type="isinstance" result_type="datatype">interval.Gff</test>
                    <to_param param_attr="id">gff_id</to_param>
                </data_source>
                <data_source>
                    <model_class>HistoryDatasetAssociation</model_class>
                    <test type="and">
                        <test test_attr="datatype" type="isinstance" result_type="datatype">interval.Bed</test>
                        <test test_attr="name" type="contains">regions</test>
                    </test>
                    <to_param param_attr="id">regions_id</to_param>
                </data_source>
            </data_source_group>
        """ )
        parsed_source_xml = parse_xml_string( source_xml )
        parser = config_parser.VisualizationsConfigParser( app )
        data_source = parser.parse_data_source_group( parsed_source_xml )

        gff = hdas.HDAManager( app ).create( extension='gff' )
        bed = hdas.HDAManager( app ).create( extension='bed', name='blah.regions.blah.bed' )
        not_good0 = hdas.HDAManager( app ).create( extension='tabular' )
        not_good1 = hdas.HDAManager( app ).create( extension='bed', name='nope' )

        self.log( 'Groups should be discernable even out of order or amongst non-applicable items' )
        self.assertTrue( data_source.is_applicable([ gff, bed ]) )
        self.assertTrue( data_source.is_applicable([ bed, gff ]) )
        self.assertTrue( data_source.is_applicable([ bed, gff, not_good0 ]) )

        self.log( 'Bad lists or lists containing not enough applicable items will not be applicable' )
        self.assertFalse( data_source.is_applicable([]) )
        self.assertFalse( data_source.is_applicable([ gff ]) )
        self.assertFalse( data_source.is_applicable([ bed ]) )
        self.assertFalse( data_source.is_applicable( gff ) )
        self.assertFalse( data_source.is_applicable([ gff, not_good1 ]) )
        self.assertFalse( data_source.is_applicable([ bed, not_good0 ]) )

        self.log( 'Params should be parsable from properly formed groups' )
        params = data_source.params( galaxy_mock.MockTrans( app=app ), [ gff, bed ] )
        self.assertTrue( isinstance( params, dict ) )
        gff_id = params.get( 'gff_id', None )
        regions = params.get( 'regions_id', None )
        self.assertTrue( isinstance( gff_id, str ) )
        self.assertTrue( isinstance( regions, str ) )
        self.assertTrue( gff_id != regions )


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
