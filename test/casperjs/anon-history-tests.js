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


// -------------------------------------------------------------------
/* TODO:
    run a tool

*/
// =================================================================== globals and helpers
var email = spaceghost.user.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
    spaceghost.info( 'Will use fixtureData.testUser: ' + email );
}

var tooltipSelector  = '.bs-tooltip',

    editableTextClass = 'editable-text',
    editableTextInputSelector = 'input#renaming-active',

    galaxyCookieName = 'galaxysession';

    unnamedName         = spaceghost.historypanel.data.text.history.newName,
    nameSelector        = spaceghost.historypanel.data.selectors.history.name,
    subtitleSelector    = spaceghost.historypanel.data.selectors.history.subtitle,
    initialSizeStr      = spaceghost.historypanel.data.text.history.newSize,
    tagIconSelector     = spaceghost.historypanel.data.selectors.history.tagIcon,
    annoIconSelector    = spaceghost.historypanel.data.selectors.history.annoIcon,
    emptyMsgSelector    = spaceghost.historypanel.data.selectors.history.emptyMsg,
    emptyMsgStr         = spaceghost.historypanel.data.text.history.emptyMsg,
    anonNameTooltip     = spaceghost.historypanel.data.text.anonymous.tooltips.name;

var historyFrameInfo = {},
    testUploadInfo = {};


// =================================================================== TESTS
// ------------------------------------------------------------------- anonymous new, history
// open galaxy - ensure not logged in
spaceghost.thenOpen( spaceghost.baseUrl, function(){
    var loggedInAs = spaceghost.user.loggedInAs();
    this.debug( 'loggedInAs: ' + loggedInAs );
    if( loggedInAs ){ this.logout(); }
});

// ------------------------------------------------------------------- check anon cookies
spaceghost.then( function testAnonCookies(){
    this.test.comment( 'session cookie for anon-user should be present and well formed' );
    var cookies = this.page.cookies;
    this.debug( this.jsonStr( this.page.cookies ) );
    //??: what are 'well formed' values?
    this.test.assert( cookies.length === 1, "Has one cookie" );
    var galaxyCookie = cookies[0];
    this.test.assert( galaxyCookie.name === galaxyCookieName, "Cookie named: " + galaxyCookieName );
    this.test.assert( !galaxyCookie.secure, "Cookie.secure is false" );
});

// ------------------------------------------------------------------- check the empty history for well formedness
// grab the history frame bounds for mouse later tests
spaceghost.then( function(){
    historyFrameInfo = this.getElementInfo( 'iframe[name="galaxy_history"]' );
    //this.debug( 'historyFrameInfo:' + this.jsonStr( historyFrameInfo ) );
});

spaceghost.thenOpen( spaceghost.baseUrl, function testPanelStructure(){
    this.test.comment( 'history panel for anonymous user, new history' );
    this.withFrame( this.selectors.frames.history, function(){
        this.test.comment( "frame should have proper url and title: 'History'" );
        this.test.assertMatch( this.getCurrentUrl(), /\/history/, 'Found history frame url' );
        this.test.assertTitle( this.getTitle(), 'History', 'Found history frame title' );

        this.test.comment( "history name should exist, be visible, and have text " + unnamedName );
        this.test.assertExists( nameSelector, nameSelector + ' exists' );
        this.test.assertVisible( nameSelector, 'History name is visible' );
        this.test.assertSelectorHasText( nameSelector, unnamedName, 'History name is ' + unnamedName );

        this.test.comment( "history subtitle should display size and size should be 0 bytes" );
        this.test.assertExists( subtitleSelector, 'Found ' + subtitleSelector );
        this.test.assertVisible( subtitleSelector, 'History subtitle is visible' );
        this.test.assertSelectorHasText( subtitleSelector, initialSizeStr,
            'History subtitle has "' + initialSizeStr + '"' );

        this.test.comment( "NO tags or annotations icons should be available for an anonymous user" );
        this.test.assertDoesntExist( tagIconSelector,  'Tag icon button not found' );
        this.test.assertDoesntExist( annoIconSelector, 'Annotation icon button not found' );

        this.test.assertExists( emptyMsgSelector, emptyMsgSelector + ' exists' );
        this.test.comment( "A message about the current history being empty should be displayed" );
        this.test.assertVisible( emptyMsgSelector, 'Empty history message is visible' );
        this.test.assertSelectorHasText( emptyMsgSelector, emptyMsgStr,
            'Message contains "' + emptyMsgStr + '"' );

        this.test.comment( 'name should have a tooltip with info on anon-user name editing' );
        // mouse over to find tooltip
        //NOTE!!: bounds are returned relative to containing frame - need to adjust using historyFrameInfo
        //TODO: into conv. fn
        var nameInfo = this.getElementInfo( nameSelector );
        //this.debug( 'nameInfo:' + this.jsonStr( nameInfo ) );
        this.page.sendEvent( 'mousemove',
            historyFrameInfo.x + nameInfo.x + 1, historyFrameInfo.y + nameInfo.y + 1 );
        this.test.assertExists( tooltipSelector, "Found tooltip after name hover" );
        this.test.assertSelectorHasText( tooltipSelector, anonNameTooltip );

        this.test.comment( 'name should NOT be editable when clicked by anon-user' );
        this.test.assert( nameInfo.attributes[ 'class' ].indexOf( editableTextClass ) === -1,
            "Name field is not class for editable text" );
        this.click( nameSelector );
        this.test.assertDoesntExist( editableTextInputSelector, "Clicking on name does not create an input" );
    });
});

