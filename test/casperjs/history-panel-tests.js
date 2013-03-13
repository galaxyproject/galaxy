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
    possibly break this file up
*/
// =================================================================== globals and helpers
var email = spaceghost.user.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
    spaceghost.info( 'Will use fixtureData.testUser: ' + email );
}

// selectors and labels
var nameSelector     = spaceghost.historypanel.data.selectors.history.name,
    subtitleSelector = spaceghost.historypanel.data.selectors.history.subtitle,
    unnamedName      = spaceghost.historypanel.data.text.history.newName,
    initialSizeStr   = spaceghost.historypanel.data.text.history.newSize,
    tagIconSelector  = spaceghost.historypanel.data.selectors.history.tagIcon,
    annoIconSelector = spaceghost.historypanel.data.selectors.history.annoIcon,
    emptyMsgSelector = spaceghost.historypanel.data.selectors.history.emptyMsg,
    emptyMsgStr      = spaceghost.historypanel.data.text.history.emptyMsg,
    wrapperOkClassName  = spaceghost.historypanel.data.selectors.hda.wrapper.stateClasses.ok,
    tagAreaSelector     = spaceghost.historypanel.data.selectors.history.tagArea,
    annoAreaSelector    = spaceghost.historypanel.data.selectors.history.annoArea,
    nameTooltip      = spaceghost.historypanel.data.text.history.tooltips.name,

    tooltipSelector  = '.bs-tooltip',

    editableTextClass = 'editable-text',
    editableTextInputSelector = 'input#renaming-active',

    refreshButtonSelector = 'a#history-refresh-button',
    refreshButtonIconSelector = 'span.fa-icon-refresh',
    refreshButtonHref = '/history',

    includeDeletedOptionsLabel = spaceghost.historyoptions.data.labels.options.includeDeleted;

// local
var newHistoryName = "Test History",
    filepathToUpload = '../../test-data/1.txt',
    historyFrameInfo = {},
    uploadInfo = {};


// =================================================================== TESTS
// ------------------------------------------------------------------- set up
// start a new user
spaceghost.user.loginOrRegisterUser( email, password );
//??: why is a reload needed here? If we don't, loggedInAs === '' ...
spaceghost.thenOpen( spaceghost.baseUrl, function(){
    var loggedInAs = spaceghost.user.loggedInAs();
    this.test.assert( loggedInAs === email, 'loggedInAs() matches email: "' + loggedInAs + '"' );
});

// grab the history frame bounds for later mouse tests
spaceghost.then( function(){
    historyFrameInfo = this.getElementInfo( 'iframe[name="galaxy_history"]' );
    //this.debug( 'historyFrameInfo:' + this.jsonStr( historyFrameInfo ) );
});

// ------------------------------------------------------------------- check structure of empty history
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
// upload file: 1.txt
spaceghost.then( function upload(){
    this.test.comment( 'uploaded file should appear in history' );
    spaceghost.tools.uploadFile( filepathToUpload, function uploadCallback( _uploadInfo ){
        this.debug( 'uploaded HDA info: ' + this.jsonStr( _uploadInfo ) );
        var hasHda = _uploadInfo.hdaElement,
            hasClass = _uploadInfo.hdaElement.attributes[ 'class' ],
            hasOkClass = _uploadInfo.hdaElement.attributes[ 'class' ].indexOf( wrapperOkClassName ) !== -1;
        this.test.assert( ( hasHda && hasClass && hasOkClass ), "Uploaded file: " + _uploadInfo.name );
        uploadInfo = _uploadInfo;
    });
});

spaceghost.then( function checkPanelStructure(){
    this.test.comment( 'checking structure of non-empty panel' );

    this.withFrame( this.selectors.frames.history, function(){
        this.test.comment( "history name should exist, be visible, and have text " + unnamedName );
        this.test.assertExists( nameSelector, nameSelector + ' exists' );
        this.test.assertVisible( nameSelector, 'History name is visible' );
        this.test.assertSelectorHasText( nameSelector, newHistoryName, 'History name is ' + newHistoryName );

        this.test.comment( "history subtitle should display size and size should be " + onetxtFilesize + " bytes" );
        var onetxtFilesize = require( 'fs' ).size( this.options.scriptDir + filepathToUpload ),
            expectedSubtitle = onetxtFilesize + ' bytes';
        this.test.assertExists( subtitleSelector, 'Found ' + subtitleSelector );
        this.test.assertVisible( subtitleSelector, 'History subtitle is visible' );
        this.test.assertSelectorHasText( subtitleSelector, expectedSubtitle,
            'History subtitle has "' + expectedSubtitle + '"' );

        this.test.comment( "tags and annotation icons should be available" );
        this.test.assertExists( tagIconSelector,  'Tag icon button found' );
        this.test.assertExists( annoIconSelector, 'Annotation icon button found' );

        this.test.comment( "A message about the current history being empty should NOT be displayed" );
        this.test.assertExists( emptyMsgSelector, emptyMsgSelector + ' exists' );
        this.test.assertNotVisible( emptyMsgSelector, 'Empty history message is NOT visible' );
    });
});

