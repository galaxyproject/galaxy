"""
Unit tests for base DataProviders.
.. seealso:: galaxy.datatypes.dataproviders.base
"""
import logging
import os.path
import sys
import unittest

from six import StringIO

from galaxy.datatypes.dataproviders import base, exceptions

unit_root = os.path.abspath( os.path.join( os.path.dirname( __file__ ), os.pardir, os.pardir ) )
sys.path.insert( 1, unit_root )
from unittest_utils import tempfilecache, utility

log = logging.getLogger( __name__ )

# TODO: fix imports there after dist and retry
# TODO: fix off by ones in FilteredDataProvider counters
# currently because of dataproviders.dataset importing galaxy.model this doesn't work


class BaseTestCase( unittest.TestCase ):
    default_file_contents = """
            One
            Two
            Three
        """

    @classmethod
    def setUpClass( cls ):
        log.debug( 'CLASS %s %s', ( '_' * 40 ), cls.__name__ )

    @classmethod
    def tearDownClass( cls ):
        log.debug( 'CLASS %s %s\n\n', ( '_' * 40 ), cls.__name__ )

    def __init__( self, *args ):
        unittest.TestCase.__init__( self, *args )
        self.tmpfiles = tempfilecache.TempFileCache( log )

    def setUp( self ):
        log.debug( 'BEGIN %s %s', ( '.' * 40 ), self._testMethodName )
        if self._testMethodDoc:
            log.debug( ' """%s"""', self._testMethodDoc.strip() )

    def tearDown( self ):
        self.tmpfiles.clear()
        log.debug( 'END\n' )

    def format_tmpfile_contents( self, contents=None ):
        contents = contents or self.default_file_contents
        contents = utility.clean_multiline_string( contents )
        log.debug( 'file contents:\n%s', contents )
        return contents

    def parses_default_content_as( self ):
        return [ 'One\n', 'Two\n', 'Three\n' ]


class Test_BaseDataProvider( BaseTestCase ):
    provider_class = base.DataProvider

    def contents_provider_and_data( self,
            filename=None, contents=None, source=None, *provider_args, **provider_kwargs ):
        # to remove boiler plate
        # returns file content string, provider used, and data list
        if not filename:
            contents = self.format_tmpfile_contents( contents )
            filename = self.tmpfiles.create_tmpfile( contents )
        # TODO: if filename, contents == None
        if not source:
            source = open( filename )
        provider = self.provider_class( source, *provider_args, **provider_kwargs )
        log.debug( 'provider: %s', provider )
        data = list( provider )
        log.debug( 'data: %s', str( data ) )
        return ( contents, provider, data )

    def test_iterators( self ):
        source = ( str( x ) for x in range( 1, 10 ) )
        provider = self.provider_class( source )
        data = list( provider )
        log.debug( 'data: %s', str( data ) )
        self.assertEqual( data, [ str( x ) for x in range( 1, 10 ) ] )

        source = ( str( x ) for x in range( 1, 10 ) )
        provider = self.provider_class( source )
        data = list( provider )
        log.debug( 'data: %s', str( data ) )
        self.assertEqual( data, [ str( x ) for x in range( 1, 10 ) ] )

        source = ( str( x ) for x in range( 1, 10 ) )
        provider = self.provider_class( source )
        data = list( provider )
        log.debug( 'data: %s', str( data ) )
        self.assertEqual( data, [ str( x ) for x in range( 1, 10 ) ] )

    def test_validate_source( self ):
        """validate_source should throw an error if the source doesn't have attr '__iter__'
        """
        def non_iterator_dprov( source ):
            return self.provider_class( source )
        self.assertRaises( exceptions.InvalidDataProviderSource,
            non_iterator_dprov, 'one two three' )
        self.assertRaises( exceptions.InvalidDataProviderSource,
            non_iterator_dprov, 40 )

    def test_writemethods( self ):
        """should throw an error if any write methods are called
        """
        source = ( str( x ) for x in range( 1, 10 ) )
        provider = self.provider_class( source )

        # should throw error
        def call_method( provider, method_name, *args ):
            method = getattr( provider, method_name )
            return method( *args )

        self.assertRaises( NotImplementedError, call_method, provider, 'truncate', 20 )
        self.assertRaises( NotImplementedError, call_method, provider, 'write', 'bler' )
        self.assertRaises( NotImplementedError, call_method, provider, 'writelines', [ 'one', 'two' ] )

    def test_readlines( self ):
        """readlines should return all the data in list form
        """
        source = ( str( x ) for x in range( 1, 10 ) )
        provider = self.provider_class( source )
        data = provider.readlines()
        log.debug( 'data: %s', str( data ) )
        self.assertEqual( data, [ str( x ) for x in range( 1, 10 ) ] )

    def test_stringio( self ):
        """should work with StringIO
        """
        contents = utility.clean_multiline_string( """
            One
            Two
            Three
        """ )
        source = StringIO( contents )
        provider = self.provider_class( source )
        data = list( provider )
        log.debug( 'data: %s', str( data ) )
        # provider should call close on file
        self.assertEqual( data, self.parses_default_content_as() )
        self.assertTrue( source.closed )

    def test_file( self ):
        """should work with files
        """
        ( contents, provider, data ) = self.contents_provider_and_data()
        self.assertEqual( data, self.parses_default_content_as() )
        # provider should call close on file
        self.assertTrue( hasattr(provider.source, 'read'))
        self.assertTrue( provider.source.closed )


