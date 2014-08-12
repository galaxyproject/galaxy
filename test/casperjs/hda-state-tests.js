var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Test the form of various HDA states', 0, function suite( test ){
    spaceghost.start();
    spaceghost.openHomePage().then( function(){
    });

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

var tooltipSelector = spaceghost.data.selectors.tooltipBalloon,
    filepathToUpload = '../../test-data/1.txt',
    testUploadInfo = {},
    //TODO: get from the api module - that doesn't exist yet
    summaryShouldBeArray = [ '10 lines', 'format', 'txt' ],
    infoShouldBe = 'uploaded txt file',
    metadataFiles = null,
    peekShouldBeArray = [];

// ------------------------------------------------------------------- set up
// start a new user and upload a file
spaceghost.user.loginOrRegisterUser( email, password );
spaceghost.then( function upload(){
    spaceghost.tools.uploadFile( filepathToUpload, function uploadCallback( _uploadInfo ){
        testUploadInfo = _uploadInfo;
    });
});

// =================================================================== TEST HELPERS
//NOTE: to be called with fn.call( spaceghost, ... )

function testTitle( hdaSelector, name ){
    var titleSelector = hdaSelector + ' ' + this.historypanel.data.selectors.hda.title;
    this.test.assertVisible( titleSelector,
        'HDA title is visible' );
    this.test.assertSelectorHasText( titleSelector, name,
        'HDA contains name (' + name + '): ' + this.fetchText( titleSelector ) );
}

function testIconButton( hdaDbId, containerSelector, buttonName, expectedButtonData ){
    this.test.comment( buttonName + ' should exist, be visible, and well formed' );
    this.debug( 'checking button "' + buttonName + '" within "' + containerSelector + '":\n' +
        this.jsonStr( expectedButtonData ) );
    
    if( !expectedButtonData.selector ){ this.test.fail( 'BAD TEST DATA: no selector given' ); }
    var btnSelector = containerSelector + ' ' + expectedButtonData.selector;
    this.test.assertExists( btnSelector,  buttonName + ' button exists' );
    this.test.assertVisible( btnSelector, buttonName + ' button is visible' );

    var buttonElement = this.getElementInfo( btnSelector );
    this.debug( 'buttonElement:' + this.jsonStr( this.quickInfo( buttonElement ) ) );

    if( expectedButtonData.nodeName ){
        this.test.assert( buttonElement.nodeName === expectedButtonData.nodeName,
            buttonName + ' is proper node type (' + expectedButtonData.nodeName + '): ' + buttonElement.nodeName );
    }

    if( expectedButtonData.hrefTpl ){
        var href = buttonElement.attributes.href,
            hrefShouldBe = ( expectedButtonData.hrefTpl.indexOf( '%s' ) !== -1 )?
                ( utils.format( expectedButtonData.hrefTpl, hdaDbId ) ):( expectedButtonData.hrefTpl );
        this.assertTextContains( href, hrefShouldBe,
            buttonName + ' has proper href (' + hrefShouldBe + '): ' + href );
    }

    if( expectedButtonData.tooltip ){
        this.hoverOver( btnSelector );
        var tooltipText = expectedButtonData.tooltip;
        this.test.assertVisible( tooltipSelector, buttonName + ' button tooltip is visible when hovering' );
        this.test.assertSelectorHasText( tooltipSelector, tooltipText,
            buttonName + ' button has tooltip text: "' + tooltipText + '"' );
        // clear the tooltip
        this.page.sendEvent( 'mouseover', 0, 0 );
    }
}

