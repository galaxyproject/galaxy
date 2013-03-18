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

var tooltipSelector = spaceghost.data.selectors.tooltipBalloon;

var utils = require( 'utils' ),
    historyFrameInfo = {},
    filepathToUpload = '../../test-data/1.txt',
    testUploadInfo = {},
    //TODO: get from the api module - that doesn't exist yet
    summaryShouldBeArray = [ '10 lines', 'format: txt' ],
    infoShouldBe = 'uploaded txt file',
    peekShouldBeArray = [];

// ------------------------------------------------------------------- set up
// start a new user
spaceghost.user.loginOrRegisterUser( email, password );

// grab the history frame bounds for later mouse tests
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


// =================================================================== TEST HELPERS
//NOTE: to be called with fn.call( spaceghost, ... )

function testTitle( hdaSelector, hid, name ){
    var titleSelector = hdaSelector + ' ' + this.historypanel.data.selectors.hda.title,
        titleShouldBe = hid + ': ' + name;
    this.test.assertVisible( titleSelector,
        'HDA title is visible' );
    this.test.assertSelectorHasText( titleSelector, titleShouldBe,
        'HDA has proper hid and title' );
}

function testTitleButtonStructure( hdaSelector, shouldHaveTheseButtons ){
    // defaults to the current buttons most states should have
    shouldHaveTheseButtons = shouldHaveTheseButtons || [ 'display', 'edit', 'delete' ];

    var hdaDbId = this.getElementAttribute( hdaSelector, 'id' ).split( '-' )[1],
        buttonsArea = hdaSelector + ' ' + this.historypanel.data.selectors.hda.titleButtons,
        buttons = {
            // this seems backwards -> TODO: move buttonsArea concat into loop below, move this data to historypanel.data
            display : {
                nodeName : this.historypanel.data.text.hda.ok.nodeNames.displayButton,
                selector : buttonsArea + ' ' + this.historypanel.data.selectors.hda.displayButton,
                tooltip  : this.historypanel.data.text.hda.ok.tooltips.displayButton,
                hrefTpl  : this.historypanel.data.text.hda.ok.hrefs.displayButton
            },
            edit : {
                nodeName : this.historypanel.data.text.hda.ok.nodeNames.editAttrButton,
                selector : buttonsArea + ' ' + this.historypanel.data.selectors.hda.editAttrButton,
                tooltip  : this.historypanel.data.text.hda.ok.tooltips.editAttrButton,
                hrefTpl  : this.historypanel.data.text.hda.ok.hrefs.editAttrButton
            },
            'delete' : {
                nodeName : this.historypanel.data.text.hda.ok.nodeNames.deleteButton,
                selector : buttonsArea + ' ' + this.historypanel.data.selectors.hda.deleteButton,
                tooltip  : this.historypanel.data.text.hda.ok.tooltips.deleteButton,
                hrefTpl  : this.historypanel.data.text.hda.ok.hrefs.deleteButton
            }
        };
    this.test.assertVisible( buttonsArea, 'Button area is visible' );

    for( var i=0; i<shouldHaveTheseButtons.length; i++ ){
        // don't use button names we don't have data for
        var buttonName = shouldHaveTheseButtons[ i ];
        if( !buttons.hasOwnProperty( buttonName ) ){ continue; }

        this.test.comment( buttonName + ' should exist, be visible, and well formed' );
        var button = buttons[ buttonName ];
        this.debug( 'checking button "' + buttonName + '" on hda "' + hdaDbId + '":\n' + this.jsonStr( button ) );
        this.test.assertExists( button.selector,  buttonName + ' button exists' );
        this.test.assertVisible( button.selector, buttonName + ' button is visible' );

        var buttonElement = this.getElementInfo( button.selector );
        this.debug( 'buttonElement:' + this.jsonStr( buttonElement ) );

        // should be an anchor
        this.test.assert( buttonElement.nodeName === button.nodeName,
            buttonName + ' is proper node type (' + button.nodeName + '): ' + buttonElement.nodeName );

        // should have a proper href
        var href = buttonElement.attributes.href,
            hrefShouldBe = utils.format( button.hrefTpl, hdaDbId );
        this.assertTextContains( href, hrefShouldBe,
            buttonName + ' has proper href (' + hrefShouldBe + '): ' + href );

        this.historypanel.hoverOver( button.selector, function testingHover(){
            var tooltipText = button.tooltip;
            this.test.assertVisible( tooltipSelector, buttonName + ' button tooltip is visible when hovering' );
            this.test.assertSelectorHasText( tooltipSelector, tooltipText,
                buttonName + ' button has tooltip text: "' + tooltipText + '"' );
        }, historyFrameInfo );
    }
}

