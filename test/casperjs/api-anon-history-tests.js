var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Test API functions for histories with an anonymous user', 0, function suite( test ){
    spaceghost.start();

// =================================================================== TESTS
spaceghost.thenOpen( spaceghost.baseUrl ).waitForSelector( spaceghost.historypanel.data.selectors.history.name );
spaceghost.then( function(){

    // ------------------------------------------------------------------------------------------- anon allowed
    this.test.comment( 'index should get a list of histories' );
    var index = this.api.histories.index();
    this.test.assert( utils.isArray( index ), "index returned an array: length " + index.length );
    this.test.assert( index.length === 1, 'Has at least one history' );

    this.test.comment( 'show should get a history details object' );
    var historyShow = this.api.histories.show( index[0].id );
    //this.debug( this.jsonStr( historyShow ) );
    this.test.assert( historyShow.id === index[0].id, 'Is the first history' );
    this.test.assert( this.hasKeys( historyShow, [ 'id', 'name', 'user_id' ] ) );


    // ------------------------------------------------------------------------------------------- anon forbidden
    //TODO: why not return the current history?
    this.test.comment( 'calling show with "most_recently_used" should return None for an anon user' );
    var recent = this.api.histories.show( 'most_recently_used' );
    this.test.assert( recent === null, 'most_recently_used returned None' );

    this.test.comment( 'Calling create should fail for an anonymous user' );
    this.api.assertRaises( function(){
        this.api.histories.create({ name: 'new' });
    }, 403, 'API authentication required for this request', 'create failed with error' );

    this.test.comment( 'Calling delete should fail for an anonymous user' );
    this.api.assertRaises( function(){
        this.api.histories.delete_( historyShow.id );
    }, 403, 'API authentication required for this request', 'create failed with error' );

    this.test.comment( 'Calling update should fail for an anonymous user' );
    this.api.assertRaises( function(){
        this.api.histories.update( historyShow.id, {} );
    }, 403, 'API authentication required for this request', 'update failed with error' );

    //TODO: need these two in api.js
    //this.test.comment( 'Calling archive_import should fail for an anonymous user' );
    //this.api.assertRaises( function(){
    //    this.api.histories.archive_import( historyShow.id, {} );
    //}, 403, 'API authentication required for this request', 'archive_import failed with error' );

    //this.test.comment( 'Calling archive_download should fail for an anonymous user' );
    //this.api.assertRaises( function(){
    //    this.api.histories.archive_download( historyShow.id, {} );
    //}, 403, 'API authentication required for this request', 'archive_download failed with error' );

    // test server bad id protection
    spaceghost.test.comment( 'A bad id should throw an error' );
    this.api.assertRaises( function(){
        this.api.histories.show( '1234123412341234' );
    }, 400, 'unable to decode', 'Bad Request with invalid id: show' );

});

// ------------------------------------------------------------------------------------------- hdas
spaceghost.thenOpen( spaceghost.baseUrl ).waitForSelector( spaceghost.historypanel.data.selectors.history.name );
spaceghost.then( function(){
    spaceghost.tools.uploadFile( '../../test-data/1.sam', function( uploadInfo ){
        this.test.assert( uploadInfo.hdaElement !== null, "Convenience function produced hda" );
        var state = this.historypanel.getHdaState( '#' + uploadInfo.hdaElement.attributes.id );
        this.test.assert( state === 'ok', "Convenience function produced hda in ok state" );
    });
});

spaceghost.then( function(){
    var current = this.api.histories.index()[0];

    // ------------------------------------------------------------------------------------------- anon allowed
    this.test.comment( 'anonymous users can index hdas in their current history' );
    var hdaIndex = this.api.hdas.index( current.id );
    this.test.assert( hdaIndex.length === 1, 'indexed hdas' );

    this.test.comment( 'anonymous users can show hdas in their current history' );
    var hda = this.api.hdas.show( current.id, hdaIndex[0].id );
    this.test.assert( this.hasKeys( hda, [ 'id', 'name' ] ), 'showed hda: ' + hda.name );

    this.test.comment( 'anonymous users can hide hdas in their current history' );
    var changed = this.api.hdas.update( current.id, hda.id, { visible: false });
    hda = this.api.hdas.show( current.id, hda.id );
    this.test.assert( hda.visible === false, 'successfully hidden' );

    this.test.comment( 'anonymous users can mark their hdas as deleted in their current history' );
    changed = this.api.hdas.update( current.id, hda.id, { deleted: true });
    hda = this.api.hdas.show( current.id, hda.id );
    this.test.assert( hda.deleted, 'successfully deleted' );

    // ------------------------------------------------------------------------------------------- anon forbidden
    this.test.comment( 'Creating an hda should work for an anonymous user' );
    var returned = this.api.hdas.create( current.id, { source: 'hda', content: hda.id });
    //this.debug( this.jsonStr( returned ) );
    this.test.assert( returned.name === hda.name, 'name matches: ' + returned.name );
    this.test.assert( returned.id !== hda.id, 'new id: ' + returned.id );

    //TODO: should be allowed
    this.test.comment( 'Calling hda delete should fail for an anonymous user' );
    this.api.assertRaises( function(){
        this.api.hdas.delete_( current.id, hda.id );
    }, 403, 'API authentication required for this request', 'delete failed with error' );

    //TODO: only sharing, tags, annotations should be blocked/prevented
    this.test.comment( 'Calling update with keys other than "visible" or "deleted" should fail silently' );
    this.test.comment( 'Calling update on tags should fail silently' );
    changed = this.api.hdas.update( current.id, hda.id, { tags: [ 'one' ] });
    hda = this.api.hdas.show( current.id, hda.id );
    this.test.assert( hda.tags.length === 0, 'tags were not set: ' + this.jsonStr( hda.tags ) );

    this.test.comment( 'Calling update on annotation should fail silently' );
    changed = this.api.hdas.update( current.id, hda.id, { annotation: 'yup yup yup' });
    hda = this.api.hdas.show( current.id, hda.id );
    this.test.assert( !hda.annotation, 'annotation was not set: ' + hda.annotation );

});

// ===================================================================
    spaceghost.run( function(){ test.done(); });
});

