/* Utility to load a specific page and output html, page text, or a screenshot
 *  Optionally wait for some time, text, or dom selector
 */
try {
    //...if there's a better way - please let me know, universe
    var scriptDir = require( 'system' ).args[3]
            // remove the script filename
            .replace( /[\w|\.|\-|_]*$/, '' )
            // if given rel. path, prepend the curr dir
            .replace( /^(?!\/)/, './' ),
        spaceghost = require( scriptDir + 'spaceghost' ).create({
            // script options here (can be overridden by CLI)
            //verbose: true,
            //logLevel: debug,
            scriptDir: scriptDir
        });

} catch( error ){
    console.debug( error );
    phantom.exit( 1 );
}
spaceghost.start();


// =================================================================== SET UP
var utils = require( 'utils' );

var email = spaceghost.user.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
}
spaceghost.user.loginOrRegisterUser( email, password );

function hasKeys( object, keysArray ){
    if( !utils.isObject( object ) ){ return false; }
    for( var i=0; i<keysArray.length; i += 1 ){
        if( !object.hasOwnProperty( keysArray[i] ) ){
            spaceghost.debug( 'object missing key: ' + keysArray[i] );
            return false;
        }
    }
    return true;
}

function countKeys( object ){
    if( !utils.isObject( object ) ){ return 0; }
    var count = 0;
    for( var key in object ){
        if( object.hasOwnProperty( key ) ){ count += 1; }
    }
    return count;
}

