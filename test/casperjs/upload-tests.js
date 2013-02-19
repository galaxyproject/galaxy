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


// =================================================================== TESTS
// ------------------------------------------------------------------- start a new user
spaceghost.user.loginOrRegisterUser( email, password );
//??: why is a reload needed here? If we don't, loggedInAs === '' ...
spaceghost.thenOpen( spaceghost.baseUrl, function(){
    var loggedInAs = spaceghost.user.loggedInAs();
    this.test.assert( loggedInAs === email, 'loggedInAs() matches email: "' + loggedInAs + '"' );
});


// ------------------------------------------------------------------- long form
// upload a file from the filesystem
var uploadInfo = {};
spaceghost.then( function(){
    // strangely, this works with a non-existant file --> empty txt file
    var filename = '1.sam';
    var filepath = this.options.scriptDir + '/../../test-data/' + filename;
    this.tools._uploadFile( filepath );

    // when an upload begins successfully...
    // 1. main should reload with a donemessagelarge
    // 2. which contains the uploaded file's new hid
    // 3. and the filename of the upload
    this.withFrame( 'galaxy_main', function(){
        var doneElementInfo = this.elementInfoOrNull( '.donemessagelarge' );
        this.test.assert( doneElementInfo !== null,
            "Found donemessagelarge after uploading file" );

        uploadInfo = this.tools._parseDoneMessageForTool( doneElementInfo.text );
        this.test.assert( uploadInfo.hid >= 0,
            'Found sensible hid from upload donemessagelarge: ' + uploadInfo.hid );
        this.test.assert( uploadInfo.name === filename,
            'Found matching name from upload donemessagelarge: ' + uploadInfo.name );
    });

});

// move to the history panel and wait for upload to finish
spaceghost.then( function(){
    var hdaInfo = null;

    this.withFrame( 'galaxy_history', function(){
        hdaInfo = this.historypanel.hdaElementInfoByTitle( uploadInfo.name, uploadInfo.hid );
        this.debug( 'hda:\n' + this.jsonStr( hdaInfo ) );
    });

    this.then( function(){
        this.test.comment( 'Waiting for upload to move to ok state in history' );
        //precondition: needs class
        var hdaStateClass = hdaInfo.attributes[ 'class' ].match( /historyItem\-(\w+)/ )[0];
        if( hdaStateClass !== 'historyItem-ok' ){
            this.historypanel.waitForHdaState( '#' + hdaInfo.attributes.id, 'ok',
                function whenInStateFn(){
                    this.test.assert( true, 'Upload completed successfully for: ' + uploadInfo.name );

                }, function timeoutFn(){
                    this.test.fail( 'Test timedout for upload: ' + uploadInfo.name );

                // wait a maximum of 30 secs
                }, 30 * 1000 );
        }
    });
});

spaceghost.then( function(){
    this.test.comment( 'testing convenience function' );
    spaceghost.tools.uploadFile( '../../test-data/1.sam', function( uploadInfo ){
        this.test.assert( uploadInfo.hdaElement !== null, "Convenience function produced hda in ok state" );
    });
});

/*
//??: this error's AND waitFor()s THREE times - something to do with assertStepsRaise + waitFor
spaceghost.then( function(){
    this.test.comment( 'testing convenience function timeout error' );
    this.assertStepsRaise( 'GalaxyError: Upload Error: timeout waiting', function(){
        spaceghost.then( function(){
            spaceghost.tools.uploadFile( '../../test-data/1.sam', function( uploadInfo ){
                this.test.fail( "Convenience function did not timeout!" );
            }, 250 );
        });
    });
});

// this correctly errors
spaceghost.then( function(){
    spaceghost.tools.uploadFile( '../../test-data/1.sam', function( uploadInfo ){
        this.test.fail( "Convenience function did not timeout!" );
    }, 250 );
});
*/

// ===================================================================
spaceghost.run( function(){
    this.test.done();
});
