# -*- coding: utf-8 -*-

import json

from requests import delete, put

from base import api
from base.populators import DatasetCollectionPopulator, LibraryPopulator, TestsDatasets


# TODO: Test anonymous access.
class HistoryContentsApiTestCase( api.ApiTestCase, TestsDatasets ):

    def setUp( self ):
        super( HistoryContentsApiTestCase, self ).setUp()
        self.history_id = self._new_history()
        self.dataset_collection_populator = DatasetCollectionPopulator( self.galaxy_interactor )

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

    def test_update(self):
        hda1 = self._wait_for_new_hda()
        assert str(hda1["deleted"]).lower() == "false"
        update_response = self._raw_update(hda1["id"], dict(deleted=True))
        self._assert_status_code_is(update_response, 200)
        show_response = self.__show(hda1)
        assert str(show_response.json()["deleted"]).lower() == "true"

        update_response = self._raw_update(hda1["id"], dict(name="Updated Name"))
        assert self.__show(hda1).json()["name"] == "Updated Name"

        update_response = self._raw_update(hda1["id"], dict(name="Updated Name"))
        assert self.__show(hda1).json()["name"] == "Updated Name"

        unicode_name = u'ржевский сапоги'
        update_response = self._raw_update(hda1["id"], dict(name=unicode_name))
        updated_hda = self.__show(hda1).json()
        assert updated_hda["name"] == unicode_name, updated_hda

        quoted_name = '"Mooo"'
        update_response = self._raw_update(hda1["id"], dict(name=quoted_name))
        updated_hda = self.__show(hda1).json()
        assert updated_hda["name"] == quoted_name, quoted_name

    def test_update_type_failures(self):
        hda1 = self._wait_for_new_hda()
        update_response = self._raw_update(hda1["id"], dict(deleted='not valid'))
        self._assert_status_code_is(update_response, 400)

    def _wait_for_new_hda(self):
        hda1 = self._new_dataset(self.history_id)
        self._wait_for_history(self.history_id)
        return hda1

    def _raw_update(self, item_id, data):
        update_url = self._api_url( "histories/%s/contents/%s" % (self.history_id, item_id), use_key=True)
        update_response = put(update_url, json=data)
        return update_response

    def test_delete( self ):
        hda1 = self._new_dataset( self.history_id )
        self._wait_for_history( self.history_id )
        assert str( self.__show( hda1 ).json()[ "deleted" ] ).lower() == "false"
        url = self._api_url( "histories/%s/contents/%s" % ( self.history_id, hda1["id" ] ), use_key=True )
        delete_response = delete( url )
        assert delete_response.status_code < 300  # Something in the 200s :).
        assert str( self.__show( hda1 ).json()[ "deleted" ] ).lower() == "true"

    def test_dataset_collections( self ):
        payload = self.dataset_collection_populator.create_pair_payload(
            self.history_id,
            type="dataset_collection"
        )
        pre_collection_count = self.__count_contents( type="dataset_collection" )
        pre_dataset_count = self.__count_contents( type="dataset" )
        pre_combined_count = self.__count_contents( type="dataset,dataset_collection" )

        dataset_collection_response = self._post( "histories/%s/contents" % self.history_id, payload )

        dataset_collection = self.__check_create_collection_response( dataset_collection_response )

        post_collection_count = self.__count_contents( type="dataset_collection" )
        post_dataset_count = self.__count_contents( type="dataset" )
        post_combined_count = self.__count_contents( type="dataset,dataset_collection" )

        # Test filtering types with index.
        assert pre_collection_count == 0
        assert post_collection_count == 1
        assert post_combined_count == pre_dataset_count + 1
        assert post_combined_count == pre_combined_count + 1
        assert pre_dataset_count == post_dataset_count

        # Test show dataset colleciton.
        collection_url = "histories/%s/contents/dataset_collections/%s" % ( self.history_id, dataset_collection[ "id" ] )
        show_response = self._get( collection_url )
        self._assert_status_code_is( show_response, 200 )
        dataset_collection = show_response.json()
        self._assert_has_keys( dataset_collection, "url", "name", "deleted" )

        assert not dataset_collection[ "deleted" ]

        delete_response = delete( self._api_url( collection_url, use_key=True ) )
        self._assert_status_code_is( delete_response, 200 )

        show_response = self._get( collection_url )
        dataset_collection = show_response.json()
        assert dataset_collection[ "deleted" ]

    def test_update_dataset_collection( self ):
        payload = self.dataset_collection_populator.create_pair_payload(
            self.history_id,
            type="dataset_collection"
        )
        dataset_collection_response = self._post( "histories/%s/contents" % self.history_id, payload )
        self._assert_status_code_is( dataset_collection_response, 200 )
        hdca = dataset_collection_response.json()
        update_url = self._api_url( "histories/%s/contents/dataset_collections/%s" % ( self.history_id, hdca[ "id" ] ), use_key=True )
        # Awkward json.dumps required here because of https://trello.com/c/CQwmCeG6
        body = json.dumps( dict( name="newnameforpair" ) )
        update_response = put( update_url, data=body )
        self._assert_status_code_is( update_response, 200 )
        show_response = self.__show( hdca )
        assert str( show_response.json()[ "name" ] ) == "newnameforpair"

    def test_hdca_copy( self ):
        hdca = self.dataset_collection_populator.create_pair_in_history( self.history_id ).json()
        hdca_id = hdca[ "id" ]
        second_history_id = self._new_history()
        create_data = dict(
            source='hdca',
            content=hdca_id,
        )
        assert len( self._get( "histories/%s/contents/dataset_collections" % second_history_id ).json() ) == 0
        create_response = self._post( "histories/%s/contents/dataset_collections" % second_history_id, create_data )
        self.__check_create_collection_response( create_response )
        assert len( self._get( "histories/%s/contents/dataset_collections" % second_history_id ).json() ) == 1

    def __check_create_collection_response( self, response ):
        self._assert_status_code_is( response, 200 )
        dataset_collection = response.json()
        self._assert_has_keys( dataset_collection, "url", "name", "deleted", "visible", "elements" )
        return dataset_collection

    def __show( self, contents ):
        show_response = self._get( "histories/%s/contents/%ss/%s" % ( self.history_id, contents["history_content_type"], contents[ "id" ] ) )
        return show_response

    def __count_contents( self, history_id=None, **kwds ):
        if history_id is None:
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
