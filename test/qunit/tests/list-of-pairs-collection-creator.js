/* global define */
define([
    "mvc/collection/list-of-pairs-collection-creator",
    "test-data/paired-collection-creator.data",
    "jquery",
    "sinon",
    "QUnit"
], function(
    PAIRED_COLLECTION_CREATOR,
    DATA,
    $,
    sinon,
    QUnit
){
    "use strict";
    PAIRED_COLLECTION_CREATOR = PAIRED_COLLECTION_CREATOR.default;
    var PCC = PAIRED_COLLECTION_CREATOR.PairedCollectionCreator;

    QUnit.module( "Galaxy client app tests" );

    QUnit.test( "Collection creation", function(assert) {
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
        assert.deepEqual( requestJSON, DATA._1requestJSON );
    });

    QUnit.test( "Creator base/empty construction/initializiation defaults", function(assert) {
        var pcc = new PCC([]);
        assert.ok( pcc instanceof PCC );
        assert.deepEqual( pcc.filters, pcc.commonFilters[ pcc.DEFAULT_FILTERS ] );
        assert.ok( pcc.automaticallyPair );
        assert.equal( pcc.matchPercentage, 0.9 );
        assert.equal( pcc.strategy, 'autopairLCS' );
    });

    QUnit.test( "Creator construction/initializiation with datasets", function(assert) {
        var pcc = new PCC({
            datasets    : DATA._1
        });
        //pcc.initialList.forEach( function( dataset, i ){
        //    console.log( i + ':\n' + JSON.stringify( dataset ) );
        //});
        // pcc maintains the original list - which, in this case, is already sorted
        assert.deepEqual( pcc.initialList, DATA._1 );
        // datasets 1 has no ids, so the pcc will create them
        assert.ok( _.every( pcc.initialList, function( dataset ){
            return dataset.id;
        }));
        // datasets 1 is very easy to auto pair
        assert.equal( pcc.unpaired.length, 0 );
        assert.equal( pcc.paired.length, pcc.initialList.length / 2 );
    });

    QUnit.test( "Try easy autopairing with simple exact matching", function(assert) {
        var pcc = new PCC({
            datasets    : DATA._1,
            strategy    : 'simple',
            twoPassAutopairing : false
        });
        assert.equal( pcc.unpaired.length, 0 );
        assert.equal( pcc.paired.length, pcc.initialList.length / 2 );
    });

    QUnit.test( "Try easy autopairing with LCS", function(assert) {
        var pcc = new PCC({
            datasets    : DATA._1,
            strategy    : 'lcs',
            twoPassAutopairing : false
        });
        assert.equal( pcc.unpaired.length, 0 );
        assert.equal( pcc.paired.length, pcc.initialList.length / 2 );
    });

    QUnit.test( "Try easy autopairing with Levenshtein", function(assert) {
        var pcc = new PCC({
            datasets    : DATA._1,
            strategy    : 'levenshtein',
            twoPassAutopairing : false
        });
        assert.equal( pcc.unpaired.length, 0 );
        assert.equal( pcc.paired.length, pcc.initialList.length / 2 );
    });

    //TODO:
    //  filters: clearing, setting via popover, regex
    //  partition: maximize paired, maximize unpaired, split evenly
    //  pairing: manually pairing and unpairing
    //  misc: renaming pairs, removing file extensions
});