function testDbkey( hdaSelector, dbkeySetTo ){
    var dbkeySelector = hdaSelector + ' ' + this.historypanel.data.selectors.hda.body
                                    + ' ' + this.historypanel.data.selectors.hda.dbkey,
        unspecifiedDbkeyText     = '?',
        unspecifiedDbkeyNodeName = 'a',
        specifiedDbkeyNodeName   = 'span',
        editAttrHrefRegex = /\/datasets\/\w+\/edit/;

    this.test.assertExists( dbkeySelector, 'dbkey exists' );
    this.test.assertVisible( dbkeySelector, 'dbkey is visible' );
    var dbkey = this.elementInfoOrNull( dbkeySelector );
    if( !dbkey ){ return; }

    // dbkey is set, check text
    if( dbkeySetTo ){
        this.test.comment( '(specified) dbkey should be displayed correctly' );
        this.test.assertSelectorHasText( dbkeySelector, dbkeySetTo,
            'dbkey is specified: ' + dbkey.text );
        this.test.assert( dbkey.nodeName === specifiedDbkeyNodeName,
            'dbkey has proper nodeName (' + specifiedDbkeyNodeName + '):' + dbkey.nodeName );

    // dbkey expected to be not set
    } else {
        this.test.comment( '(unspecified) dbkey should be displayed correctly' );
        this.test.assertSelectorHasText( dbkeySelector, unspecifiedDbkeyText,
            'dbkey is not specified: ' + dbkey.text );
        this.test.assert( dbkey.nodeName === unspecifiedDbkeyNodeName,
            'dbkey has proper nodeName (' + unspecifiedDbkeyNodeName + '):' + dbkey.nodeName );

        this.test.comment( '(unspecified) dbkey href should point to edit attributes' );
        this.test.assertMatch( dbkey.attributes.href, editAttrHrefRegex,
            'dbkey has a proper href: ' + dbkey.attributes.href );
    }
}

function testPrimaryActionButtons( hdaSelector ){
    var buttonsSelector = hdaSelector + ' ' + this.historypanel.data.selectors.hda.body
                                      + ' ' + this.historypanel.data.selectors.hda.primaryActionButtons;
    this.test.comment( 'Primary action buttons div should exist and be visible' );
    this.test.assertExists( buttonsSelector, 'Primary action buttons div exists' );
    this.test.assertVisible( buttonsSelector, 'Primary action buttons div is visible' );
}

function testSecondaryActionButtons( hdaSelector ){
    var buttonsSelector = hdaSelector + ' ' + this.historypanel.data.selectors.hda.body
                                      + ' ' + this.historypanel.data.selectors.hda.secondaryActionButtons;
    this.test.comment( 'Secondary action buttons div should exist and be visible' );
    this.test.assertExists( buttonsSelector, 'Secondary action buttons div exists' );
    this.test.assertVisible( buttonsSelector, 'Secondary action buttons div is visible' );
}

function testPeek( hdaSelector, expectedPeekArray ){
    var peekSelector = hdaSelector + ' ' + this.historypanel.data.selectors.hda.body
                                   + ' ' + this.historypanel.data.selectors.hda.peek;
    this.test.comment( 'Peek div should exist and be visible' );
    this.test.assertExists( peekSelector, 'peek exists' );
    this.test.assertVisible( peekSelector, 'peek is visible' );
    expectedPeekArray.forEach( function( string, i ){
        spaceghost.test.assertSelectorHasText( peekSelector, string, 'peek has proper text (' + string + ')' );
    });
}

function testExpandedBody( hdaSelector, expectedSummaryTextArray, expectedInfoText, dbkeySetTo ){
    var body = hdaSelector + ' ' + this.historypanel.data.selectors.hda.body;
    this.test.assertExists( body, 'body exists' );
    this.test.assertVisible( body, 'body is visible' );

    //TODO: create api module, match with api history_contents

    this.test.comment( 'Summary should be displayed correctly' );
    var summary = body + ' ' + this.historypanel.data.selectors.hda.summary;
    this.test.assertExists( summary, 'summary exists' );
    this.test.assertVisible( summary, 'summary is visible' );
    // summary text is broken up by whitespace making it inconv. to test in one go
    expectedSummaryTextArray.forEach( function( string, i ){
        spaceghost.test.assertSelectorHasText( summary, string, 'summary has proper text (' + string + ')' );
    });
    this.debug( 'summary text: ' + this.fetchText( summary ) );

    testDbkey.call( this, hdaSelector, dbkeySetTo );

    this.test.comment( 'Info should be displayed correctly' );
    var info = body + ' ' + this.historypanel.data.selectors.hda.info;
    this.test.assertExists( info, 'info exists' );
    this.test.assertVisible( info, 'info is visible' );
    this.test.assertSelectorHasText( info, expectedInfoText,
        'info has proper text (' + expectedInfoText + '): ' + this.fetchText( info ) );

    testPrimaryActionButtons.call( this, hdaSelector );
    testSecondaryActionButtons.call( this, hdaSelector ); //TODO: isAnonymous
    testPeek.call( this, hdaSelector, peekShouldBeArray );
}

