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

var uploadFilename = '1.sam',
    uploadFilepath = '../../test-data/' + uploadFilename,
    upload = {};
spaceghost.thenOpen( spaceghost.baseUrl ).tools.uploadFile( uploadFilepath, function( uploadInfo ){
    upload = uploadInfo;
});

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
var summaryKeys = [ 'id', 'name', 'type', 'url' ],
    detailKeys  = [
        // the following are always present regardless of datatype
        'id', 'name', 'api_type', 'model_class',
        'history_id', 'hid',
        'accessible', 'deleted', 'visible', 'purged',
        'state', 'data_type', 'file_ext', 'file_size',
        'misc_info', 'misc_blurb',
        'download_url', 'visualizations', 'display_apps', 'display_types',
        'genome_build',
        // the following are NOT always present DEPENDING ON datatype
        'metadata_dbkey',
        'metadata_column_names', 'metadata_column_types', 'metadata_columns',
        'metadata_comment_lines', 'metadata_data_lines'
    ];

spaceghost.historypanel.waitForHdas().then( function(){
    
    var uploaded = this.historypanel.hdaElementInfoByTitle( uploadFilename );
    this.info( 'found uploaded hda: ' + uploaded.attributes.id );
    this.debug( 'uploaded hda: ' + this.jsonStr( uploaded ) );
    // ------------------------------------------------------------------------------------------- INDEX
    this.test.comment( 'index should return a list of summary data for each hda' );
    var histories = this.api.histories.index(),
        lastHistory = histories[0],
        hdaIndex = this.api.hdas.index( lastHistory.id );
    //this.debug( 'hdaIndex:' + this.jsonStr( hdaIndex ) );

    this.test.assert( utils.isArray( hdaIndex ), "index returned an array: length " + hdaIndex.length );
    this.test.assert( hdaIndex.length >= 1, 'Has at least one hda' );

    var firstHda = hdaIndex[0];
    this.test.assert( hasKeys( firstHda, summaryKeys ), 'Has the proper keys' );

    this.test.assert( this.api.isEncodedId( firstHda.id ), 'Id appears well-formed: ' + firstHda.id );
    this.test.assert( uploaded.text.indexOf( firstHda.name ) !== -1, 'Title matches: ' + firstHda.name );
    // not caring about type or url here


    // ------------------------------------------------------------------------------------------- SHOW
    this.test.comment( 'show should get an HDA details object' );
    var hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    //this.debug( this.jsonStr( hdaShow ) );
    this.test.assert( hasKeys( hdaShow, detailKeys ), 'Has the proper keys' );

    //TODO: validate data in each hdaShow attribute...


    // ------------------------------------------------------------------------------------------- INDEX (detailed)
    this.test.comment( 'index should return a list of detailed data for each hda in "ids" when passed' );
    hdaIndex = this.api.hdas.index( lastHistory.id, [ firstHda.id ] );
    this.debug( 'hdaIndex:' + this.jsonStr( hdaIndex ) );

    this.test.assert( utils.isArray( hdaIndex ), "index returned an array: length " + hdaIndex.length );
    this.test.assert( hdaIndex.length >= 1, 'Has at least one hda' );

    firstHda = hdaIndex[0];
    this.test.assert( hasKeys( firstHda, detailKeys ), 'Has the proper keys' );

    //TODO??: validate data in firstHda attribute? we ASSUME it's from a common method as show...


    // ------------------------------------------------------------------------------------------- CREATE
    //TODO: create from_ld_id


    // ------------------------------------------------------------------------------------------- UPDATE
    // ........................................................................................... idiot proofing
    this.test.comment( 'updating to the current value should return no value (no change)' );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    var returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        name : hdaShow.name
    });
    this.test.assert( countKeys( returned ) === 0, "No changed returned: " + this.jsonStr( returned ) );

    this.test.comment( 'updating using a nonsense key should fail with an error' );
    var err = {};
    try {
        returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
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
        returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
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
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        name : 'New name'
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.name === 'New name', "Name successfully set via update: " + hdaShow.name );

    this.test.comment( 'update should sanitize any new name' );
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        name : 'New name<script type="text/javascript" src="bler">alert("blah");</script>'
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.name === 'New name', "Update sanitized name: " + hdaShow.name );

    //NOTE!: this fails on sqlite3 (with default setup)
    try {
        this.test.comment( 'update should allow unicode in names' );
        var unicodeName = 'Ржевский сапоги';
        returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
            name : unicodeName
        });
        //this.debug( 'returned:\n' + this.jsonStr( returned ) );
        hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
        this.test.assert( hdaShow.name === unicodeName, "Update accepted unicode name: " + hdaShow.name );
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
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        name : quotedName
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.name === quotedName,
        "Update accepted escaped quotations in name: " + hdaShow.name );


    // ........................................................................................... deleted
    this.test.comment( 'update should allow changing the deleted flag' );
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        deleted: true
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.deleted === true, "Update set the deleted flag: " + hdaShow.deleted );

    this.test.comment( 'update should allow changing the deleted flag back' );
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        deleted: false
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.deleted === false, "Update set the deleted flag: " + hdaShow.deleted );


    // ........................................................................................... visible/hidden
    this.test.comment( 'update should allow changing the visible flag' );
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        visible: false
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.visible === false, "Update set the visible flag: " + hdaShow.visible );


    // ........................................................................................... genome_build/dbkey
    this.test.comment( 'update should allow changing the genome_build' );
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        genome_build : 'hg18'
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.genome_build === 'hg18',
        "genome_build successfully set via update: " + hdaShow.genome_build );
    this.test.assert( hdaShow.metadata_dbkey === 'hg18',
        "metadata_dbkey successfully set via the same update: " + hdaShow.metadata_dbkey );

    this.test.comment( 'update should sanitize any genome_build' );
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        genome_build : 'hg18<script type="text/javascript" src="bler">alert("blah");</script>'
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.genome_build === 'hg18',
        "Update sanitized genome_build: " + hdaShow.genome_build );
    this.test.assert( hdaShow.metadata_dbkey === 'hg18',
        "metadata_dbkey successfully set via the same update: " + hdaShow.metadata_dbkey );

    this.test.comment( 'update should allow unicode in genome builds' );
    var unicodeBuild = 'Ржевский18';
    //NOTE!: this fails on sqlite3 (with default setup)
    try {
        returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
            name : unicodeBuild
        });
        //this.debug( 'returned:\n' + this.jsonStr( returned ) );
        hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
        this.test.assert( hdaShow.genome_build === unicodeBuild,
            "Update accepted unicode genome_build: " + hdaShow.name );
    } catch( err ){
        //this.debug( this.jsonStr( err ) );
        if( ( err instanceof this.api.APIError )
        &&  ( err.status === 500 )
        &&  ( err.message.indexOf( '(ProgrammingError) You must not use 8-bit bytestrings' ) !== -1 ) ){
            this.skipTest( 'Unicode update failed. Are you using sqlite3 as the db?' );
        }
    }

    // ........................................................................................... misc_info/info
    this.test.comment( 'update should allow changing the misc_info' );
    var newInfo = 'I\'ve made a huge mistake.';
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        misc_info : newInfo
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.misc_info === newInfo,
        "misc_info successfully set via update: " + hdaShow.misc_info );

    this.test.comment( 'update should sanitize any misc_info' );
    var newInfo = 'You\'re going to get hop-ons.';
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        misc_info : newInfo + '<script type="text/javascript" src="bler">alert("blah");</script>'
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.misc_info === newInfo,
        "Update sanitized misc_info: " + hdaShow.misc_info );

    this.test.comment( 'update should allow unicode in misc_info' );
    var unicodeInfo = '여보!';
    //NOTE!: this fails on sqlite3 (with default setup)
    try {
        returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
            misc_info : unicodeInfo
        });
        //this.debug( 'returned:\n' + this.jsonStr( returned ) );
        hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
        this.test.assert( hdaShow.misc_info === unicodeInfo,
            "Update accepted unicode misc_info: " + hdaShow.misc_info );
    } catch( err ){
        //this.debug( this.jsonStr( err ) );
        if( ( err instanceof this.api.APIError )
        &&  ( err.status === 500 )
        &&  ( err.message.indexOf( '(ProgrammingError) You must not use 8-bit bytestrings' ) !== -1 ) ){
            this.skipTest( 'Unicode update failed. Are you using sqlite3 as the db?' );
        }
    }

