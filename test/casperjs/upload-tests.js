var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Test uploading data to a history', 0, function suite( test ){
    spaceghost.start();

// ===================================================================
/* TODO:

    find a way to error on bad upload?
    general tool execution
*/
// =================================================================== globals and helpers
var email = spaceghost.user.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
}

var testUploadInfo = {};

// =================================================================== TESTS
// ------------------------------------------------------------------- start a new user
spaceghost.user.loginOrRegisterUser( email, password ).openHomePage( function(){
    var loggedInAs = spaceghost.user.loggedInAs();
    this.test.assert( loggedInAs === email, 'loggedInAs() matches email: "' + loggedInAs + '"' );
});

// ------------------------------------------------------------------- long form
// upload a file...
spaceghost.then( function(){
    this.test.comment( 'Test uploading a file' );

    var filename = '1.txt',
        filepath = '../../test-data/' + filename;
    this.tools._uploadFile( filepath );

    // when an upload begins successfully main should reload with a infomessagelarge
    this.withMainPanel( function mainAfterUpload(){
        var infoInfo = this.elementInfoOrNull( this.data.selectors.messages.infolarge );
        this.test.assert( infoInfo !== null,
            "Found infomessagelarge after uploading file" );
        this.test.assert( infoInfo.text.indexOf( this.data.text.upload.success ) !== -1,
            "Found upload success message: " + this.data.text.upload.success );

        testUploadInfo.name = filename;
    });
});

// ... and move to the history panel and wait for upload to finish
spaceghost.historypanel.waitForHda( '1.txt',
    function uploadComplete( hdaElement ){
        this.test.pass( 'Upload completed successfully for: ' + this.jsonStr( hdaElement.attributes.id ) );
    },
    function timeout( hdaElement ){
        this.debug( 'hdaElement:\n' + this.jsonStr( hdaElement ) );
        this.test.fail( 'Test timed out for upload: ' + testUploadInfo.name );
    },
    30 * 1000
);

// ------------------------------------------------------------------- short form
spaceghost.then( function(){
    this.test.comment( 'Test convenience function' );

    spaceghost.tools.uploadFile( '../../test-data/1.sam', function( uploadInfo ){
        this.test.assert( uploadInfo.hdaElement !== null, "Convenience function produced hda" );
        var state = this.historypanel.getHdaState( '#' + uploadInfo.hdaElement.attributes.id );
        this.test.assert( state === 'ok', "Convenience function produced hda in ok state" );
    });
});

// ------------------------------------------------------------------- test conv. fn error
/*
//??: this error's AND waitFor()s THREE times (or more) - something to do with assertStepsRaise + waitFor
spaceghost.then( function(){
    this.test.comment( 'testing convenience function timeout error' );
    this.assertStepsRaise( 'GalaxyError: Upload Error: timeout waiting', function(){
        spaceghost.tools.uploadFile( '../../test-data/1.sam', function( uploadInfo ){
            this.test.fail( "Convenience function did not timeout!" );
        }, 50 );
    });
});
*/

// ===================================================================
    spaceghost.run( function(){ test.done(); });
});
