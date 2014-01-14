from base import api
# requests.post or something like it if unavailable
from base.interactor import post_request


class HistoriesApiTestCase( api.ApiTestCase ):

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
