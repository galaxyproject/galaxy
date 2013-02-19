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
*/
// =================================================================== globals and helpers
var email = spaceghost.user.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
}
var newHistoryName = "Test History";

var nameSelector     = 'div#history-name',
    unnamedName      = 'Unnamed history',
    subtitleSelector = 'div#history-subtitle-area',
    initialSizeStr   = '0 bytes',
    tagIconSelector  = '#history-tag.icon-button',
    annoIconSelector = '#history-annotate.icon-button',
    //emptyMsgSelector = '#emptyHistoryMessage';
    emptyMsgSelector = '.infomessagesmall',
    emptyMsgStr      = "Your history is empty. Click 'Get Data' on the left pane to start",

    tooltipSelector  = '.bs-tooltip',
    nameTooltip      = 'Click to rename history',

    editableTextClass = 'editable-text',
    editableTextInputSelector = 'input#renaming-active';

var historyFrameInfo = {},
    testUploadInfo = {};


// =================================================================== TESTS
// ------------------------------------------------------------------- start a new user
spaceghost.user.loginOrRegisterUser( email, password );
//??: why is a reload needed here? If we don't, loggedInAs === '' ...
spaceghost.thenOpen( spaceghost.baseUrl, function(){
    var loggedInAs = spaceghost.user.loggedInAs();
    this.test.assert( loggedInAs === email, 'loggedInAs() matches email: "' + loggedInAs + '"' );
});

// ------------------------------------------------------------------- check structure of empty history
// grab the history frame bounds for mouse later tests
spaceghost.then( function(){
    historyFrameInfo = this.getElementInfo( 'iframe[name="galaxy_history"]' );
    //this.debug( 'historyFrameInfo:' + this.jsonStr( historyFrameInfo ) );
});

spaceghost.thenOpen( spaceghost.baseUrl, function testPanelStructure(){
    this.test.comment( 'history panel, new history' );
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

        this.test.comment( "tags and annotation icons should be available" );
        this.test.assertExists( tagIconSelector,  'Tag icon button found' );
        this.test.assertExists( annoIconSelector, 'Annotation icon button found' );

        this.test.comment( "A message about the current history being empty should be displayed" );
        this.test.assertExists( emptyMsgSelector, emptyMsgSelector + ' exists' );
        this.test.assertVisible( emptyMsgSelector, 'Empty history message is visible' );
        this.test.assertSelectorHasText( emptyMsgSelector, emptyMsgStr,
            'Message contains "' + emptyMsgStr + '"' );

    });
});

// ------------------------------------------------------------------- name editing
spaceghost.then( function(){
    this.test.comment( 'history panel, editing the history name' );
    this.withFrame( this.selectors.frames.history, function(){
        this.test.comment( 'name should have a tooltip with proper info on name editing' );
        var nameInfo = this.getElementInfo( nameSelector );
        this.page.sendEvent( 'mousemove',
            historyFrameInfo.x + nameInfo.x + 1, historyFrameInfo.y + nameInfo.y + 1 );
        this.test.assertExists( tooltipSelector, "Found tooltip after name hover" );
        this.test.assertSelectorHasText( tooltipSelector, nameTooltip );

        this.test.comment( 'name should be create an input when clicked' );
        this.test.assert( nameInfo.attributes[ 'class' ].indexOf( editableTextClass ) !== -1,
            "Name field classed for editable text" );
        this.click( nameSelector );
        this.test.assertExists( editableTextInputSelector, "Clicking on name creates an input" );

        this.test.comment( 'name should be editable by entering keys and pressing enter' );
        //NOTE: casperjs.sendKeys adds a click before and a selector.blur after sending - won't work here
        //TODO: to conv. fn
        this.page.sendEvent( 'keypress', newHistoryName );
        this.page.sendEvent( 'keypress', this.page.event.key.Enter );
        this.wait( 1000, function(){
            this.test.assertSelectorHasText( nameSelector, newHistoryName, 'History name is ' + newHistoryName );
            this.test.assertDoesntExist( editableTextInputSelector, "Input disappears after pressing enter" );
        });
    });
});
spaceghost.then( function(){
    this.withFrame( this.selectors.frames.history, function(){
        this.test.comment( 'name should revert if user clicks away while editing' );
        this.click( nameSelector );
        this.page.sendEvent( 'keypress', "Woodchipper metagenomics, Fargo, ND" );

        // click above the name input element
        var inputInfo = this.getElementInfo( editableTextInputSelector );
        this.page.sendEvent( 'mousedown',
            historyFrameInfo.x + inputInfo.x + 1, historyFrameInfo.y + inputInfo.y - 5 );

        this.wait( 1000, function(){
            this.test.assertSelectorHasText( nameSelector, newHistoryName, 'History name is STILL ' + newHistoryName );
            this.test.assertDoesntExist( editableTextInputSelector, "Input disappears after clicking away" );
        });
    });
});
spaceghost.then( function(){
    this.withFrame( this.selectors.frames.history, function(){
        this.test.comment( 'name should revert if user hits ESC while editing' );
        this.click( nameSelector );
        this.page.sendEvent( 'keypress', "Arsenic Bacteria" );

        this.page.sendEvent( 'keypress', this.page.event.key.Escape );
        this.wait( 1000, function(){
            this.test.assertSelectorHasText( nameSelector, newHistoryName, 'History name is STILL ' + newHistoryName );
            this.test.assertDoesntExist( editableTextInputSelector, "Input disappears after hitting ESC" );
        });
    });
});


// ------------------------------------------------------------------- check structure of NON empty history
/*
// upload file: 1.txt
spaceghost.then( function upload(){
    this.test.comment( 'anon-user should be able to upload files' );
    spaceghost.uploadFile( '../../test-data/1.txt', function uploadCallback( _uploadInfo ){
        this.debug( 'uploaded HDA info: ' + this.jsonStr( _uploadInfo ) );
        var hasHda = _uploadInfo.hdaElement,
            hasClass = _uploadInfo.hdaElement.attributes[ 'class' ],
            hasOkClass = _uploadInfo.hdaElement.attributes[ 'class' ].indexOf( 'historyItem-ok' ) !== -1;
        this.test.assert( ( hasHda && hasClass && hasOkClass ), "Uploaded file: " + _uploadInfo.name );
        uploadInfo = _uploadInfo;
    });
});

//TODO: for each uploaded file: 1 file per (standard) datatype (or some subset)
// txt, tabular, sam, bam, fasta, fastq, bed, gff,
*/

// -------------------------------------------------------------------
//history panel
    // structure of empty
    // upload file
    // structure of not empty
    // tags
    // annotation
    // history refresh
    // history options
        // structure

    // deleted

    // hidden

    // persistant expansion (or in hdaView?)

//hdaView
// with hpanel:
    // (we assume hda is in the ok state)
    // with collapsed hda:
        // can we see the hid?
        // can we see the title?
        // three primary action buttons:
            // they exist?
            // Do they have good hrefs, targets?
            // Are they enabled?
            // do they have proper tooltips?
                // display
                // edit
                // delete
        //??: click through?

    // with expaned hda:
        // can we see the hid, title, and primary display buttons?

        // misc info: no dbkey specified - is there a '?' link leading to edit attr?
        // misc info: uploaded sam file
        // misc info: format: sam

        // secondary actions:
            // download
            // info
            // rerun
            // visualizations

        // tags and annotations
            //TODO: to their own file? tested elsewhere?

        // peek:
            // proper headers?
            // lines?
            // scrollbar?

    // can re-collapse?








// ===================================================================
spaceghost.run( function(){
    this.test.done();
});
