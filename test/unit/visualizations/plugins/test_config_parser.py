"""
Test lib/galaxy/visualization/plugins/plugin.
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
# from galaxy.datatypes import tabular
from galaxy.datatypes import interval

# from galaxy.visualization.plugins import plugin as vis_plugin
from galaxy.visualization.plugins import config_parser
# from galaxy.visualization.plugins import utils as vis_utils


# -----------------------------------------------------------------------------
class DataSourceParser_TestCase( test_utils.unittest.TestCase ):

    def log( self, *msgs ):
        print( *msgs )

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


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