class Test_FilteredDataProvider( Test_BaseDataProvider ):
    provider_class = base.FilteredDataProvider

    def assertCounters( self, provider, read, valid, returned ):
        self.assertEqual( provider.num_data_read, read )
        self.assertEqual( provider.num_valid_data_read, valid )
        self.assertEqual( provider.num_data_returned, returned )

    def test_counters( self ):
        """should count: lines read, lines that passed the filter, lines returned
        """
        ( contents, provider, data ) = self.contents_provider_and_data()
        self.assertCounters( provider, 3, 3, 3 )

    def test_filter_fn( self ):
        """should filter out lines using filter_fn and set counters properly
        based on filter
        """
        def filter_ts( string ):
            if string.lower().startswith( 't' ):
                return None
            return string
        ( contents, provider, data ) = self.contents_provider_and_data( filter_fn=filter_ts )
        self.assertCounters( provider, 3, 1, 1 )


class Test_LimitedOffsetDataProvider( Test_FilteredDataProvider ):
    provider_class = base.LimitedOffsetDataProvider

    def test_offset_1( self ):
        """when offset is 1, should skip first
        """
        ( contents, provider, data ) = self.contents_provider_and_data( offset=1 )
        self.assertEqual( data, self.parses_default_content_as()[1:] )
        self.assertCounters( provider, 3, 3, 2 )

    def test_offset_all( self ):
        """when offset >= num lines, should return empty list
        """
        ( contents, provider, data ) = self.contents_provider_and_data( offset=4 )
        self.assertEqual( data, [] )
        self.assertCounters( provider, 3, 3, 0 )

    def test_offset_none( self ):
        """when offset is 0, should return all
        """
        ( contents, provider, data ) = self.contents_provider_and_data( offset=0 )
        self.assertEqual( data, self.parses_default_content_as() )
        self.assertCounters( provider, 3, 3, 3 )

    def test_offset_negative( self ):
        """when offset is negative, should return all
        """
        ( contents, provider, data ) = self.contents_provider_and_data( offset=-1 )
        self.assertEqual( data, self.parses_default_content_as() )
        self.assertCounters( provider, 3, 3, 3 )

    def test_limit_1( self ):
        """when limit is one, should return first
        """
        ( contents, provider, data ) = self.contents_provider_and_data( limit=1 )
        self.assertEqual( data, self.parses_default_content_as()[:1] )
        self.assertCounters( provider, 1, 1, 1 )

    def test_limit_all( self ):
        """when limit >= num lines, should return all
        """
        ( contents, provider, data ) = self.contents_provider_and_data( limit=4 )
        self.assertEqual( data, self.parses_default_content_as() )
        self.assertCounters( provider, 3, 3, 3 )

    def test_limit_zero( self ):
        """when limit >= num lines, should return empty list
        """
        ( contents, provider, data ) = self.contents_provider_and_data( limit=0 )
        self.assertEqual( data, [] )
        self.assertCounters( provider, 0, 0, 0 )

    def test_limit_none( self ):
        """when limit is None, should return all
        """
        ( contents, provider, data ) = self.contents_provider_and_data( limit=None )
        self.assertEqual( data, self.parses_default_content_as() )
        self.assertCounters( provider, 3, 3, 3 )

    # TODO: somehow re-use tmpfile here
    def test_limit_with_offset( self ):
        def limit_offset_combo( limit, offset, data_should_be, read, valid, returned ):
            ( contents, provider, data ) = self.contents_provider_and_data( limit=limit, offset=offset )
            self.assertEqual( data, data_should_be )
            # self.assertCounters( provider, read, valid, returned )
        result_data = self.parses_default_content_as()
        test_data = [
            ( 0, 0, [], 0, 0, 0 ),
            ( 1, 0, result_data[:1], 1, 1, 1 ),
            ( 2, 0, result_data[:2], 2, 2, 2 ),
            ( 3, 0, result_data[:3], 3, 3, 3 ),
            ( 1, 1, result_data[1:2], 1, 1, 1 ),
            ( 2, 1, result_data[1:3], 2, 2, 2 ),
            ( 3, 1, result_data[1:3], 2, 2, 2 ),
            ( 1, 2, result_data[2:3], 1, 1, 1 ),
            ( 2, 2, result_data[2:3], 1, 1, 1 ),
            ( 3, 2, result_data[2:3], 1, 1, 1 ),
        ]
        for test in test_data:
            log.debug( 'limit_offset_combo: %s', ', '.join([ str( e ) for e in test ]) )
            limit_offset_combo( *test )

    def test_limit_with_offset_and_filter( self ):
        def limit_offset_combo( limit, offset, data_should_be, read, valid, returned ):
            def only_ts( string ):
                if not string.lower().startswith( 't' ):
                    return None
                return string
            ( contents, provider, data ) = self.contents_provider_and_data(
                limit=limit, offset=offset, filter_fn=only_ts )
            self.assertEqual( data, data_should_be )
            # self.assertCounters( provider, read, valid, returned )
        result_data = [ c for c in self.parses_default_content_as() if c.lower().startswith( 't' ) ]
        test_data = [
            ( 0, 0, [], 0, 0, 0 ),
            ( 1, 0, result_data[:1], 1, 1, 1 ),
            ( 2, 0, result_data[:2], 2, 2, 2 ),
            ( 3, 0, result_data[:3], 2, 2, 2 ),
            ( 1, 1, result_data[1:2], 1, 1, 1 ),
            ( 2, 1, result_data[1:3], 1, 1, 1 ),
            ( 1, 2, result_data[2:3], 0, 0, 0 ),
        ]
        for test in test_data:
            log.debug( 'limit_offset_combo: %s', ', '.join([ str( e ) for e in test ]) )
            limit_offset_combo( *test )


