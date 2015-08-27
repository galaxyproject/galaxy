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
            self.assertEqual( data, [] )

    def test_chroms( self ):
        with open( TEST_FILE, 'rb' ) as source:
            provider = self.provider_class(
                source,
                chromosomes=True
            )
            data = list( provider )[0]
            try:
                data['chromosomes'].sort()
            except:
                pass
            self.assertEqual( data, {'chromosomes': ['18', '19'], 'includes_trans': True} )

    def test_header( self ):
        with open( TEST_FILE, 'rb' ) as source:
            provider = self.provider_class(
                source,
                header=True,
                chrom1='18',
                chrom2='19'
            )
            data = list( provider )
            self.assertEqual( data, [{'shape_bins': 75, 'start1': -3114508, 'hres': 5000000, 'start2': 2217738, 'stop1': 96885492, 'minscore': -14.89890193939209, 'index_bins': 75, 'm': 3, 'lres': 20000000, 'n': 5, 'data_bins': 291, 'total_bytes': 1614, 'offset': 1540, 'stop2': 62217738, 'maxscore': -12.311820030212402, 'total_bins': 441}] )

    def test_small_cis_window( self ):
        with open( TEST_FILE, 'rb' ) as source:
            provider = self.provider_class(
                source,
                chrom1='18',
                chrom2='18',
                start1=20000000,
                start2=60000000,
                stop1=40000000,
                stop2=80000000,
                minresolution=20000000,
                maxresolution=10000000
            )
            data = list( provider )
            self.assertEqual( data, [[20000000, 6885492, 60000000, 6885492, -10.190299034118652, 1], [20000000, 6885492, 66885492, 10000000, -10.598214149475098, 1], [26885492, 10000000, 60000000, 6885492, -9.802485466003418, 1], [26885492, 10000000, 66885492, 10000000, -10.095721244812012, 1], [20000000, 6885492, 76885492, 3114508, -11.09201717376709, 1], [26885492, 10000000, 76885492, 3114508, -10.56174373626709, 1], [36885492, 3114508, 60000000, 6885492, -9.686873435974121, 1], [36885492, 3114508, 66885492, 10000000, -9.738481521606445, 1], [36885492, 3114508, 76885492, 3114508, -10.048870086669922, 1]] )

    def test_small_trans_window( self ):
        with open( TEST_FILE, 'rb' ) as source:
            provider = self.provider_class(
                source,
                chrom1='18',
                chrom2='19',
                start1=20000000,
                start2=60000000,
                stop1=40000000,
                stop2=80000000,
                minresolution=20000000,
                maxresolution=10000000
            )
            data = list( provider )
            self.assertEqual( data, [[20000000, 6885492, 60000000, 2217738, -14.142205238342285, 1], [26885492, 10000000, 60000000, 2217738, -13.74052619934082, 1], [36885492, 3114508, 60000000, 2217738, -14.021368026733398, 1]] )

if __name__ == '__main__':
    unittest.main()
