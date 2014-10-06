var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Testing histories for anonymous users', 0, function suite( test ){
    spaceghost.start();

// ===================================================================

var email = spaceghost.user.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
    spaceghost.info( 'Will use fixtureData.testUser: ' + email );
}

var tooltipSelector     = spaceghost.data.selectors.tooltipBalloon,
    editableTextClass   = spaceghost.data.selectors.editableText,
    editableTextInput   = spaceghost.data.selectors.editableTextInput,

    unnamedName         = spaceghost.historypanel.data.text.history.newName,
    nameSelector        = spaceghost.historypanel.data.selectors.history.name,
    sizeSelector        = spaceghost.historypanel.data.selectors.history.size,
    initialSizeStr      = spaceghost.historypanel.data.text.history.newSize,
    tagIconSelector     = spaceghost.historypanel.data.selectors.history.tagIcon,
    annoIconSelector    = spaceghost.historypanel.data.selectors.history.annoIcon,
    emptyMsgSelector    = spaceghost.historypanel.data.selectors.history.emptyMsg,
    emptyMsgStr         = spaceghost.historypanel.data.text.history.emptyMsg,
    anonNameTooltip     = spaceghost.historypanel.data.text.anonymous.tooltips.name;

var historyFrameInfo = {},
    filenameToUpload = '1.txt',
    filepathToUpload = '../../test-data/' + filenameToUpload,
    testUploadInfo = {};


// =================================================================== TESTS
// ------------------------------------------------------------------- check the anonymous new, history for form
spaceghost.openHomePage().historypanel.waitForHdas( function testPanelStructure(){
    this.test.comment( 'history panel for anonymous user, new history' );

    this.test.comment( "history name should exist, be visible, and have text " + unnamedName );
    this.test.assertExists( nameSelector, nameSelector + ' exists' );
    this.test.assertVisible( nameSelector, 'History name is visible' );
    this.test.assertSelectorHasText( nameSelector, unnamedName, 'History name is ' + unnamedName );

    this.test.comment( "history should display size and size should be 0 bytes" );
    this.test.assertExists( sizeSelector, 'Found ' + sizeSelector );
    this.test.assertVisible( sizeSelector, 'History size is visible' );
    this.test.assertSelectorHasText( sizeSelector, initialSizeStr,
        'History size has "' + initialSizeStr + '"' );

    this.test.comment( "NO tags or annotations icons should be available for an anonymous user" );
    this.test.assertDoesntExist( tagIconSelector,  'Tag icon button not found' );
    this.test.assertDoesntExist( annoIconSelector, 'Annotation icon button not found' );

    this.test.assertExists( emptyMsgSelector, emptyMsgSelector + ' exists' );
    this.test.comment( "A message about the current history being empty should be displayed" );
    this.test.assertVisible( emptyMsgSelector, 'Empty history message is visible' );
    this.test.assertSelectorHasText( emptyMsgSelector, emptyMsgStr,
        'Message contains "' + emptyMsgStr + '"' );

    this.test.comment( 'name should NOT be editable when clicked by anon-user' );
    this.assertDoesntHaveClass( nameSelector, editableTextClass, "Name field is not classed as editable text" );
    this.click( nameSelector );
    this.test.assertDoesntExist( editableTextInput, "Clicking on name does not create an input" );
});

// ------------------------------------------------------------------- anon user can upload file
spaceghost.then( function testAnonUpload(){
    this.test.comment( 'anon-user should be able to upload files' );

    spaceghost.tools.uploadFile( filepathToUpload, function uploadCallback( _uploadInfo ){
        this.debug( 'uploaded HDA info: ' + this.jsonStr( this.quickInfo( _uploadInfo.hdaElement ) ) );
        var hasHda = _uploadInfo.hdaElement,
            hasClass = _uploadInfo.hdaElement.attributes[ 'class' ],
            hasOkClass = _uploadInfo.hdaElement.attributes[ 'class' ].indexOf( 'state-ok' ) !== -1;
        this.test.assert( ( hasHda && hasClass && hasOkClass ), "Uploaded file: " + _uploadInfo.hdaElement.text );
        testUploadInfo = _uploadInfo;
    });

});
spaceghost.then( function testAnonUpload(){
    this.test.comment( "empty should be NO LONGER be displayed" );
    this.test.assertNotVisible( emptyMsgSelector, 'Empty history message is not visible' );
});

// ------------------------------------------------------------------- anon user can run tool on file

// ------------------------------------------------------------------- anon user registers/logs in -> same history
spaceghost.user.loginOrRegisterUser( email, password ).openHomePage( function(){
    this.test.comment( 'anon-user should login and be associated with previous history' );

    var loggedInAs = spaceghost.user.loggedInAs();
    this.test.assert( loggedInAs === email, 'loggedInAs() matches email: "' + loggedInAs + '"' );

    this.historypanel.waitForHdas( function(){
        var hdaInfo = this.historypanel.hdaElementInfoByTitle( filenameToUpload );
        this.test.assert( hdaInfo !== null, "After logging in - found a matching hda by name and hid" );
        if( hdaInfo ){
            this.test.assert( testUploadInfo.hdaElement.attributes.id === hdaInfo.attributes.id,
                "After logging in - found a matching hda by hda view id: " + hdaInfo.attributes.id );
        }
    });
});

// ------------------------------------------------------------------- logs out -> new history
spaceghost.user.logout().openHomePage( function(){
    this.test.comment( 'logging out should create a new, anonymous history' );

    this.historypanel.waitForHdas( function(){
        this.test.assertSelectorHasText( nameSelector, unnamedName, 'History name is ' + unnamedName );
        this.test.assertSelectorHasText( emptyMsgSelector, emptyMsgStr,
            'Message contains "' + emptyMsgStr + '"' );
    });
});

// ===================================================================
    spaceghost.run( function(){ test.done(); });
});
