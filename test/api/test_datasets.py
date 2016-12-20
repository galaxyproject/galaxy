from __future__ import print_function

import textwrap

from base import api
from base.populators import TestsDatasets


class DatasetsApiTestCase( api.ApiTestCase, TestsDatasets ):

    def setUp( self ):
        super( DatasetsApiTestCase, self ).setUp()
        self.history_id = self._new_history()

    def test_index( self ):
        index_response = self._get( "datasets" )
        self._assert_status_code_is( index_response, 501 )

    def test_show( self ):
        hda1 = self._new_dataset( self.history_id )
        show_response = self._get( "datasets/%s" % ( hda1[ "id" ] ) )
        self._assert_status_code_is( show_response, 200 )
        self.__assert_matches_hda( hda1, show_response.json() )

    def __assert_matches_hda( self, input_hda, query_hda ):
        self._assert_has_keys( query_hda, "id", "name" )
        assert input_hda[ "name" ] == query_hda[ "name" ]
        assert input_hda[ "id" ] == query_hda[ "id" ]

    def test_display( self ):
        contents = textwrap.dedent( """\
        1   2   3   4
        A   B   C   D
        10  20  30  40
        """ )
        hda1 = self._new_dataset(self.history_id, content=contents)
        self._wait_for_history(self.history_id)
        display_response = self._get( "histories/%s/contents/%s/display" % ( self.history_id, hda1[ "id" ] ), {
            'raw': 'True'
        })
        self._assert_status_code_is( display_response, 200 )
        assert display_response.text == contents
