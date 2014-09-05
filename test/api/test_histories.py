from base import api
from requests import post
from requests import put
from requests import get
from .helpers import DatasetPopulator, wait_on


class HistoriesApiTestCase( api.ApiTestCase ):

    def setUp( self ):
        super( HistoriesApiTestCase, self ).setUp( )
        self.dataset_populator = DatasetPopulator( self.galaxy_interactor )

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
        create_response = post( url=histories_url, data=post_data )
        self._assert_status_code_is( create_response, 403 )

    def test_import_export( self ):
        history_id = self.dataset_populator.new_history( name="for_export" )
        self.dataset_populator.new_dataset( history_id, content="1 2 3" )
        self.dataset_populator.wait_for_history( history_id, assert_ok=True )
        download_path = self._export( history_id )
        full_download_url = "%s%s?key=%s" % ( self.url, download_path, self.galaxy_interactor.api_key )
        download_response = get( full_download_url )
        self._assert_status_code_is( download_response, 200 )

        def history_names():
            history_index = self._get( "histories" )
            return dict( map( lambda h: ( h[ "name" ], h ), history_index.json() ) )

        import_name = "imported from archive: for_export"
        assert import_name not in history_names()

        import_data = dict( archive_source=full_download_url, archive_type="url" )
        import_response = self._post( "histories", data=import_data )

        self._assert_status_code_is( import_response, 200 )

        def has_history_with_name():
            histories = history_names()
            return histories.get( import_name, None )

        imported_history = wait_on( has_history_with_name, desc="import history" )
        imported_history_id = imported_history[ "id" ]
        self.dataset_populator.wait_for_history( imported_history_id )
        contents_response = self._get( "histories/%s/contents" % imported_history_id )
        self._assert_status_code_is( contents_response, 200 )
        contents = contents_response.json()
        assert len( contents ) == 1
        imported_content = self.dataset_populator.get_history_dataset_content(
            history_id=imported_history_id,
            dataset_id=contents[ 0 ][ "id" ]
        )
        assert imported_content == "1 2 3\n"

    def _export(self, history_id):
        export_url = self._api_url( "histories/%s/exports" % history_id, use_key=True )
        put_response = put( export_url )
        self._assert_status_code_is( put_response, 202 )

        def export_ready_response():
            put_response = put( export_url )
            if put_response.status_code == 202:
                return None
            return put_response

        put_response = wait_on( export_ready_response, desc="export ready" )
        self._assert_status_code_is( put_response, 200 )
        response = put_response.json()
        self._assert_has_keys( response, "download_url" )
        download_path = response[ "download_url" ]
        return download_path

    #TODO: (CE) test_create_from_copy