// =================================================================== TESTS
// ------------------------------------------------------------------- ok state
spaceghost.then( function checkOkState(){
    this.test.comment( 'HDAs in the "ok" state should be well formed' );

    this.withFrame( spaceghost.data.selectors.frames.history, function(){
        var uploadSelector = '#' + testUploadInfo.hdaElement.attributes.id;
        this.test.assertVisible( uploadSelector, 'HDA is visible' );

        this.test.comment( 'should have the proper state class' );
        this.assertHasClass( uploadSelector, this.historypanel.data.selectors.hda.wrapper.stateClasses.ok,
            'HDA has ok state class' );

        // since we're using css there's no great way to test state icon (.state-icon is empty)

        this.test.comment( 'should have proper title and hid' );
        testTitle.call( spaceghost, uploadSelector, testUploadInfo.hid, testUploadInfo.name );

        this.test.comment( 'should have all of the three, main buttons' );
        testTitleButtonStructure.call( spaceghost, uploadSelector );

        this.test.comment( 'body is not visible before clicking the hda title' );
        var body = uploadSelector + ' ' + this.historypanel.data.selectors.hda.body;
        this.test.assertNotVisible( body, 'body is not visible' );

        this.test.comment( 'clicking the hda title should expand its body' );
        var hdaTitle = uploadSelector + ' ' + this.historypanel.data.selectors.hda.title;
        this.click( hdaTitle );
        this.wait( 500, function(){
            testExpandedBody.call( spaceghost, uploadSelector, summaryShouldBeArray, infoShouldBe, false );
        });
    });
});

// restore to collapsed
spaceghost.then( function collapseOkState(){
    this.test.comment( "Collapsing hda in 'ok' state should hide body again" );
    this.withFrame( spaceghost.data.selectors.frames.history, function(){
        var uploadSelector = '#' + testUploadInfo.hdaElement.attributes.id,
            hdaTitle = uploadSelector + ' ' + this.historypanel.data.selectors.hda.title;
            body = uploadSelector + ' ' + this.historypanel.data.selectors.hda.body;

        this.click( hdaTitle );
        this.wait( 500, function(){
            this.test.assertNotVisible( body, 'body is not visible' );
        });
    });
});


// ------------------------------------------------------------------- new state
spaceghost.then( function checkNewState(){
    this.test.comment( 'HDAs in the "new" state should be well formed' );

    this.withFrame( spaceghost.data.selectors.frames.history, function(){
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
            testTitle.call( spaceghost, uploadSelector, testUploadInfo.hid, testUploadInfo.name );

            this.test.comment( 'new HDA should have the new state class' );
            this.assertHasClass( uploadSelector, this.historypanel.data.selectors.hda.wrapper.stateClasses['new'],
                'HDA has new state class' );

            this.test.comment( 'new HDA should NOT have any of the three, main buttons' );
            var buttonSelector = uploadSelector + ' ' + this.historypanel.data.selectors.hda.titleButtons + ' a';
            this.test.assertDoesntExist( buttonSelector, 'No display, edit, or delete buttons' );

            this.test.comment( 'clicking the title of the new HDA will expand the body' );
            var hdaTitle = uploadSelector + ' ' + this.historypanel.data.selectors.hda.title;
            this.click( hdaTitle );
            this.wait( 500, function(){
                var bodySelector = uploadSelector + ' ' + this.historypanel.data.selectors.hda.body;
                this.test.assertVisible( bodySelector, 'HDA body is visible (after expanding)' );

                var expectedBodyText = 'This is a new dataset';
                this.test.comment( 'the body should have the text: ' + expectedBodyText );
                this.test.assertSelectorHasText( bodySelector, expectedBodyText,
                    'HDA body has text: ' + expectedBodyText );

                // restore to collapsed
                this.click( hdaTitle );
            });
        });
    });
});
// restore state, collapse
spaceghost.then( function revertStateAndCollapse(){
    this.withFrame( spaceghost.data.selectors.frames.history, function(){
        this.evaluate( function(){
            return Galaxy.currHistoryPanel.model.hdas.at( 0 ).set( 'state', 'ok' );
        });
        this.wait( 500, function(){
            var hdaTitle = '#' + testUploadInfo.hdaElement.attributes.id
                + ' ' + this.historypanel.data.selectors.hda.title;
            this.click( hdaTitle );
        });
    });
});


// ===================================================================
spaceghost.run( function(){
    this.test.done();
});
