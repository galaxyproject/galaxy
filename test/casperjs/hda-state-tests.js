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
    currently going to fake states via JS
        - better if we can capture actual hdas in these states
        - easier said than done - API?
*/
// =================================================================== globals and helpers
var email = spaceghost.user.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
    spaceghost.info( 'Will use fixtureData.testUser: ' + email );
}

var newHistoryName = "Test History",
    historyFrameInfo = {},
    filepathToUpload = '../../test-data/1.txt',
    possibleHDAStates = [],
    testUploadInfo = {};

// ------------------------------------------------------------------- set up
// start a new user
spaceghost.user.loginOrRegisterUser( email, password );
// ??: why is a reload needed here? If we don't, loggedInAs === '' ...
spaceghost.thenOpen( spaceghost.baseUrl, function(){
    var loggedInAs = spaceghost.user.loggedInAs();
    this.test.assert( loggedInAs === email, 'loggedInAs() matches email: "' + loggedInAs + '"' );
});

// grab the history frame bounds for mouse later tests
spaceghost.then( function(){
    historyFrameInfo = this.getElementInfo( 'iframe[name="galaxy_history"]' );
    //this.debug( 'historyFrameInfo:' + this.jsonStr( historyFrameInfo ) );
});

// upload a file
spaceghost.then( function upload(){
    spaceghost.tools.uploadFile( filepathToUpload, function uploadCallback( _uploadInfo ){
        testUploadInfo = _uploadInfo;
        this.info( 'testUploadInfo:' + this.jsonStr( testUploadInfo ) );
    });
});

spaceghost.then( function getHDAStates(){
    this.withFrame( this.selectors.frames.history, function(){
        var model = this.evaluate( function(){
            return Galaxy.currHistoryPanel.model.hdas.at( 0 ).attributes;
        });
        this.info( 'model:' + this.jsonStr( model ) );
    });
});

spaceghost.then( function checkNewState(){
    this.test.comment( 'HDAs in the "new" state should be well formed' );

    this.withFrame( this.selectors.frames.history, function(){
        // set state directly through model
        //TODO: not ideal
        this.evaluate( function(){
            return Galaxy.currHistoryPanel.model.hdas.at( 0 ).set( 'state', 'new' );
        });
        // wait for re-render
        this.wait( 500, function(){
            var uploadSelector = '#' + testUploadInfo.hdaElement.attributes.id;
            this.test.assertVisible( uploadSelector, 'HDA is visible' );

            // should have proper title and hid
            var titleSelector = uploadSelector + ' .historyItemTitle';
            this.test.assertVisible( titleSelector, 'HDA title is visible' );
            this.test.assertSelectorHasText( titleSelector, testUploadInfo.name,
                'HDA has proper title' );
            this.test.assertSelectorHasText( titleSelector, testUploadInfo.hid,
                'HDA has proper hid' );

            // should have the new state class
            var newStateClass = 'historyItem-new',
                uploadElement = this.getElementInfo( uploadSelector );
            this.test.assert( uploadElement.attributes['class'].indexOf( newStateClass ) !== -1,
                'HDA has new state class' );

            // since we're using css there's no great way to test this
            //var stateIconSelector = uploadSelector + ' .state-icon';
            //this.test.assertVisible( stateIconSelector, 'HDA has proper hid' );

            // should NOT have any of the three, main buttons
            var buttonSelector = uploadSelector + ' .historyItemButtons a';
            this.test.assertDoesntExist( buttonSelector, 'No display, edit, or delete buttons' );

            // expand and check the body
            this.click( titleSelector );
            this.wait( 500, function(){
                var bodySelector = uploadSelector + ' .historyItemBody';
                this.test.assertVisible( bodySelector, 'HDA body is visible (after expanding)' );

                var expectedBodyText = 'This is a new dataset';
                this.test.assertSelectorHasText( bodySelector, expectedBodyText,
                    'HDA body has text: ' + expectedBodyText );

                // restore to collapsed
                this.click( titleSelector );
            });
        });
    });
});

// =================================================================== TESTS


// ===================================================================
spaceghost.run( function(){
    this.test.done();
});
