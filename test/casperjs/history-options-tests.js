var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Testing the history options menu', 0, function suite( test ){
    spaceghost.start();
    // ===================================================================

    var email = spaceghost.user.getRandomEmail(),
        password = '123456';
    if( spaceghost.fixtureData.testUser ){
        email = spaceghost.fixtureData.testUser.email;
        password = spaceghost.fixtureData.testUser.password;
        spaceghost.info( 'Will use fixtureData.testUser: ' + email );
    }

    var includeDeletedOptionsLabel = spaceghost.historyoptions.data.labels.options.includeDeleted,
        filepathToUpload = '../../test-data/1.txt',
        uploadId = null;

    // ------------------------------------------------------------------- set up
    // start a new user and upload a file
    spaceghost.user.loginOrRegisterUser( email, password );
    spaceghost.api.tools.thenUploadToCurrent({ filepath: filepathToUpload }, function uploadCallback( id, json ){
        uploadId = id;
    });

    // ------------------------------------------------------------------- history options menu structure
    //NOTE: options menu should be functionally tested elsewhere
    spaceghost.openHomePage().historypanel.waitForHdas().then( function checkHistoryOptions(){
        this.test.comment( 'History options icon should be in place and menu should have the proper structure' );

        // check the button and icon
        this.test.assertExists(  this.historyoptions.data.selectors.button, "Found history options button" );
        this.test.assertVisible( this.historyoptions.data.selectors.button, "History options button is visible" );
        this.test.assertVisible( this.historyoptions.data.selectors.buttonIcon, "History options icon is visible" );

        // open the menu
        this.click( this.historyoptions.data.selectors.button );
        this.test.assertVisible( this.historyoptions.data.selectors.menu,
            "Menu is visible when options button is clicked" );

        // check the options
        var historyOptions = this.historyoptions.data.labels.options;
        for( var optionKey in historyOptions ){
            if( historyOptions.hasOwnProperty( optionKey ) ){
                var optionLabel = historyOptions[ optionKey ];
                this.test.assertVisible( this.historyoptions.data.selectors.optionXpathByLabelFn( optionLabel ),
                    'Option label is visible: ' + optionLabel );
            }
        }

        // clear the menu
        this.click( 'body' );
        this.test.assertNotVisible( this.historyoptions.data.selectors.menu,
            "Clicking away from the menu closes it" );
    });

    // ------------------------------------------------------------------- history options collapses all expanded hdas
    spaceghost.then( function(){
        this.historypanel.thenExpandHda( '#dataset-' + uploadId );
    });
    spaceghost.then( function(){
        this.test.comment( 'History option collapses all expanded hdas' );

        this.historyoptions.collapseExpanded( function(){
            var uploadedSelector = '#dataset-' + uploadId;
            this.test.assertNotVisible( uploadedSelector + ' ' + this.historypanel.data.selectors.hda.body,
                "Body for uploaded file is not visible" );
        });
    });

    // ===================================================================
    spaceghost.run( function(){ test.done(); });
});
