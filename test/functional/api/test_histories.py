import time
from base import api
# requests.{post,put,get} or something like it if unavailable
from base.interactor import post_request
from base.interactor import put_request
from base.interactor import get_request
from .helpers import TestsDatasets



class HistoriesApiTestCase( api.ApiTestCase, TestsDatasets ):

    def test_create_history( self ):
        # Create a history.
        post_data = dict( name="TestHistory1" )
        create_response = self._post( "histories", data=post_data ).json()
        self._assert_has_keys( create_response, "name", "id" )
        self.assertEquals( create_response[ "name" ], "TestHistory1" )
        created_id = create_response[ "id" ]

        # Make sure new history appears in index of user's histories.
        index_response = self._get( "histories" ).json()
        indexed_history = [ h for h in index_response if h[ "id" ] == created_id ][0]
        self.assertEquals(indexed_history[ "name" ], "TestHistory1")

    def test_create_anonymous_fails( self ):
        post_data = dict( name="CannotCreate" )
        # Using lower-level _api_url will cause key to not be injected.
        histories_url = self._api_url( "histories" )
        create_response = post_request( url=histories_url, data=post_data )
        self._assert_status_code_is( create_response, 403 )

    def test_export( self ):
        history_id = self._new_history()
        self._new_dataset( history_id, content="1 2 3" )
        self._wait_for_history( history_id, assert_ok=True )
        export_url = self._api_url( "histories/%s/exports" % history_id , use_key=True )
        put_response = put_request( export_url )
        self._assert_status_code_is( put_response, 202 )
        while True:
            put_response = put_request( export_url )
            if put_response.status_code == 202:
                time.sleep( .1 )
            else:
                break
        self._assert_status_code_is( put_response, 200 )
        response = put_response.json()
        self._assert_has_keys( response, "download_url" )
        download_path = response[ "download_url" ]
        full_download_url = "%s%s?key=%s" % ( self.url, download_path, self.galaxy_interactor.api_key )
        download_response = get_request( full_download_url )
        self._assert_status_code_is( download_response, 200 )