// ------------------------------------------------------------------- anon user can upload file
spaceghost.then( function testAnonUpload(){
    this.test.comment( 'anon-user should be able to upload files' );
    spaceghost.tools.uploadFile( '../../test-data/1.txt', function uploadCallback( _uploadInfo ){
        this.debug( 'uploaded HDA info: ' + this.jsonStr( _uploadInfo ) );
        var hasHda = _uploadInfo.hdaElement,
            hasClass = _uploadInfo.hdaElement.attributes[ 'class' ],
            hasOkClass = _uploadInfo.hdaElement.attributes[ 'class' ].indexOf( 'historyItem-ok' ) !== -1;
        this.test.assert( ( hasHda && hasClass && hasOkClass ), "Uploaded file: " + _uploadInfo.name );
        uploadInfo = _uploadInfo;
    });
});
spaceghost.then( function testAnonUpload(){
    this.test.comment( "empty should be NO LONGER be displayed" );
    this.test.assertNotVisible( emptyMsgSelector, 'Empty history message is not visible' );
});


// ------------------------------------------------------------------- anon user can run tool on file

// ------------------------------------------------------------------- anon user registers/logs in -> same history
spaceghost.user.loginOrRegisterUser( email, password );
//??: why is a reload needed here? If we don't, loggedInAs === '' ...
spaceghost.thenOpen( spaceghost.baseUrl, function(){

    this.test.comment( 'anon-user should login and be associated with previous history' );
    var loggedInAs = spaceghost.user.loggedInAs();
    this.test.assert( loggedInAs === email, 'loggedInAs() matches email: "' + loggedInAs + '"' );

    this.withFrame( this.selectors.frames.history, function(){
        var hdaInfo = this.historypanel.hdaElementInfoByTitle( uploadInfo.name, uploadInfo.hid );
        this.test.assert( hdaInfo !== null, "After logging in - found a matching hda by name and hid" );
        if( hdaInfo ){
            this.test.assert( uploadInfo.hdaElement.attributes.id === hdaInfo.attributes.id,
                "After logging in - found a matching hda by hda view id: " + hdaInfo.attributes.id );
        }
    });
});

spaceghost.user.logout();
spaceghost.thenOpen( spaceghost.baseUrl, function(){
    this.test.comment( 'logging out should create a new, anonymous history' );

    this.withFrame( this.selectors.frames.history, function(){
        this.test.assertSelectorHasText( nameSelector, unnamedName, 'History name is ' + unnamedName );
        this.test.assertSelectorHasText( emptyMsgSelector, emptyMsgStr,
            'Message contains "' + emptyMsgStr + '"' );
    });
});


// ===================================================================
spaceghost.run( function(){
    this.test.done();
});