// ------------------------------------------------------------------- tags
// keeping this light here - better for it's own test file
//TODO: check tooltips
spaceghost.then( function openTags(){
    this.test.comment( 'tag area should open when the history panel tag icon is clicked' );
    this.withFrame( this.selectors.frames.history, function(){
        this.capture( 'tag-area.png' );
        this.mouseEvent( 'click', tagIconSelector );
        this.wait( 1000, function(){
            this.test.assertVisible( tagAreaSelector, 'Tag area is now displayed' );
        });
    });
});

// ------------------------------------------------------------------- annotation
// keeping this light here - better for it's own test file
//TODO: check tooltips
spaceghost.then( function openAnnotation(){
    this.test.comment( 'annotation area should open when the history panel annotation icon is clicked' );
    this.withFrame( this.selectors.frames.history, function(){
        this.mouseEvent( 'click', annoIconSelector );
        this.wait( 1000, function(){
            this.test.assertVisible( annoAreaSelector, 'Annotation area is now displayed' );
        });
    });
});
spaceghost.then( function closeAnnotation(){
    this.test.comment( 'annotation area should close when the history panel tag icon is clicked again' );
    this.withFrame( this.selectors.frames.history, function bler(){
        this.mouseEvent( 'click', annoIconSelector );
        this.wait( 1000, function(){
            this.test.assertNotVisible( annoAreaSelector, 'Tag area is now hidden' );
        });
    });
});

// ------------------------------------------------------------------- refresh button
spaceghost.then( function refreshButton(){
    this.test.comment( 'History panel should refresh when the history refresh icon is clicked' );

    this.test.assertExists(  refreshButtonSelector, "Found refresh button" );
    this.test.assertVisible( refreshButtonSelector, "Refresh button is visible" );
    this.test.assertVisible( refreshButtonSelector + ' ' + refreshButtonIconSelector, "Refresh icon is visible" );
    this.test.assert( this.getElementAttribute( refreshButtonSelector, 'href' ) === refreshButtonHref,
        "Refresh button has href: " + refreshButtonHref );

    this.assertNavigationRequested( refreshButtonHref, "History refreshed when clicking refresh icon", function(){
        this.click( refreshButtonSelector );
    });
});

// ------------------------------------------------------------------- history options menu structure
//NOTE: options menu should be functionally tested elsewhere
spaceghost.then( function historyOptions(){
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
    for( var optionKey in this.historyoptions.data.labels.options ){
        if( this.historyoptions.data.labels.options.hasOwnProperty( optionKey ) ){
            var optionLabel = this.historyoptions.data.labels.options[ optionKey ],
                optionXpath = this.historyoptions.data.selectors.optionXpathByLabelFn( optionLabel );
            this.test.assertVisible( optionXpath, 'Option label is visible: ' + optionLabel );
        }
    }
});

// ------------------------------------------------------------------- deleted hdas aren't in the dom
spaceghost.then( function(){
    this.test.comment( 'deleted hdas shouldn\'t be in the history panel DOM' );

    this.historypanel.deleteHda( '#' + uploadInfo.hdaElement.attributes.id, function(){
        this.test.assertDoesntExist( '#' + uploadInfo.hdaElement.attributes.id, "Deleted HDA is not in the DOM" );
    });
});

// ------------------------------------------------------------------- options allow showing/hiding deleted hdas
spaceghost.then( function(){
    this.test.comment( 'History options->' + includeDeletedOptionsLabel + ' shows deleted datasets' );

    this.historyoptions.includeDeleted();
    this.withFrame( this.selectors.frames.history, function(){
        this.waitForSelector( nameSelector, function(){
            this.test.assertExists( '#' + uploadInfo.hdaElement.attributes.id,
                "Deleted HDA is in the DOM (using history options -> " + includeDeletedOptionsLabel + ")" );
            this.test.assertVisible( '#' + uploadInfo.hdaElement.attributes.id,
                "Deleted HDA is visible again (using history options -> " + includeDeletedOptionsLabel + ")" );
        });
    });
});

