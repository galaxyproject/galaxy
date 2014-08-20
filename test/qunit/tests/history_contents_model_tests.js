// This file isn't really testing anything useful yet, it is just testing
// (or demonstrating) qunit+backbone interactions.
define([
    "mvc/history/hda-model",
    "jquery",
    "sinon-qunit"
], function(
    HDA_MODEL,
    $,
    sinon
){
    module( "History Contents Model Tests" );

    test( "HDA Constructions with Default Attributes", function() {
        var hda = new HDA_MODEL.HistoryDatasetAssociation({});
        equal( hda.get( 'name' ), "(unnamed dataset)" );
        equal( hda.get( 'state' ), "new" );
    } );

    test( "HDA Construction with Supplied Attributes", function() {
        var hda = new HDA_MODEL.HistoryDatasetAssociation({
                history_content_type : 'dataset',
                name: "my dataset",
                state: "ok"
            });
        equal( hda.get( 'name' ), "my dataset" );
        equal( hda.get( 'state' ), "ok" );
    } );

    test( "HDA Deletion", function() {
        var hda = new HDA_MODEL.HistoryDatasetAssociation({
                history_content_type : 'dataset',
                id: "hda1",
                history_id: "h1",
                deleted: false
            });
        equal( hda.get( 'deleted' ), false );
        sinon.stub( $, "ajax" );
        hda[ 'delete' ]();
        equal( hda.get( 'deleted' ), true );
        // to get the url sinon used:
        //console.debug( $.ajax.lastCall.args[0].url )
        ok( $.ajax.calledWithMatch( { url: "/api/histories/h1/contents/datasets/hda1" } ) );
    });
});
