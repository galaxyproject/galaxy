// This file isn't really testing anything useful yet, it is just testing
// (or demonstrating) qunit+backbone interactions.
define([
    "mvc/dataset/hda-model",
    "jquery",
    "sinon-qunit"
], function(
    hdaModel,
    $,
    sinon
){
    module( "History Contents Model Tests" );

    test( "HDA Constructions with Default Attributes", function() {
        var hda = new hdaModel.HistoryDatasetAssociation();
        expect( 2 );
        equal( hda.get( 'name' ), "(unnamed dataset)" );
        equal( hda.get( 'state' ), "new" );
    } );

    test( "HDA Construction with Supplied Attributes", function() {
        var hda = new hdaModel.HistoryDatasetAssociation( {
            name: "my dataset",
            state: "ok",
        } );
        expect( 2 );

        equal( hda.get( 'name' ), "my dataset" );
        equal( hda.get( 'state' ), "ok" );
    } );

    test( "HDA Deletion", function() {
        var hda = new hdaModel.HistoryDatasetAssociation( {
            id: "hda1",
            history_id: "h1",
            deleted: false,
        } );

        // Demonstrate sinon stubbing out of Ajax queries...
        equal( hda.get( 'deleted' ), false );
        sinon.stub( $, "ajax" );
        hda.delete();
        equal( hda.get( 'deleted' ), true );
        ok( $.ajax.calledWithMatch( { url: "/api/histories/h1/contents/hda1" } ) );
    } );
} );
