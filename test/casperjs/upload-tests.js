// have to handle errors here - or phantom/casper won't bail but _HANG_
try {
    var utils = require( 'utils' ),
        xpath = require( 'casper' ).selectXPath,
        format = utils.format,

        //...if there's a better way - please let me know, universe
        scriptDir = require( 'system' ).args[3]
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

    spaceghost.start();

} catch( error ){
    console.debug( error );
    phantom.exit( 1 );
}


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
spaceghost.user.loginOrRegisterUser( email, password );
//??: why is a reload needed here? If we don't, loggedInAs === '' ...
spaceghost.thenOpen( spaceghost.baseUrl, function(){
    var loggedInAs = spaceghost.user.loggedInAs();
    this.test.assert( loggedInAs === email, 'loggedInAs() matches email: "' + loggedInAs + '"' );
});


// ------------------------------------------------------------------- long form

// upload a file...
spaceghost.then( function(){
    this.test.comment( 'Test uploading a file' );

    var filename = '1.txt',
        filepath = this.options.scriptDir + '/../../test-data/' + filename;

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
spaceghost.historypanel.waitForHdas( function(){
    this.test.comment( 'Waiting for upload to move to ok state in history' );

    var hdaInfo = this.historypanel.hdaElementInfoByTitle( testUploadInfo.name );
    if( !hdaInfo ){
        this.test.fail( 'Could not locate new hda: ' + testUploadInfo.name );

    } else {
        this.historypanel.waitForHdaState( '#' + hdaInfo.attributes.id, 'ok',
            function whenInStateFn( newHdaInfo ){
                //this.debug( 'newHdaInfo:\n' + this.jsonStr( newHdaInfo ) );
                this.test.pass( 'Upload completed successfully for: ' + testUploadInfo.name );
            },
            function timeoutFn( newHdaInfo ){
                this.debug( 'newHdaInfo:\n' + this.jsonStr( newHdaInfo ) );
                this.test.fail( 'Test timed out for upload: ' + testUploadInfo.name );
            },
            // wait a maximum of 30 secs
            30 * 1000 );
    }
});

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
spaceghost.run( function(){
    this.test.done();
});