class Test_MultiSourceDataProvider( BaseTestCase ):
    provider_class = base.MultiSourceDataProvider

    def contents_and_tmpfile( self, contents=None ):
        # TODO: hmmmm...
        contents = contents or self.default_file_contents
        contents = utility.clean_multiline_string( contents )
        return ( contents, self.tmpfiles.create_tmpfile( contents ) )

    def test_multiple_sources( self ):
        # clean the following contents, write them to tmpfiles, open them,
        #   and pass as a list to the provider
        contents = [
            """
                One
                Two
                Three
                Four
                Five
            """,
            """
                Six
                Seven
                Eight
                Nine
                Ten
            """,
            """
                Eleven
                Twelve! (<-- http://youtu.be/JZshZp-cxKg)
            """
        ]
        contents = [ utility.clean_multiline_string( c ) for c in contents ]
        source_list = [ open( self.tmpfiles.create_tmpfile( c ) ) for c in contents ]

        provider = self.provider_class( source_list )
        log.debug( 'provider: %s', provider )
        data = list( provider )
        log.debug( 'data: %s', str( data ) )
        self.assertEqual( ''.join( data ), ''.join( contents) )

    def test_multiple_compound_sources( self ):
        # clean the following contents, write them to tmpfiles, open them,
        #   and pass as a list to the provider
        contents = [
            """
                One
                Two
                Three
                Four
                Five
            """,
            """
                Six
                Seven
                Eight
                Nine
                Ten
            """,
            """
                Eleven
                Twelve! (<-- http://youtu.be/JZshZp-cxKg)
            """
        ]
        contents = [ utility.clean_multiline_string( c ) for c in contents ]
        source_list = [ open( self.tmpfiles.create_tmpfile( c ) ) for c in contents ]

        def no_Fs( string ):
            return None if string.startswith( 'F' ) else string

        def no_youtube( string ):
            return None if ( 'youtu.be' in string ) else string

        source_list = [
            base.LimitedOffsetDataProvider( source_list[0], filter_fn=no_Fs, limit=2, offset=1 ),
            base.LimitedOffsetDataProvider( source_list[1], limit=1, offset=3 ),
            base.FilteredDataProvider( source_list[2], filter_fn=no_youtube ),
        ]
        provider = self.provider_class( source_list )
        log.debug( 'provider: %s', provider )
        data = list( provider )
        log.debug( 'data: %s', str( data ) )
        self.assertEqual( ''.join( data ), 'Two\nThree\nNine\nEleven\n' )


if __name__ == '__main__':
    unittest.main()
