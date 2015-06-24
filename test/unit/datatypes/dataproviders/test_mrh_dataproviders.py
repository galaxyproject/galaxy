"""
Unit tests for Multiresolution Heatmap (Mrh) DataProviders.
.. seealso:: galaxy.datatypes.dataproviders.base
"""

import os.path
import imp
import unittest

import logging
log = logging.getLogger( __name__ )

test_utils = imp.load_source( 'test_utils',
    os.path.join( os.path.dirname( __file__), '../../unittest_utils/utility.py' ) )

from test_base_dataproviders import BaseTestCase
from galaxy.datatypes.dataproviders import mrh

TEST_FILE = os.path.join( test_utils.get_galaxy_root(), 'test-data/1.mrh' )


class Test_BaseDataProvider( BaseTestCase ):
    provider_class = mrh.MrhSquareDataProvider

    def test_no_params( self ):
        with open( TEST_FILE, 'rb' ) as source:
            provider = self.provider_class( source )
            data = list( provider )
            # print 'data: %s' % str( data )
            self.assertEqual( data, [] )

    def test_small_cis_window( self ):
        with open( TEST_FILE, 'rb' ) as source:
            provider = self.provider_class( source,
                chrom1='18',
                chrom2='18',
                start1=20000000,
                start2=20000000,
                stop1=22560000,
                stop2=22560000,
                min_resolution=1280000,
                max_resolution=320000,
            )
            data = list( provider )
            # print 'len data: %s' % str( len( data ) )
            self.assertEqual( len( data ), 64 )
            # print data[1]['value']
            self.assertEqual( "-2.98051", "%0.5f" % data[1]['value'])

    def test_small_trans_window( self ):
        with open( TEST_FILE, 'rb' ) as source:
            provider = self.provider_class( source,
                chrom1='18',
                chrom2='19',
                start1=20000000,
                start2=20000000,
                stop1=22560000,
                stop2=22560000,
                min_resolution=1280000,
                max_resolution=320000,
            )
            data = list( provider )
            # print 'len data: %s' % str( len( data ) )
            self.assertEqual( len( data ), 7 )
            # print data[1]['value']
            self.assertEqual( "-13.46063", "%0.5f" % data[1]['value'])

if __name__ == '__main__':
    unittest.main()
