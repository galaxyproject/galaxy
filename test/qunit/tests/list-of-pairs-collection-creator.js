define([
    "mvc/collection/list-of-pairs-collection-creator",
    "test-data/paired-collection-creator.data",
    "jquery",
    "sinon-qunit"
], function(
    PAIRED_COLLECTION_CREATOR,
    // why am I yelling?
    DATA,
    $,
    sinon
){
    /*globals equal test module expect deepEqual strictEqual throws ok */
    "use strict";
    var PCC = PAIRED_COLLECTION_CREATOR.PairedCollectionCreator;

    module( "Galaxy client app tests" );

    test( "Collection creation", function() {
        var pcc = new PCC({
                datasets    : DATA._1,
                historyId   : 'fakeHistoryId'
            }),
            server = sinon.fakeServer.create();

        var requestJSON;
        server.respondWith( 'POST', '/api/histories/fakeHistoryId/contents/dataset_collections', function( request ){
            requestJSON = JSON.parse( request.requestBody );
            request.respond(
                200,
                { "Content-Type": "application/json" },
                JSON.stringify({
                    fakeResponse: 'yes'
                })
            );
        });

        //console.debug( 'requestBody:', JSON.stringify( requestJSON, null, '  ' ) );
        pcc.createList( 'Heres a collection' );
        server.respond();
        deepEqual( requestJSON, DATA._1requestJSON );
    });

    test( "Creator base/empty construction/initializiation defaults", function() {
        var pcc = new PCC([]);
        ok( pcc instanceof PCC );
        deepEqual( pcc.filters, pcc.commonFilters[ pcc.DEFAULT_FILTERS ] );
        ok( pcc.automaticallyPair );
        equal( pcc.matchPercentage, 0.9 );
        equal( pcc.strategy, 'autopairLCS' );
    });

    test( "Creator construction/initializiation with datasets", function() {
        var pcc = new PCC({
            datasets    : DATA._1
        });
        //pcc.initialList.forEach( function( dataset, i ){
        //    console.log( i + ':\n' + JSON.stringify( dataset ) );
        //});
        // pcc maintains the original list - which, in this case, is already sorted
        deepEqual( pcc.initialList, DATA._1 );
        // datasets 1 has no ids, so the pcc will create them
        ok( _.every( pcc.initialList, function( dataset ){
            return dataset.id;
        }));
        // datasets 1 is very easy to auto pair
        equal( pcc.unpaired.length, 0 );
        equal( pcc.paired.length, pcc.initialList.length / 2 );
    });

    test( "Try easy autopairing with simple exact matching", function() {
        var pcc = new PCC({
            datasets    : DATA._1,
            strategy    : 'simple',
            twoPassAutopairing : false
        });
        equal( pcc.unpaired.length, 0 );
        equal( pcc.paired.length, pcc.initialList.length / 2 );
    });

    test( "Try easy autopairing with LCS", function() {
        var pcc = new PCC({
            datasets    : DATA._1,
            strategy    : 'lcs',
            twoPassAutopairing : false
        });
        equal( pcc.unpaired.length, 0 );
        equal( pcc.paired.length, pcc.initialList.length / 2 );
    });

    test( "Try easy autopairing with Levenshtein", function() {
        var pcc = new PCC({
            datasets    : DATA._1,
            strategy    : 'levenshtein',
            twoPassAutopairing : false
        });
        equal( pcc.unpaired.length, 0 );
        equal( pcc.paired.length, pcc.initialList.length / 2 );
    });

    //TODO:
    //  filters: clearing, setting via popover, regex
    //  partition: maximize paired, maximize unpaired, split evenly
    //  pairing: manually pairing and unpairing
    //  misc: renaming pairs, removing file extensions
});