// =================================================================== TESTS
spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){

    // ------------------------------------------------------------------------------------------- INDEX
    this.test.comment( 'index should get a list of histories' );
    var historyIndex = this.api.histories.index();
    //this.debug( this.jsonStr( historyIndex ) );
    this.test.assert( utils.isArray( historyIndex ), "index returned an array: length " + historyIndex.length );
    this.test.assert( historyIndex.length >= 1, 'Has at least one history' );

    var firstHistory = historyIndex[0];
    this.test.assert( hasKeys( firstHistory, [ 'id', 'name', 'url' ] ), 'Has the proper keys' );
    this.test.assert( this.api.isEncodedId( firstHistory.id ), 'Id appears well-formed' );


    // ------------------------------------------------------------------------------------------- SHOW
    this.test.comment( 'show should get a history details object' );
    var historyShow = this.api.histories.show( firstHistory.id );
    //this.debug( this.jsonStr( historyShow ) );
    this.test.assert( hasKeys( historyShow, [
            'id', 'name', 'annotation', 'nice_size', 'contents_url',
            'state', 'state_details', 'state_ids' ]),
        'Has the proper keys' );

    this.test.comment( 'a history details object should contain two objects named state_details and state_ids' );
    var states = [
            'discarded', 'empty', 'error', 'failed_metadata', 'new',
            'ok', 'paused', 'queued', 'running', 'setting_metadata', 'upload' ],
        state_details = historyShow.state_details,
        state_ids = historyShow.state_ids;
    this.test.assert( hasKeys( state_details, states ), 'state_details has the proper keys' );
    this.test.assert( hasKeys( state_ids, states ),     'state_ids has the proper keys' );
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

    // test server bad id protection
    this.test.comment( 'A bad id to show should throw an error' );
    this.assertRaises( function(){
        this.api.histories.show( '1234123412341234' );
    }, 'Error in history API at showing history detail: 400 Bad Request', 'Raises an exception' );


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
    this.test.assert( deletedHistory === 'OK',
        "Deletion returned 'OK' - even though that's not a great, informative response: " + deletedHistory );

    newFirstHistory = this.api.histories.index()[0];
    //this.debug( 'newFirstHistory:\n' + this.jsonStr( newFirstHistory ) );
    this.test.assert( newFirstHistory.id !== createdHistory.id,
        "Id of last history (from index) DOES NOT appear: " + newFirstHistory.id );

    this.test.comment( 'calling index with delete=true should include the deleted history' );
    newFirstHistory = this.api.histories.index( true )[0];
    //this.debug( 'newFirstHistory:\n' + this.jsonStr( newFirstHistory ) );
    this.test.assert( newFirstHistory.id === createdHistory.id,
        "Id of last history (from index) DOES appear using index( deleted=true ): " + newFirstHistory.id );


    // ------------------------------------------------------------------------------------------- UNDELETE
    this.test.comment( 'calling undelete should undelete the given history and re-include it in index' );
    var undeletedHistory = this.api.histories.undelete( createdHistory.id );
    //this.debug( 'returned from undelete:\n' + this.jsonStr( undeletedHistory ) );
    this.test.assert( undeletedHistory === 'OK',
        "Undeletion returned 'OK' - even though that's not a great, informative response: " + undeletedHistory );

    newFirstHistory = this.api.histories.index()[0];
    this.debug( 'newFirstHistory:\n' + this.jsonStr( newFirstHistory ) );
    this.test.assert( newFirstHistory.id === createdHistory.id,
        "Id of last history (from index) DOES appear after undeletion: " + newFirstHistory.id );


    //TODO: show, deleted flag
    //TODO: delete, purge flag
    // ------------------------------------------------------------------------------------------- UPDATE
    // ........................................................................................... idiot proofing
    this.test.comment( 'updating to the current value should return no value (no change)' );
    historyShow = this.api.histories.show( newFirstHistory.id );
    var returned = this.api.histories.update( newFirstHistory.id, {
        name : historyShow.name
    });
    this.test.assert( countKeys( returned ) === 0, "No changed returned: " + this.jsonStr( returned ) );

    this.test.comment( 'updating using a nonsense key should fail with an error' );
    var err = {};
    try {
        returned = this.api.histories.update( newFirstHistory.id, {
            konamiCode : 'uuddlrlrba'
        });
    } catch( error ){
        err = error;
        //this.debug( this.jsonStr( err ) );
    }
    this.test.assert( !!err.message, "Error occurred: " + err.message );
    this.test.assert( err.status === 400, "Error status is 400: " + err.status );

    this.test.comment( 'updating by attempting to change type should cause an error' );
    err = {};
    try {
        returned = this.api.histories.update( newFirstHistory.id, {
            //name : false
            deleted : 'sure why not'
        });
    } catch( error ){
        err = error;
        //this.debug( this.jsonStr( err ) );
    }
    this.test.assert( !!err.message, "Error occurred: " + err.message );
    this.test.assert( err.status === 400, "Error status is 400: " + err.status );
    //TODO??: other type checks?


    // ........................................................................................... name
    this.test.comment( 'update should allow changing the name' );
    returned = this.api.histories.update( newFirstHistory.id, {
        name : 'New name'
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id );
    this.test.assert( historyShow.name === 'New name', "Name successfully set via update: " + historyShow.name );

    this.test.comment( 'update should sanitize any new name' );
    returned = this.api.histories.update( newFirstHistory.id, {
        name : 'New name<script type="text/javascript" src="bler">alert("blah");</script>'
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id );
    this.test.assert( historyShow.name === 'New name', "Update sanitized name: " + historyShow.name );

    //NOTE!: this fails on sqlite3 (with default setup)
    try {
        this.test.comment( 'update should allow unicode in names' );
        var unicodeName = '桜ゲノム';
        returned = this.api.histories.update( newFirstHistory.id, {
            name : unicodeName
        });
        //this.debug( 'returned:\n' + this.jsonStr( returned ) );
        historyShow = this.api.histories.show( newFirstHistory.id );
        this.test.assert( historyShow.name === unicodeName, "Update accepted unicode name: " + historyShow.name );
    } catch( err ){
        //this.debug( this.jsonStr( err ) );
        if( ( err instanceof this.api.APIError )
        &&  ( err.status === 500 )
        &&  ( err.message.indexOf( '(ProgrammingError) You must not use 8-bit bytestrings' ) !== -1 ) ){
            this.skipTest( 'Unicode update failed. Are you using sqlite3 as the db?' );
        }
    }

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
    historyShow = this.api.histories.show( newFirstHistory.id );
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

    this.test.comment( 'update should sanitize any genome_build' );
    returned = this.api.histories.update( newFirstHistory.id, {
        genome_build : 'hg18<script type="text/javascript" src="bler">alert("blah");</script>'
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id );
    this.test.assert( historyShow.genome_build === 'hg18',
        "Update sanitized genome_build: " + historyShow.genome_build );

    this.test.comment( 'update should allow unicode in genome builds' );
    var unicodeBuild = '桜12';
    //NOTE!: this fails on sqlite3 (with default setup)
    try {
        returned = this.api.histories.update( newFirstHistory.id, {
            name : unicodeBuild
        });
        //this.debug( 'returned:\n' + this.jsonStr( returned ) );
        historyShow = this.api.histories.show( newFirstHistory.id );
        this.test.assert( historyShow.genome_build === unicodeBuild,
            "Update accepted unicode genome_build: " + historyShow.name );
    } catch( err ){
        //this.debug( this.jsonStr( err ) );
        if( ( err instanceof this.api.APIError )
        &&  ( err.status === 500 )
        &&  ( err.message.indexOf( '(ProgrammingError) You must not use 8-bit bytestrings' ) !== -1 ) ){
            this.skipTest( 'Unicode update failed. Are you using sqlite3 as the db?' );
        }
    }


    // ........................................................................................... annotation
    this.test.comment( 'update should allow changing the annotation' );
    var newAnnotation = 'Here are some notes that I stole from the person next to me';
    returned = this.api.histories.update( newFirstHistory.id, {
        annotation : newAnnotation
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id );
    this.test.assert( historyShow.annotation === newAnnotation,
        "Annotation successfully set via update: " + historyShow.annotation );

    this.test.comment( 'update should sanitize any new annotation' );
    returned = this.api.histories.update( newFirstHistory.id, {
        annotation : 'New annotation<script type="text/javascript" src="bler">alert("blah");</script>'
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    historyShow = this.api.histories.show( newFirstHistory.id );
    this.test.assert( historyShow.annotation === 'New annotation',
        "Update sanitized annotation: " + historyShow.annotation );

    //NOTE!: this fails on sqlite3 (with default setup)
    try {
        this.test.comment( 'update should allow unicode in annotations' );
        var unicodeAnnotation = 'お願いは、それが落下させない';
        returned = this.api.histories.update( newFirstHistory.id, {
            annotation : unicodeAnnotation
        });
        //this.debug( 'returned:\n' + this.jsonStr( returned ) );
        historyShow = this.api.histories.show( newFirstHistory.id );
        this.test.assert( historyShow.annotation === unicodeAnnotation,
            "Update accepted unicode annotation: " + historyShow.annotation );
    } catch( err ){
        //this.debug( this.jsonStr( err ) );
        if( ( err instanceof this.api.APIError )
        &&  ( err.status === 500 )
        &&  ( err.message.indexOf( '(ProgrammingError) You must not use 8-bit bytestrings' ) !== -1 ) ){
            this.skipTest( 'Unicode update failed. Are you using sqlite3 as the db?' );
        }
    }

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
    //TODO: make sure expected errors are being passed back (but no permissions checks here - different suite)
    // bad ids: index, show, update, delete, undelete

/*
*/
    //this.debug( this.jsonStr( historyShow ) );
});

// ===================================================================
spaceghost.run( function(){
});