/*
    // ........................................................................................... annotation
    // currently fails because no annotation is returned in details
    this.test.comment( 'update should allow changing the annotation' );
    var newAnnotation = 'Found this sample on a movie theatre floor';
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        annotation : newAnnotation
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.annotation === newAnnotation,
        "Annotation successfully set via update: " + hdaShow.annotation );

    this.test.comment( 'update should sanitize any new annotation' );
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        annotation : 'New annotation<script type="text/javascript" src="bler">alert("blah");</script>'
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.annotation === 'New annotation',
        "Update sanitized annotation: " + hdaShow.annotation );

    //NOTE!: this fails on sqlite3 (with default setup)
    try {
        this.test.comment( 'update should allow unicode in annotations' );
        var unicodeAnnotation = 'お願いは、それが落下させない';
        returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
            annotation : unicodeAnnotation
        });
        //this.debug( 'returned:\n' + this.jsonStr( returned ) );
        hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
        this.test.assert( hdaShow.annotation === unicodeAnnotation,
            "Update accepted unicode annotation: " + hdaShow.annotation );
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
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        annotation : quotedAnnotation
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.annotation === quotedAnnotation,
        "Update accepted escaped quotations in annotation: " + hdaShow.annotation );
*/


    // ------------------------------------------------------------------------------------------- ERRORS
    this.test.comment( 'create should error with "not implemented" when the param "from_ld_id" is not used' );
    var errored = false;
    try {
        // sending an empty object won't work
        var created = this.api.hdas.create( lastHistory.id, { bler: 'bler' } );

    } catch( err ){
        errored = true;
        this.test.assert( err.message.indexOf( 'Not implemented' ) !== -1,
            'Error has the proper message: ' + err.message );
        this.test.assert( err.status === 501, 'Error has the proper status code: ' + err.status );
    }
    if( !errored ){
        this.test.fail( 'create without "from_ld_id" did not cause error' );
    }


    //var returned = this.api.hdas.update( lastHistory.id, hdaIndex[0].id, { deleted: true, blerp: 'blerp' });
    //var returned = this.api.hdas.update( lastHistory.id, { deleted: true, blerp: 'blerp' });
    //this.debug( 'returned:' + this.jsonStr( returned ) );
    //this.debug( 'page:' + this.jsonStr( this.page ) );
});

// ===================================================================
spaceghost.run( function(){
});