spaceghost.then( function(){
    this.test.comment( 'History options->' + includeDeletedOptionsLabel + ' (again) re-hides deleted datasets' );

    this.historyoptions.includeDeleted();
    this.withFrame( this.selectors.frames.history, function(){
        this.waitForSelector( nameSelector, function(){
            this.test.assertDoesntExist( '#' + uploadInfo.hdaElement.attributes.id,
                "Deleted HDA is not in the DOM (using history options -> " + includeDeletedOptionsLabel + ")" );
        });
    });
});

// undelete the uploaded file
spaceghost.then( function(){
    this.historyoptions.includeDeleted();
    this.withFrame( this.selectors.frames.history, function(){
        this.waitForSelector( nameSelector, function(){
            //TODO: to conv. fn
            this.click( '#' + uploadInfo.hdaElement.attributes.id
                + ' ' + this.historypanel.data.selectors.history.undeleteLink );
        });
    });
});

// ------------------------------------------------------------------- hidden hdas aren't shown
// ------------------------------------------------------------------- history options allows showing hidden hdas
// can't test this yet w/o a way to make hdas hidden thru the ui or api

// ------------------------------------------------------------------- hdas can be expanded by clicking on the hda name
// broken in webkit w/ jq 1.7
spaceghost.then( function(){
    this.test.comment( 'HDAs can be expanded by clicking on the name' );
    var uploadedSelector = '#' + uploadInfo.hdaElement.attributes.id;

    this.withFrame( this.selectors.frames.history, function(){
        this.click( uploadedSelector + ' .historyItemTitle' );
        this.debug( 'title: ' + this.debugElement( uploadedSelector + ' .historyItemTitle' ) );
        this.debug( 'wrapper: ' + this.debugElement( uploadedSelector ) );

        this.wait( 1000, function(){
            this.test.assertExists( uploadedSelector + ' .historyItemBody', "Body for uploaded file is found" );
            this.test.assertVisible( uploadedSelector + ' .hda-summary', "hda-summary is visible" );
        });
    });
});

// ------------------------------------------------------------------- expanded hdas are still expanded after a refresh
spaceghost.then( function(){
    this.test.comment( 'Expanded hdas are still expanded after a refresh' );
    var uploadedSelector = '#' + uploadInfo.hdaElement.attributes.id;

    this.click( refreshButtonSelector );
    this.withFrame( this.selectors.frames.history, function(){
        this.waitForSelector( nameSelector, function(){
            this.test.assertExists( uploadedSelector + ' .historyItemBody', "Body for uploaded file is found" );
            this.test.assertVisible( uploadedSelector + ' .hda-summary', "hda-summary is visible" );
        });
    });
    // this will break: webkit + jq 1.7
});

// ------------------------------------------------------------------- expanded hdas collapse by clicking name again
spaceghost.then( function(){
    this.test.comment( 'Expanded hdas collapse by clicking name again' );
    var uploadedSelector = '#' + uploadInfo.hdaElement.attributes.id;

    this.withFrame( this.selectors.frames.history, function(){
        this.click( uploadedSelector + ' .historyItemTitle' );

        this.wait( 500, function(){
            this.test.assertNotVisible( uploadedSelector + ' .hda-summary', "hda-summary is not visible" );
        });
    });
});

// ------------------------------------------------------------------- collapsed hdas are still collapsed after a refresh
spaceghost.then( function(){
    this.test.comment( 'Expanded hdas are still expanded after a refresh' );
    var uploadedSelector = '#' + uploadInfo.hdaElement.attributes.id;

    this.click( refreshButtonSelector );
    this.withFrame( this.selectors.frames.history, function(){
        this.waitForSelector( nameSelector, function(){
            this.test.assertNotVisible( uploadedSelector + ' .hda-summary', "hda-summary is not visible" );
        });
    });
});

// ------------------------------------------------------------------- history options collapses all expanded hdas
spaceghost.then( function(){
    // expand again
    this.withFrame( this.selectors.frames.history, function(){
        this.click( '#' + uploadInfo.hdaElement.attributes.id + ' .historyItemTitle' );
        this.wait( 500, function(){});
    });
});
spaceghost.then( function(){
    this.test.comment( 'History option collapses all expanded hdas' );
    var uploadedSelector = '#' + uploadInfo.hdaElement.attributes.id;

    this.historyoptions.collapseExpanded();
    this.wait( 500, function(){
        this.withFrame( this.selectors.frames.history, function(){
            this.test.assertNotVisible( uploadedSelector + ' .hda-summary', "hda-summary is not visible" );
        });
    });
});

// ===================================================================
spaceghost.run( function(){
    this.test.done();
});
