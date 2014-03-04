from base import api
import json

from .helpers import TestsDatasets
from .helpers import LibraryPopulator
from base.interactor import (
    put_request,
    delete_request,
)


# TODO: Test anonymous access.
class HistoryContentsApiTestCase( api.ApiTestCase, TestsDatasets ):

    def setUp( self ):
        super( HistoryContentsApiTestCase, self ).setUp()
        self.history_id = self._new_history()

    def test_index_hda_summary( self ):
        hda1 = self._new_dataset( self.history_id )
        contents_response = self._get( "histories/%s/contents" % self.history_id )
        hda_summary = self.__check_for_hda( contents_response, hda1 )
        assert "display_types" not in hda_summary  # Quick summary, not full details

    def test_index_hda_all_details( self ):
        hda1 = self._new_dataset( self.history_id )
        contents_response = self._get( "histories/%s/contents?details=all" % self.history_id )
        hda_details = self.__check_for_hda( contents_response, hda1 )
        self.__assert_hda_has_full_details( hda_details )

    def test_index_hda_detail_by_id( self ):
        hda1 = self._new_dataset( self.history_id )
        contents_response = self._get( "histories/%s/contents?details=%s" % ( self.history_id, hda1[ "id" ] ) )
        hda_details = self.__check_for_hda( contents_response, hda1 )
        self.__assert_hda_has_full_details( hda_details )

    def test_show_hda( self ):
        hda1 = self._new_dataset( self.history_id )
        show_response = self.__show( hda1 )
        self._assert_status_code_is( show_response, 200 )
        self.__assert_matches_hda( hda1, show_response.json() )

    def test_hda_copy( self ):
        hda1 = self._new_dataset( self.history_id )
        create_data = dict(
            source='hda',
            content=hda1[ "id" ],
        )
        second_history_id = self._new_history()
        assert self.__count_contents( second_history_id ) == 0
        create_response = self._post( "histories/%s/contents" % second_history_id, create_data )
        self._assert_status_code_is( create_response, 200 )
        assert self.__count_contents( second_history_id ) == 1

    def test_library_copy( self ):
        ld = LibraryPopulator( self ).new_library_dataset( "lda_test_library" )
        create_data = dict(
            source='library',
            content=ld[ "id" ],
        )
        assert self.__count_contents( self.history_id ) == 0
        create_response = self._post( "histories/%s/contents" % self.history_id, create_data )
        self._assert_status_code_is( create_response, 200 )
        assert self.__count_contents( self.history_id ) == 1

    def test_update( self ):
        hda1 = self._new_dataset( self.history_id )
        self._wait_for_history( self.history_id )
        assert str( hda1[ "deleted" ] ).lower() == "false"
        update_url = self._api_url( "histories/%s/contents/%s" % ( self.history_id, hda1[ "id" ] ), use_key=True )
        # Awkward json.dumps required here because of https://trello.com/c/CQwmCeG6
        body = json.dumps( dict( deleted=True ) )
        update_response = put_request( update_url, data=body )
        self._assert_status_code_is( update_response, 200 )
        show_response = self.__show( hda1 )
        assert str( show_response.json()[ "deleted" ] ).lower() == "true"

    def test_delete( self ):
        hda1 = self._new_dataset( self.history_id )
        self._wait_for_history( self.history_id )
        assert str( self.__show( hda1 ).json()[ "deleted" ] ).lower() == "false"
        url = self._api_url( "histories/%s/contents/%s" % ( self.history_id, hda1["id" ] ), use_key=True )
        delete_response = delete_request( url )
        assert delete_response.status_code < 300  # Something in the 200s :).
        assert str( self.__show( hda1 ).json()[ "deleted" ] ).lower() == "true"

    def __show( self, hda ):
        show_response = self._get( "histories/%s/contents/%s" % ( self.history_id, hda[ "id" ] ) )
        return show_response

    def __count_contents( self, history_id=None, **kwds ):
        if history_id == None:
            history_id = self.history_id
        contents_response = self._get( "histories/%s/contents" % history_id, kwds )
        return len( contents_response.json() )

    def __assert_hda_has_full_details( self, hda_details ):
        self._assert_has_keys( hda_details, "display_types", "display_apps" )

    def __check_for_hda( self, contents_response, hda ):
        self._assert_status_code_is( contents_response, 200 )
        contents = contents_response.json()
        assert len( contents ) == 1
        hda_summary = contents[ 0 ]
        self.__assert_matches_hda( hda, hda_summary )
        return hda_summary

    def __assert_matches_hda( self, input_hda, query_hda ):
        self._assert_has_keys( query_hda, "id", "name" )
        assert input_hda[ "name" ] == query_hda[ "name" ]
        assert input_hda[ "id" ] == query_hda[ "id" ]
