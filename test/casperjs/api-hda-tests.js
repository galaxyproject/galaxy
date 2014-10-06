var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Test the HDA API', 0, function suite( test ){
    spaceghost.start();

// =================================================================== SET UP
var email = spaceghost.user.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
}
spaceghost.user.loginOrRegisterUser( email, password );

spaceghost.thenOpen( spaceghost.baseUrl, function(){
    this.test.comment( '(logged in as ' + this.user.loggedInAs() + ')' );
    this.api.tools.thenUpload( spaceghost.api.histories.index()[0].id, {
        filepath: '../../test-data/1.sam'
    });
});

// =================================================================== TESTS
var summaryKeys = [ 'id', 'name', 'history_id', 'state', 'deleted', 'purged', 'visible', 'url', 'type' ],
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

// ------------------------------------------------------------------------------------------- logged in user
spaceghost.then( function(){
    
    // ------------------------------------------------------------------------------------------- INDEX
    this.test.comment( 'index should return a list of summary data for each hda' );
    var histories = this.api.histories.index(),
        lastHistory = histories[0],
        hdaIndex = this.api.hdas.index( lastHistory.id );
    //this.debug( 'hdaIndex:' + this.jsonStr( hdaIndex ) );

    this.test.assert( utils.isArray( hdaIndex ), "index returned an array: length " + hdaIndex.length );
    this.test.assert( hdaIndex.length >= 1, 'Has at least one hda' );

    var firstHda = hdaIndex[0];
    this.test.assert( this.hasKeys( firstHda, summaryKeys ), 'Has the proper keys' );

    this.test.assert( this.api.isEncodedId( firstHda.id ), 'Id appears well-formed: ' + firstHda.id );
    this.test.assert( firstHda.name === '1.sam', 'Title matches: ' + firstHda.name );


    // ------------------------------------------------------------------------------------------- SHOW
    this.test.comment( 'show should get an HDA details object' );
    var hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    //this.debug( this.jsonStr( hdaShow ) );
    this.test.assert( this.hasKeys( hdaShow, detailKeys ), 'Has the proper keys' );

    //TODO: validate data in each hdaShow attribute...


    // ------------------------------------------------------------------------------------------- INDEX (detailed)
    this.test.comment( 'index should return a list of detailed data for each hda in "ids" when passed' );
    hdaIndex = this.api.hdas.index( lastHistory.id, [ firstHda.id ] );
    this.debug( 'hdaIndex:' + this.jsonStr( hdaIndex ) );

    this.test.assert( utils.isArray( hdaIndex ), "index returned an array: length " + hdaIndex.length );
    this.test.assert( hdaIndex.length >= 1, 'Has at least one hda' );

    firstHda = hdaIndex[0];
    this.test.assert( this.hasKeys( firstHda, detailKeys ), 'Has the proper keys' );

    //TODO??: validate data in firstHda attribute? we ASSUME it's from a common method as show...


    // ------------------------------------------------------------------------------------------- CREATE
    //TODO: create from_ld_id
    this.test.comment( 'create should allow copying an accessible hda' );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    var returned = this.api.hdas.create( lastHistory.id, {
        source  : 'hda',
        content : hdaShow.id
    });
    //this.debug( 'returned:' + this.jsonStr( returned ) );
    this.test.assert( this.hasKeys( returned, detailKeys ), 'Has the proper keys' );
    this.test.assert( typeof returned.id !== 'number' && isNaN( Number( returned.id ) ),
        'id seems to be encoded: ' + returned.id );
    this.test.assert( typeof returned.history_id !== 'number' && isNaN( Number( returned.history_id ) ),
        'history_id seems to be encoded: ' + returned.history_id );


    // ------------------------------------------------------------------------------------------- UPDATE
    // ........................................................................................... idiot proofing
    this.test.comment( 'updating to the current value should return no value (no change)' );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    var returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        name : hdaShow.name
    });
    this.test.assert( this.countKeys( returned ) === 0, "No changed returned: " + this.jsonStr( returned ) );

    this.test.comment( 'updating using a nonsense key should NOT fail with an error' );
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        konamiCode : 'uuddlrlrba'
    });
    this.test.assert( this.countKeys( returned ) === 0, "No changed returned: " + this.jsonStr( returned ) );

    this.test.comment( 'updating by attempting to change type should cause an error' );
    this.api.assertRaises( function(){
        returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
            //name : false
            deleted : 'sure why not'
        });
    }, 400, 'deleted must be a boolean', 'changing deleted type failed' );

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

    this.test.comment( 'update should allow unicode in names' );
    var unicodeName = 'Ржевский сапоги';
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        name : unicodeName
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.name === unicodeName, "Update accepted unicode name: " + hdaShow.name );

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
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id, true );
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
    //this.debug( 'hdaShow:\n' + this.jsonStr( hdaShow ) );
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
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        genome_build : unicodeBuild
    });
    this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.debug( 'hdaShow:\n' + this.jsonStr( hdaShow ) );
    this.test.assert( hdaShow.genome_build === unicodeBuild,
        "Update accepted unicode genome_build: " + hdaShow.genome_build );

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
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        misc_info : unicodeInfo
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.misc_info === unicodeInfo,
        "Update accepted unicode misc_info: " + hdaShow.misc_info );

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

    this.test.comment( 'update should allow unicode in annotations' );
    var unicodeAnnotation = 'お願いは、それが落下させない';
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        annotation : unicodeAnnotation
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.annotation === unicodeAnnotation,
        "Update accepted unicode annotation: " + hdaShow.annotation );

    this.test.comment( 'update should allow escaped quotations in annotations' );
    var quotedAnnotation = '"Bler"';
    returned = this.api.hdas.update( lastHistory.id, firstHda.id, {
        annotation : quotedAnnotation
    });
    //this.debug( 'returned:\n' + this.jsonStr( returned ) );
    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.annotation === quotedAnnotation,
        "Update accepted escaped quotations in annotation: " + hdaShow.annotation );

    // ------------------------------------------------------------------------------------------- ERRORS
    this.test.comment( 'create should error with "Please define the source" when the param "from_ld_id" is not used' );
    this.api.assertRaises( function(){
        this.api.hdas.create( lastHistory.id, { bler: 'bler' } );
    }, 400, "must be either 'library' or 'hda'", 'create with no source failed' );

    this.test.comment( 'updating using a nonsense key should fail silently' );
    returned = this.api.hdas.update( lastHistory.id, hdaShow.id, {
        konamiCode : 'uuddlrlrba'
    });
    this.test.assert( returned.konamiCode === undefined, 'key was not set: ' + returned.konamiCode );

    spaceghost.test.comment( 'A bad id should throw an error when using show' );
    this.api.assertRaises( function(){
        this.api.hdas.show( lastHistory.id, '1234123412341234' );
    }, 400, 'unable to decode', 'Bad Request with invalid id: show' );
    spaceghost.test.comment( 'A bad id should throw an error when using update' );
    this.api.assertRaises( function(){
        this.api.hdas.update( lastHistory.id, '1234123412341234', {} );
    }, 400, 'unable to decode', 'Bad Request with invalid id: update' );
    spaceghost.test.comment( 'A bad id should throw an error when using delete' );
    this.api.assertRaises( function(){
        this.api.hdas.delete_( lastHistory.id, '1234123412341234' );
    }, 400, 'unable to decode', 'Bad Request with invalid id: delete' );
    spaceghost.test.comment( 'A bad id should throw an error when using undelete' );

    this.test.comment( 'updating by attempting to change type should cause an error' );
    [ 'name', 'annotation', 'genome_build', 'misc_info' ].forEach( function( key ){
        var updatedAttrs = {};
        updatedAttrs[ key ] = false;
        spaceghost.api.assertRaises( function(){
            returned = spaceghost.api.hdas.update( hdaShow.history_id, hdaShow.id, updatedAttrs );
        }, 400, key + ' must be a string or unicode', 'type validation error' );
    });
    [ 'deleted', 'visible' ].forEach( function( key ){
        var updatedAttrs = {};
        updatedAttrs[ key ] = 'straaang';
        spaceghost.api.assertRaises( function(){
            returned = spaceghost.api.hdas.update( hdaShow.history_id, hdaShow.id, updatedAttrs );
        }, 400, key + ' must be a boolean', 'type validation error' );
    });
    [ 'you\'re it', [ true ] ].forEach( function( badVal ){
        spaceghost.api.assertRaises( function(){
            returned = spaceghost.api.hdas.update( hdaShow.history_id, hdaShow.id, { tags: badVal });
        }, 400, 'tags must be a list', 'type validation error' );
    });

    // ------------------------------------------------------------------------------------------- DELETE
    this.test.comment( 'calling delete on an hda should mark it as deleted but not change the history size' );
    lastHistory = this.api.histories.show( lastHistory.id );
    var sizeBeforeDelete = lastHistory.nice_size;

    returned = this.api.hdas.delete_( lastHistory.id, firstHda.id );
    //this.debug( this.jsonStr( returned ) );

    hdaShow = this.api.hdas.show( lastHistory.id, firstHda.id );
    this.test.assert( hdaShow.deleted, 'hda is marked deleted' );
    lastHistory = this.api.histories.show( lastHistory.id );
    this.test.assert( lastHistory.nice_size === sizeBeforeDelete, 'history size has not changed' );

    // by default, purging fails bc uni.ini:allow_user_dataset_purge=False
    this.api.assertRaises( function(){
        returned = this.api.hdas.delete_( lastHistory.id, firstHda.id, { purge : true });
    }, 403, 'This instance does not allow user dataset purging', 'Purge failed' );
/*
*/
});
//spaceghost.user.logout();


// ===================================================================
    spaceghost.run( function(){ test.done(); });
});

