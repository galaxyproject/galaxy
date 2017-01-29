import json

from base import api
from base.populators import DatasetCollectionPopulator, DatasetPopulator


class DatasetCollectionApiTestCase( api.ApiTestCase ):

    def setUp( self ):
        super( DatasetCollectionApiTestCase, self ).setUp()
        self.dataset_populator = DatasetPopulator( self.galaxy_interactor )
        self.dataset_collection_populator = DatasetCollectionPopulator( self.galaxy_interactor )
        self.history_id = self.dataset_populator.new_history()

    def test_create_pair_from_history( self ):
        payload = self.dataset_collection_populator.create_pair_payload(
            self.history_id,
            instance_type="history",
        )
        create_response = self._post( "dataset_collections", payload )
        dataset_collection = self._check_create_response( create_response )
        returned_datasets = dataset_collection[ "elements" ]
        assert len( returned_datasets ) == 2, dataset_collection

    def test_create_list_from_history( self ):
        element_identifiers = self.dataset_collection_populator.list_identifiers( self.history_id )

        payload = dict(
            instance_type="history",
            history_id=self.history_id,
            element_identifiers=json.dumps(element_identifiers),
            collection_type="list",
        )

        create_response = self._post( "dataset_collections", payload )
        dataset_collection = self._check_create_response( create_response )
        returned_datasets = dataset_collection[ "elements" ]
        assert len( returned_datasets ) == 3, dataset_collection

    def test_create_list_of_existing_pairs( self ):
        pair_payload = self.dataset_collection_populator.create_pair_payload(
            self.history_id,
            instance_type="history",
        )
        pair_create_response = self._post( "dataset_collections", pair_payload )
        dataset_collection = self._check_create_response( pair_create_response )
        hdca_id = dataset_collection[ "id" ]

        element_identifiers = [
            dict( name="test1", src="hdca", id=hdca_id )
        ]

        payload = dict(
            instance_type="history",
            history_id=self.history_id,
            element_identifiers=json.dumps(element_identifiers),
            collection_type="list",
        )
        create_response = self._post( "dataset_collections", payload )
        dataset_collection = self._check_create_response( create_response )
        returned_collections = dataset_collection[ "elements" ]
        assert len( returned_collections ) == 1, dataset_collection

    def test_create_list_of_new_pairs( self ):
        pair_identifiers = self.dataset_collection_populator.pair_identifiers( self.history_id )
        element_identifiers = [ dict(
            src="new_collection",
            name="test_pair",
            collection_type="paired",
            element_identifiers=pair_identifiers,
        ) ]
        payload = dict(
            collection_type="list:paired",
            instance_type="history",
            history_id=self.history_id,
            name="a nested collection",
            element_identifiers=json.dumps( element_identifiers ),
        )
        create_response = self._post( "dataset_collections", payload )
        dataset_collection = self._check_create_response( create_response )
        assert dataset_collection[ "collection_type" ] == "list:paired"
        assert dataset_collection[ "name" ] == "a nested collection"
        returned_collections = dataset_collection[ "elements" ]
        assert len( returned_collections ) == 1, dataset_collection
        pair_1_element = returned_collections[ 0 ]
        self._assert_has_keys( pair_1_element, "element_index" )
        pair_1_object = pair_1_element[ "object" ]
        self._assert_has_keys( pair_1_object, "collection_type", "elements" )
        self.assertEquals( pair_1_object[ "collection_type" ], "paired" )
        self.assertEquals( pair_1_object[ "populated" ], True )
        pair_elements = pair_1_object[ "elements" ]
        assert len( pair_elements ) == 2
        pair_1_element_1 = pair_elements[ 0 ]
        assert pair_1_element_1[ "element_index" ] == 0

    def test_hda_security( self ):
        element_identifiers = self.dataset_collection_populator.pair_identifiers( self.history_id )

        with self._different_user( ):
            history_id = self.dataset_populator.new_history()
            payload = dict(
                instance_type="history",
                history_id=history_id,
                element_identifiers=json.dumps(element_identifiers),
                collection_type="paired",
            )

            self._post( "dataset_collections", payload )
            # TODO: re-enable once there is a way to restrict access
            # to this dataset via the API.
            # self._assert_status_code_is( create_response, 403 )

    def test_enforces_unique_names( self ):
        element_identifiers = self.dataset_collection_populator.list_identifiers( self.history_id )
        element_identifiers[ 2 ][ "name" ] = element_identifiers[ 0 ][ "name" ]
        payload = dict(
            instance_type="history",
            history_id=self.history_id,
            element_identifiers=json.dumps(element_identifiers),
            collection_type="list",
        )

        create_response = self._post( "dataset_collections", payload )
        self._assert_status_code_is( create_response, 400 )

    def _check_create_response( self, create_response ):
        self._assert_status_code_is( create_response, 200 )
        dataset_collection = create_response.json()
        self._assert_has_keys( dataset_collection, "elements", "url", "name", "collection_type" )
        return dataset_collection
