var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Test the history API', 0, function suite( test ){
    spaceghost.start();

// =================================================================== SET UP
var email = spaceghost.user.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
}
spaceghost.user.loginOrRegisterUser( email, password );


// =================================================================== TESTS
spaceghost.openHomePage().then( function(){

    // ------------------------------------------------------------------------------------------- INDEX
    this.test.comment( 'index should get a list of histories' );
    var historyIndex = this.api.histories.index();
    //this.debug( this.jsonStr( historyIndex ) );
    this.test.assert( utils.isArray( historyIndex ), "index returned an array: length " + historyIndex.length );
    this.test.assert( historyIndex.length >= 1, 'Has at least one history' );

    var firstHistory = historyIndex[0];
    this.test.assert( this.hasKeys( firstHistory, [ 'id', 'name', 'url' ] ), 'Has the proper keys' );
    this.test.assert( this.api.isEncodedId( firstHistory.id ), 'Id appears well-formed' );


    // ------------------------------------------------------------------------------------------- SHOW
    this.test.comment( 'show should get a history details object' );
    var historyShow = this.api.histories.show( firstHistory.id );
    //this.debug( this.jsonStr( historyShow ) );
    this.test.assert( this.hasKeys( historyShow, [
            'id', 'name', 'annotation', 'nice_size', 'contents_url',
            'state', 'state_details', 'state_ids' ]),
        'Has the proper keys' );

    this.test.comment( 'a history details object should contain two objects named state_details and state_ids' );
    var states = [
            'discarded', 'empty', 'error', 'failed_metadata', 'new',
            'ok', 'paused', 'queued', 'running', 'setting_metadata', 'upload' ],
        state_details = historyShow.state_details,
        state_ids = historyShow.state_ids;
    this.test.assert( this.hasKeys( state_details, states ), 'state_details has the proper keys' );
    this.test.assert( this.hasKeys( state_ids, states ),     'state_ids has the proper keys' );
    var state_detailsAreNumbers = true;
        state_idsAreArrays = true;
    states.forEach( function( state ){
        if( !utils.isArray( state_ids[ state ] ) ){ state_idsAreArrays = false; }
        if( !utils.isNumber( state_details[ state ] ) ){ state_detailsAreNumbers = false; }
    });
    this.test.assert( state_idsAreArrays, 'state_ids values are arrays' );
    this.test.assert( state_detailsAreNumbers, 'state_details values are numbers' );

    this.test.comment( 'calling show with "most_recently_used" should return the first history' );
    historyShow = this.api.histories.show( 'most_recently_used' );
    //this.debug( this.jsonStr( historyShow ) );
    this.test.assert( historyShow.id === firstHistory.id, 'Is the first history' );

    this.test.comment( 'Should be able to combine calls' );
    this.test.assert( this.api.histories.show( this.api.histories.index()[0].id ).id === firstHistory.id,
        'combining function calls works' );

    // ------------------------------------------------------------------------------------------- CREATE
    this.test.comment( 'Calling create should create a new history and allow setting the name' );
    var newHistoryName = 'Created History',
        createdHistory = this.api.histories.create({ name: newHistoryName });
    //this.debug( 'returned from create:\n' + this.jsonStr( createdHistory ) );
    this.test.assert( createdHistory.name === newHistoryName,
        "Name of created history (from create) is correct: " + createdHistory.name );

    // check the index
    var newFirstHistory = this.api.histories.index()[0];
    //this.debug( 'newFirstHistory:\n' + this.jsonStr( newFirstHistory ) );
    this.test.assert( newFirstHistory.name === newHistoryName,
        "Name of last history (from index) is correct: " + newFirstHistory.name );
    this.test.assert( newFirstHistory.id === createdHistory.id,
        "Id of last history (from index) is correct: " + newFirstHistory.id );


    // ------------------------------------------------------------------------------------------- DELETE
    this.test.comment( 'calling delete should delete the given history and remove it from the standard index' );
    var deletedHistory = this.api.histories.delete_( createdHistory.id );
    //this.debug( 'returned from delete:\n' + this.jsonStr( deletedHistory ) );
    this.test.assert( deletedHistory.id === createdHistory.id,
        "Deletion returned id matching created history: " + deletedHistory.id );
    this.test.assert( deletedHistory.deleted === true,
        "Deletion return 'deleted: true': " + deletedHistory.deleted );

    newFirstHistory = this.api.histories.index()[0];
    //this.debug( 'newFirstHistory:\n' + this.jsonStr( newFirstHistory ) );
    this.test.assert( newFirstHistory.id !== createdHistory.id,
        "Id of last history (from index) DOES NOT appear: " + newFirstHistory.id );

    this.test.comment( 'calling index with delete=true should include the deleted history' );
    newFirstHistory = this.api.histories.index({ deleted: true })[0];
    //this.debug( 'newFirstHistory:\n' + this.jsonStr( newFirstHistory ) );
    this.test.assert( newFirstHistory.id === createdHistory.id,
        "Id of last history (from index) DOES appear using index( deleted=true ): " + newFirstHistory.id );


    // ------------------------------------------------------------------------------------------- UNDELETE
    this.test.comment( 'calling undelete should undelete the given history and re-include it in index' );
    var undeletedHistory = this.api.histories.undelete( createdHistory.id );
    this.debug( 'returned from undelete:\n' + this.jsonStr( undeletedHistory ) );
    this.test.assert( ( undeletedHistory.id === createdHistory.id ) && ( !undeletedHistory.deleted ),
        "Undeletion new, updated JSON for the history" );

    newFirstHistory = this.api.histories.index()[0];
    //this.debug( 'newFirstHistory:\n' + this.jsonStr( newFirstHistory ) );
    this.test.assert( newFirstHistory.id === createdHistory.id,
        "Id of last history (from index) DOES appear after undeletion: " + newFirstHistory.id );

    //TODO: show, deleted flag
    //TODO: delete, purge flag

    // ------------------------------------------------------------------------------------------- UPDATE
    // ........................................................................................... name
    this.test.comment( 'update should allow changing the name' );
    returned = this.api.histories.update( newFirstHistory.id, {
        name : 'New name'
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id );
    this.test.assert( historyShow.name === 'New name', "Name successfully set via update: " + historyShow.name );

    // no sanitizing input
    //this.test.comment( 'update should sanitize any new name' );

    //NOTE!: this fails on sqlite3 (with default setup)
    this.test.comment( 'update should allow unicode in names' );
    var unicodeName = '桜ゲノム';
    returned = this.api.histories.update( newFirstHistory.id, {
        name : unicodeName
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id );
    this.test.assert( historyShow.name === unicodeName, "Update accepted unicode name: " + historyShow.name );

    this.test.comment( 'update should allow escaped quotations in names' );
    var quotedName = '"Bler"';
    returned = this.api.histories.update( newFirstHistory.id, {
        name : quotedName
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id );
    this.test.assert( historyShow.name === quotedName,
        "Update accepted escaped quotations in name: " + historyShow.name );


    // ........................................................................................... deleted
    this.test.comment( 'update should allow changing the deleted flag' );
    returned = this.api.histories.update( newFirstHistory.id, {
        deleted: true
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id, true );
    this.test.assert( historyShow.deleted === true, "Update set the deleted flag: " + historyShow.deleted );

    this.test.comment( 'update should allow changing the deleted flag back' );
    returned = this.api.histories.update( newFirstHistory.id, {
        deleted: false
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id );
    this.test.assert( historyShow.deleted === false, "Update set the deleted flag: " + historyShow.deleted );


    // ........................................................................................... published
    this.test.comment( 'update should allow changing the published flag' );
    returned = this.api.histories.update( newFirstHistory.id, {
        published: true
    });
    this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id );
    this.test.assert( historyShow.published === true, "Update set the published flag: " + historyShow.published );


    // ........................................................................................... genome_build
    this.test.comment( 'update should allow changing the genome_build' );
    returned = this.api.histories.update( newFirstHistory.id, {
        genome_build : 'hg18'
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id );
    this.test.assert( historyShow.genome_build === 'hg18',
        "genome_build successfully set via update: " + historyShow.genome_build );

    // no sanitizing input
    //this.test.comment( 'update should sanitize any genome_build' );

    // removed since we have no pre-installed unicode builds
    //this.test.comment( 'update should allow unicode in genome builds' );

    spaceghost.test.comment( 'An unknown reference/genome_build should return a 400' );
    this.api.assertRaises( function(){
        returned = this.api.histories.update( newFirstHistory.id, {
            genome_build : 'wookiee12'
        });
    }, 400, 'invalid reference', 'Bad Request with invalid id: show' );


    // ........................................................................................... annotation
    this.test.comment( 'update should allow changing the annotation' );
    var newAnnotation = 'Here are some notes that I stole from the person next to me';
    returned = this.api.histories.update( newFirstHistory.id, {
        annotation : newAnnotation
    });
    this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id );
    this.test.assert( historyShow.annotation === newAnnotation,
        "Annotation successfully set via update: " + historyShow.annotation );

    // no sanitizing input
    //this.test.comment( 'update should sanitize any new annotation' );

    this.test.comment( 'update should allow unicode in annotations' );
    var unicodeAnnotation = 'お願いは、それが落下させない';
    returned = this.api.histories.update( newFirstHistory.id, {
        annotation : unicodeAnnotation
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id );
    this.test.assert( historyShow.annotation === unicodeAnnotation,
        "Update accepted unicode annotation: " + historyShow.annotation );

    this.test.comment( 'update should allow escaped quotations in annotations' );
    var quotedAnnotation = '"Bler"';
    returned = this.api.histories.update( newFirstHistory.id, {
        annotation : quotedAnnotation
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id );
    this.test.assert( historyShow.annotation === quotedAnnotation,
        "Update accepted escaped quotations in annotation: " + historyShow.annotation );


    // ------------------------------------------------------------------------------------------- ERRORS
    // ........................................................................................... idiot proofing
    this.test.comment( 'updating using a nonsense key should fail silently' );
    returned = this.api.histories.update( newFirstHistory.id, {
        konamiCode : 'uuddlrlrba'
    });
    this.test.assert( returned.konamiCode === undefined, 'key was not set: ' + returned.konamiCode );

    // test server bad id protection
    spaceghost.test.comment( 'A bad id should throw an error' );
    this.api.assertRaises( function(){
        this.api.histories.show( '1234123412341234' );
    }, 400, 'unable to decode', 'Bad Request with invalid id: show' );
    spaceghost.test.comment( 'A bad id should throw an error when using update' );
    this.api.assertRaises( function(){
        this.api.histories.update( '1234123412341234', {} );
    }, 400, 'unable to decode', 'Bad Request with invalid id: update' );
    spaceghost.test.comment( 'A bad id should throw an error when using delete' );
    this.api.assertRaises( function(){
        this.api.histories.delete_( '1234123412341234' );
    }, 400, 'unable to decode', 'Bad Request with invalid id: delete' );
    spaceghost.test.comment( 'A bad id should throw an error when using undelete' );
    this.api.assertRaises( function(){
        this.api.histories.undelete( '1234123412341234' );
    }, 400, 'unable to decode', 'Bad Request with invalid id: undelete' );

    this.test.comment( 'updating by attempting to change type should cause an error' );
    [ 'name', 'annotation' ].forEach( function( key ){
        var updatedAttrs = {};
        updatedAttrs[ key ] = false;
        spaceghost.api.assertRaises( function(){
            returned = spaceghost.api.histories.update( newFirstHistory.id, updatedAttrs );
        // note: annotation can be basestring or null (a tuple) so just use the partial error string
        }, 400, 'must be a type', 'type validation error' );
    });
    [ 'deleted', 'importable', 'published' ].forEach( function( key ){
        var updatedAttrs = {};
        updatedAttrs[ key ] = 'straaang';
        spaceghost.api.assertRaises( function(){
            returned = spaceghost.api.histories.update( newFirstHistory.id, updatedAttrs );
        }, 400, "must be a type: <type 'bool'>", 'type validation error' );
    });
    spaceghost.api.assertRaises( function(){
        returned = spaceghost.api.histories.update( newFirstHistory.id, { tags: 'you\'re it' });
    }, 400, "must be a type: <type 'list'>", 'type validation error' );
    spaceghost.api.assertRaises( function(){
        returned = spaceghost.api.histories.update( newFirstHistory.id, { tags: [ true ] });
    }, 400, "must be a type: <type 'basestring'>", 'type validation error' );

    // no longer throws if showing deleted...
    //this.test.comment( 'calling show with /deleted should raise a bad request' );
/*
*/
    //this.debug( this.jsonStr( historyShow ) );
});

// ===================================================================
    spaceghost.run( function(){ test.done(); });
});