function testTitleButtonStructure( hdaSelector, shouldHaveTheseButtons ){
    // defaults to the current buttons most states should have
    shouldHaveTheseButtons = shouldHaveTheseButtons || [ 'display', 'edit', 'delete' ];

    var hdaDbId = this.getElementAttribute( hdaSelector, 'id' ).split( '-' )[1],
        buttonsArea = hdaSelector + ' ' + this.historypanel.data.selectors.hda.titleButtonArea,
        buttons = this.historypanel.data.hdaTitleButtons;

    this.test.assertVisible( buttonsArea, 'Button area is visible' );

    for( var i=0; i<shouldHaveTheseButtons.length; i += 1 ){
        // don't use button names we don't have data for
        var buttonName = shouldHaveTheseButtons[ i ];
        if( !buttons.hasOwnProperty( buttonName ) ){ continue; }
        var button = buttons[ buttonName ];

        testIconButton.call( this, hdaDbId, buttonsArea, buttonName, button );
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
            'dbkey has proper nodeName (' + specifiedDbkeyNodeName + '): ' + dbkey.nodeName );

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

function testDownloadMenu( hdaSelector, expectedMetadataFiles ){
    var hdaDbId = this.getElementAttribute( hdaSelector, 'id' ).split( '-' )[1];

    // assert has classes: menubutton split popup
    // click popup
}

function testMetadataDownloadLink( menuSelector, metadataFile ){

}

function testPrimaryActionButtons( hdaSelector, expectedMetadataFiles ){
    //TODO: not abstracted well for all states
    var hdaDbId = this.getElementAttribute( hdaSelector, 'id' ).split( '-' )[1],
        buttonsSelector = hdaSelector + ' ' + this.historypanel.data.selectors.hda.body
                                      + ' ' + this.historypanel.data.selectors.hda.primaryActionButtons,
        dropdownSelector = '#' + utils.format(
            this.historypanel.data.hdaPrimaryActionButtons.downloadDropdownButtonIdTpl, hdaDbId );

    this.test.comment( 'Primary action buttons div should exist and be visible' );
    this.test.assertExists( buttonsSelector, 'Primary action buttons div exists' );
    this.test.assertVisible( buttonsSelector, 'Primary action buttons div is visible' );
    //TODO: ...
    // different states, datatypes will have different action buttons
    testIconButton.call( this, hdaDbId, buttonsSelector, 'info',
        this.historypanel.data.hdaPrimaryActionButtons.info );
    testIconButton.call( this, hdaDbId, buttonsSelector, 'rerun',
        this.historypanel.data.hdaPrimaryActionButtons.rerun );

    //TODO: move to testDownloadButton as its own step
    if( !expectedMetadataFiles ){
        this.test.comment( 'no expected metadata, download button should be an icon button' );
        this.test.assertDoesntExist( dropdownSelector, 'no dropdown selector exists:' + dropdownSelector );
        testIconButton.call( this, hdaDbId, buttonsSelector, 'download',
            this.historypanel.data.hdaPrimaryActionButtons.download );

    } else {
        this.test.comment( 'expecting metadata, download button should be a popup menu' );

        // will be a drop down and should contain links to all metadata files
        this.test.assertVisible( dropdownSelector, 'dropdown menu button visible: ' + dropdownSelector );
        testIconButton.call( this, hdaDbId, dropdownSelector, 'download',
            this.historypanel.data.hdaPrimaryActionButtons.download );

        this.test.comment( 'clicking the button should show a popup menu with download links' );
        this.click( dropdownSelector );
        this.wait( 100, function(){
            //TODO: abstract to popup menu checker
            var menuSelector = '#' + utils.format(
                this.historypanel.data.hdaPrimaryActionButtons.downloadDropdownMenuIdTpl, hdaDbId );
            this.test.assertVisible( menuSelector, 'menu visible: ' + menuSelector );

            var liCounter = 1;
            var mainDataSelector = menuSelector + ' ' + 'li:nth-child(' + liCounter + ') a';
            this.assertVisibleWithText( mainDataSelector, 'Download Dataset',
                mainDataSelector + ' (main data download) has proper text: ' + 'Download Dataset' );
            liCounter += 1;
            
            var splitLabelSelector = menuSelector + ' ' + 'li:nth-child(' + liCounter + ') a';
            this.test.assertVisible( splitLabelSelector, 'split label visible' );
            this.test.assertSelectorHasText( splitLabelSelector, 'Additional Files',
                'split label has proper text' );
            liCounter += 1;

            var self = this;
            expectedMetadataFiles.forEach( function( file ){
                var linkSelector = menuSelector + ' ' + 'li:nth-child(' + liCounter + ') a';
                self.test.assertVisible( linkSelector, '#' + liCounter + ' link visible' );
                self.test.assertSelectorHasText( linkSelector, 'Download ' + file,
                    '#' + liCounter + ' link has proper text: Download ' + file );
                liCounter += 1;
            });
        });
    }
}

function testSecondaryActionButtons( hdaSelector ){
    var buttonsSelector = hdaSelector + ' ' + this.historypanel.data.selectors.hda.body
                                      + ' ' + this.historypanel.data.selectors.hda.secondaryActionButtons;
    this.test.comment( 'Secondary action buttons div should exist and be visible' );
    this.test.assertExists( buttonsSelector, 'Secondary action buttons div exists' );
    this.test.assertVisible( buttonsSelector, 'Secondary action buttons div is visible' );
    //TODO: ...
    // tags, annotations
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

function testExpandedBody( hdaSelector, expectedSummaryTextArray, expectedInfoText, dbkeySetTo, expectedMetadata ){
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

    testPrimaryActionButtons.call( this, hdaSelector, expectedMetadata );
    testSecondaryActionButtons.call( this, hdaSelector ); //TODO: isAnonymous
    testPeek.call( this, hdaSelector, peekShouldBeArray );
}

// =================================================================== TESTS
// ------------------------------------------------------------------- ok state
spaceghost.then( function(){
    this.test.comment( 'HDAs in the "ok" state should be well formed' );

    var uploadSelector = '#' + testUploadInfo.hdaElement.attributes.id;
    this.test.assertVisible( uploadSelector, 'HDA is visible' );

    this.test.comment( 'should have the proper state class' );
    this.assertHasClass( uploadSelector, this.historypanel.data.selectors.hda.wrapper.stateClasses.ok,
        'HDA has ok state class' );

    // since we're using css there's no great way to test state icon (.state-icon is empty)

    this.test.comment( 'should have proper title and hid' );
    testTitle.call( spaceghost, uploadSelector, testUploadInfo.filename );

    this.test.comment( 'should have all of the three, main buttons' );
    testTitleButtonStructure.call( spaceghost, uploadSelector );

    this.test.comment( 'body is not visible before clicking the hda title' );
    var body = uploadSelector + ' ' + this.historypanel.data.selectors.hda.body;
    this.test.assertNotVisible( body, 'body is not visible' );

    this.test.comment( 'clicking the hda title should expand its body' );
    this.historypanel.thenExpandHda( uploadSelector, function(){
        testExpandedBody.call( spaceghost, uploadSelector,
            summaryShouldBeArray, infoShouldBe, false, metadataFiles );
        //testExpandedBody.call( spaceghost, uploadSelector,
        //    summaryShouldBeArray, infoShouldBe, false );
    });
});
// restore to collapsed
spaceghost.then( function(){
    this.test.comment( "Collapsing hda in 'ok' state should hide body again" );
    var uploadSelector = '#' + testUploadInfo.hdaElement.attributes.id;

    spaceghost.historypanel.thenCollapseHda( uploadSelector, function collapseOkState(){
        this.test.assertNotVisible( uploadSelector + ' ' + this.historypanel.data.selectors.hda.body,
            'body is not visible' );
    });
});

// ------------------------------------------------------------------- new state
spaceghost.then( function(){
    // set state directly through model, wait for re-render
    //TODO: not ideal to test this
    this.evaluate( function(){
        return Galaxy.currHistoryPanel.model.contents.at( 0 ).set( 'state', 'new' );
    });
    this.wait( 1000, function(){
        this.test.comment( 'HDAs in the "new" state should be well formed' );

        var uploadSelector = '#' + testUploadInfo.hdaElement.attributes.id;
        this.test.assertVisible( uploadSelector, 'HDA is visible' );

        // should have proper title and hid
        testTitle.call( spaceghost, uploadSelector, testUploadInfo.filename );

        this.test.comment( 'new HDA should have the new state class' );
        this.assertHasClass( uploadSelector, this.historypanel.data.selectors.hda.wrapper.stateClasses['new'],
            'HDA has new state class' );

        this.test.comment( 'new HDA should NOT have any of the three, main buttons' );
        var buttonSelector = uploadSelector + ' ' + this.historypanel.data.selectors.hda.titleButtons + ' a';
        this.test.assertDoesntExist( buttonSelector, 'No display, edit, or delete buttons' );

        this.test.comment( 'clicking the title of the new HDA will expand the body' );

        this.historypanel.thenExpandHda( uploadSelector, function(){
            var bodySelector = uploadSelector + ' ' + this.historypanel.data.selectors.hda.body;
            this.test.assertVisible( bodySelector, 'HDA body is visible (after expanding)' );

            var expectedBodyText = 'This is a new dataset';
            this.test.comment( 'the body should have the text: ' + expectedBodyText );
            this.test.assertSelectorHasText( bodySelector, expectedBodyText,
                'HDA body has text: ' + expectedBodyText );
        });

        this.then( function(){
            this.test.comment( 'a simulated error on a new dataset should appear in a message box' );
            // datasets that error on fetching their data appear as 'new', so do this here
            // more of a unit test, but ok
            var errorString = 'Blah!';

            this.evaluate( function( errorString ){
                return Galaxy.currHistoryPanel.model.contents.getByHid( 1 ).set( 'error', errorString );
            }, errorString );

            // wait for re-render
            this.wait( 1000, function(){
                var errorMessage = this.historypanel.data.selectors.hda.errorMessage;
                
                this.test.assertExists( errorMessage, 'error message exists' );
                this.test.assertVisible( errorMessage, 'error message is visible' );
                this.test.assertSelectorHasText( errorMessage, this.historypanel.data.text.hda.datasetFetchErrorMsg,
                    'error message has text: ' + this.historypanel.data.text.hda.datasetFetchErrorMsg );
                this.test.assertSelectorHasText( errorMessage, errorString,
                    'error message has error string: ' + errorString );
            });
        });
    });
});
// restore state, collapse
spaceghost.then( function revertStateAndCollapse(){
    var uploadSelector = '#' + testUploadInfo.hdaElement.attributes.id;

    this.historypanel.thenCollapseHda( uploadSelector, function(){
        this.evaluate( function(){
            Galaxy.currHistoryPanel.model.contents.getByHid( 1 ).unset( 'error' );
            return Galaxy.currHistoryPanel.model.contents.at( 0 ).set( 'state', 'ok' );
        });
    });
    this.wait( 1000 );
});
/*
*/

// ===================================================================
    spaceghost.run( function(){ test.done(); });
});
