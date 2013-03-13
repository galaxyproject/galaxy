/* TODO:
    Use in test command

    bug: assertStepsRaise raise errors (all the way) when used in 'casperjs test .'
    normalize names of fns that use withFrame or then to 'then<action>'
    make any callbacks optional (that can be)

    Does it run:
        casperjs usertests.js --url='http://localhost:8080'
        casperjs usertests.js --url='http://localhost:8080' --return-json
        casperjs usertests.js --url='http://localhost:8080' --verbose=true --logLevel=debug
        casperjs test test/casperjs --url='http://localhost:8080'
        python casperjs_runner.py
        nosetests
        sh run_functional_tests.sh test/casperjs/
        sh run_functional_tests.sh
        (buildbot)

    BUGS:
        echo doesn't seem to work with python
        trace not showing for errors here

    what if:
        does an error saving a sshot bail the entire suite?

    Do the above handle:
        test script errors
        page errors (evaluate, find element, etc.)
        failures
        passes
        python errors

    Does test_runner:
        aggregate properly (passes, failures)
        fail on first = false

    Test:
        screenshotting
        save html/sshots to GALAXY_TEST_SAVE (test_runner)

    can we pass the entire test_env (instead of just url) from test_runner to sg?
    support method chaining pattern
    move selectors, text to class level (spaceghost)

    modules?
    May want to move common functions into PageObject-like subs of sg, e.g.:
        spaceghost.loginPage.logout()
        spaceghost.masthead.userMenu().login() // to click User -> Login

    more conv. functions:
        withMainFrame( callback )
        getMessageInfo returns *message elementInfo or null

    frames in casper are a PITA (as are steps in gen.): is there a better way to select within a frame w/o a step?
    waitFor (with progress and finally): a gen. form of waitForHdaState

*/
// ===================================================================
/** Extended version of casper object for use with Galaxy
 */

// ------------------------------------------------------------------- modules
var Casper = require( 'casper' ).Casper;
var utils = require( 'utils' );

// ------------------------------------------------------------------- inheritance
/** @class An extension of the Casper object with methods and overrides specifically
 *      for interacting with a Galaxy web page.
 *  @augments Casper
 */
function SpaceGhost(){
    SpaceGhost.super_.apply( this, arguments );
    this._init.apply( this, arguments );
}
utils.inherits( SpaceGhost, Casper );

//console.debug( 'CasperError:' + CasperError );

// ------------------------------------------------------------------- included libs
//??: can we require underscore, etc. from the ../../static/scripts/lib?
// yep!
//var _ = require( '../../static/scripts/libs/underscore' );
//var stooges = [{name : 'moe', age : 40}, {name : 'larry', age : 50}, {name : 'curly', age : 60}];
//console.debug( JSON.stringify( _.pluck(stooges, 'name') ) );
//exports._ = _;

// ------------------------------------------------------------------- error types
PageError.prototype = new CasperError();
PageError.prototype.constructor = CasperError;
/** @class Represents a javascript error on the page casper is browsing
 *      (as opposed to an error in the test script).
 */
function PageError(){
    CasperError.apply( this, arguments );
    this.name = "PageError";
}
SpaceGhost.prototype.PageError = PageError;

GalaxyError.prototype = new CasperError();
GalaxyError.prototype.constructor = CasperError;
/** @class Thrown when Galaxy has (gracefully?) indicated pilot error. */
function GalaxyError(){
    CasperError.apply( this, arguments );
    this.name = "GalaxyError";
}
SpaceGhost.prototype.GalaxyError = GalaxyError;

AlertError.prototype = new CasperError();
AlertError.prototype.constructor = CasperError;
/** @class Thrown when Galaxy has displayed a javascript alert. */
function AlertError(){
    CasperError.apply( this, arguments );
    this.name = "AlertError";
}
SpaceGhost.prototype.AlertError = AlertError;

// =================================================================== METHODS / OVERRIDES
// ------------------------------------------------------------------- set up
/** More initialization: cli, event handlers, etc.
 *  @param {Object} options  option hash
 *  @private
 */
SpaceGhost.prototype._init = function _init( options ){
    //console.debug( 'init, options:', JSON.stringify( options, null, 2 ) );

    //NOTE: cli will override in-script options
    this._setOptionsFromCli();

    // save errors for later output (needs to go before process CLI)
    /** cache of errors that have occurred
     *  @memberOf SpaceGhost */
    this.errors = [];
    this.on( 'error', function pushErrorToStack( msg, backtrace ){
        //this.debug( 'adding error to stack: ' + msg + ', trace:' + JSON.stringify( backtrace, null, 2 ) );
        this.errors.push({ msg: msg, backtrace: backtrace });
    });
    this._processCLIArguments();
    this._setUpEventHandlers();

    // inject these scripts by default
    this.debug( 'this.options.scriptDir:' + this.options.scriptDir );
    this.options.clientScripts = [
        this.options.scriptDir + '../../static/scripts/libs/jquery/jquery.js'
        //...
    ].concat( this.options.clientScripts );
    this.debug( 'clientScripts:\n' + this.jsonStr( this.options.clientScripts ) );

    this._loadModules();
};

/** Allow CLI arguments to set options if the proper option name is used.
 *  @example
 *      casperjs myscript.js --verbose=true --logLevel=debug
 *  @private
 */
SpaceGhost.prototype._setOptionsFromCli = function setOptionsFromCli(){
    // get and remove any casper options passed on the command line
    for( var optionName in this.options ){
        if( this.cli.has( optionName ) ){
            //console.debug( optionName + ':' + this.options[ optionName ] + ',' + this.cli.get( optionName ) );
            this.options[ optionName ] = this.cli.get( optionName );
            this.cli.drop( optionName );
        }
    }
};

// ------------------------------------------------------------------- cli args and options
/** Set up any SG specific options passed in on the cli.
 *  @private
 */
SpaceGhost.prototype._processCLIArguments = function _processCLIArguments(){
    //this.debug( 'cli: ' + this.jsonStr( this.cli ) );

    //TODO: init these programmitically
    var CLI_OPTIONS = {
        returnJsonOnly  : { defaultsTo: false, flag: 'return-json',    help: 'send output to stderr, json to stdout' },
        raisePageError  : { defaultsTo: true,  flag: 'page-error',     help: 'raise errors thrown on the page' },
        errorOnAlert    : { defaultsTo: false, flag: 'error-on-alert', help: 'throw errors when a page calls alert' },
        failOnAlert     : { defaultsTo: true,  flag: 'fail-on-alert',  help: 'fail a test when a page calls alert' }
        //screenOnError   : { defaultsTo: false, flag: 'error-screen',   help: 'capture a screenshot on a page error' },
        //textOnError     : { defaultsTo: false, flag: 'error-text',     help: 'output page text on a page error' },
        //htmlOnError     : { defaultsTo: false, flag: 'error-html',   help: 'output page html on a page error' }
        //htmlOnFail      : { defaultsTo: false, flag: 'fail-html',   help: 'output page html on a test failure' },
        //screenOnFail    : { defaultsTo: false, flag: 'fail-screen',   help: 'capture a screenshot on a test failure' }
    };

    // --url parameter required (the url of the server to test with)
    if( !this.cli.has( 'url' ) ){
        this.die( 'Test server URL is required - ' +
                  'Usage: capserjs <test_script.js> --url=<test_server_url>', 1 );
    }
    this.baseUrl = this.cli.get( 'url' );

    //TODO: move these handlers into _setUpEventHandlers
    // --return-json: supress all output except for JSON logs, test results, and errors at finish
    //  this switch allows a testing suite to send JSON data back via stdout (w/o logs, echos interferring)
    this.options.returnJsonOnly = CLI_OPTIONS.returnJsonOnly.defaultsTo;
    if( this.cli.has( CLI_OPTIONS.returnJsonOnly.flag ) ){
        this.options.returnJsonOnly = true;

        this._redirectOutputToStderr();
        // output json on fail-first error
        this.on( 'error', function outputJSONOnError( msg, backtrace ){
            //console.debug( 'return-json caught error' );
            if( spaceghost.options.exitOnError ){
                this.outputStateAsJson();
                spaceghost.exit( 1 );
            }
        });
        // non-error finshes/json-output are handled in run() for now
    }

    //TODO: remove boilerplate
    // --error-on-alert=false: don't throw an error if the page calls alert (default: true)
    this.options.raisePageError = CLI_OPTIONS.raisePageError.defaultsTo;
    if( this.cli.has( CLI_OPTIONS.raisePageError.flag ) ){
        this.options.raisePageError = this.cli.get( CLI_OPTIONS.raisePageError.flag );
    }

    // --error-on-alert=false: don't throw an error if the page calls alert (default: true)
    this.options.errorOnAlert = CLI_OPTIONS.errorOnAlert.defaultsTo;
    if( this.cli.has( CLI_OPTIONS.errorOnAlert.flag ) ){
        this.options.errorOnAlert = this.cli.get( CLI_OPTIONS.errorOnAlert.flag );
    }

    // --fail-on-alert=false: don't fail a test if the page calls alert (default: true)
    this.options.failOnAlert = CLI_OPTIONS.failOnAlert.defaultsTo;
    if( this.cli.has( CLI_OPTIONS.failOnAlert.flag ) ){
        this.options.failOnAlert = this.cli.get( CLI_OPTIONS.failOnAlert.flag );
    }

    /* not implemented
    // --error-page: print the casper.debugPage (the page's text) output on an error
    if( this.cli.has( 'error-page' ) ){
        this.on( 'page.error', this._saveTextOnErrorHandler );

    // --error-html: print the casper.debugHTML (the page's html) output on an error (mut.exc w error-text)
    } else if( this.cli.has( 'error-html' ) ){
        this.on( 'page.error', this._saveHtmlOnErrorHandler );
    }

    // --error-screen: capture the casper browser screen on an error
    if( this.cli.has( 'error-screen' ) ){
        this.on( 'page.error', this._saveScreenOnErrorHandler );
    }

    // --fail-html: print the casper.debugHTML (the page's html) output on an test failure
    // --fail-screen: print the casper browser screen output on an test failure
    */

    // get any fixture data passed in as JSON in args
    //  (NOTE: currently the 2nd arg (with the url being 1st?)
    this.fixtureData = ( this.cli.has( 0 ) )?( JSON.parse( this.cli.get( 0 ) ) ):( {} );
    this.debug( 'fixtureData:' + this.jsonStr( this.fixtureData ) );

};

/** Suppress the normal output from the casper object (echo, errors)
 *  @private
 */
SpaceGhost.prototype._suppressOutput = function _suppressOutput(){
    // currently (1.0) the only way to suppress test pass/fail messages
    //  (no way to re-route to log either - circular)
    this.echo = function( msg ){};

    //this.removeListener( 'error', this.listeners( 'error' )[0] );
    // clear the casper listener that outputs formatted error messages
    this.removeListener( 'error', this.listeners( 'error' )[1] );
};

/** Suppress the normal output from the casper object (echo, errors)
 *  @private
 */
SpaceGhost.prototype._redirectOutputToStderr = function _redirectOutputToStderr(){
    // currently (1.0) the only way to suppress test pass/fail messages
    //  (no way to re-route to log either - circular)
    var spaceghost = this;
    this.echo = function( msg ){
        spaceghost.stderr( msg );
    };

    //this.removeListener( 'error', this.listeners( 'error' )[0] );
    // clear the casper listener that outputs formatted error messages
    this.removeListener( 'error', this.listeners( 'error' )[1] );
};

/** Outputs logs, test results and errors in a single JSON formatted object to the console.
 */
SpaceGhost.prototype.outputStateAsJson = function outputStateAsJson(){
    var returnedJSON = {
        logs: this.result,
        testResults: this.test.testResults,
        errors: this.errors
    };
    // use phantomjs console since echo can't be used (suppressed - see init)
    console.debug( JSON.stringify( returnedJSON, null, 2 ) );
};


// ------------------------------------------------------------------- event handling
//note: using non-anon fns to allow removal if needed

/** 'load failed' Event handler for failed page loads that only records to the log
 *  @private
 */
SpaceGhost.prototype._loadFailedHandler = function _loadFailedHandler( object ){
    this.error( 'load.failed: ' + spaceghost.jsonStr( object ) );
    //TODO: throw error?
};

/** 'page.error' Event handler that re-raises as PageError
 *      NOTE: this has some special handling for DOM exc 12 which some casper selectors are throwing
 *          (even tho the selector still works)
 *  @throws {PageError} (with original's msg and backtrace)
 *  @private
 */
SpaceGhost.prototype._pageErrorHandler = function _pageErrorHandler( msg, backtrace ){
    // add a page error handler to catch page errors (what we're most interested with here)
    //  normally, casper seems to let these pass unhandled
    //console.debug( 'page.error:' + msg );

    //TODO:!! lots of casper selectors are throwing this - even tho they still work
    if( msg === 'SYNTAX_ERR: DOM Exception 12: An invalid or illegal string was specified.' ){
        void( 0 ); // no op

    } else if( this.options.raisePageError ){
        //console.debug( '(page) Error: ' + msg );
        //this.bypassOnError = true;

        // ugh - these bounce back and forth between here and phantom.page.onError
        //  if we don't do this replace you end up with 'PageError: PageError: PageError: ...'
        // I haven't found a great way to prevent the bouncing
        msg = msg.replace( 'PageError: ', '' );
        throw new PageError( msg, backtrace );
    }
};

/** 'timeout' Event handler for step/casper timeouts - raises as PageError
 *  @throws {PageError} Timeout occurred
 *  @private
 */
SpaceGhost.prototype._timeoutHandler = function _timeoutHandler(){
    console.debug( 'timeout' );
    //msg = msg.replace( 'PageError: ', '' );
    throw new PageError( 'Timeout occurred' );
};

/** 'alert' Event handler that raises an AlertError with the alert message
 *  @throws {AlertError} (the alert message)
 *  @private
 */
SpaceGhost.prototype._alertHandler = function _alertHandler( message ){
    //TODO: this still isn't working well...

    // casper info level already has outputs these
    //this.warning( this + '(page alert)\n"' + message + '"' );
    var ALERT_MARKER = '(page alert) ';

    // either throw an error or fail the test
    //console.debug( 'this.options.errorOnAlert: ' + this.options.errorOnAlert );
    this.stderr( 'this.options.failOnAlert: ' + this.options.failOnAlert );
    if( this.options.errorOnAlert ){
        throw new PageError( ALERT_MARKER + message );

    } else if( this.options.failOnAlert ){
        //this.test.fail( ALERT_MARKER + message );
        //this.test.fail();
        this.test.assert( false, 'found alert message' );
        //this.stderr( 'this.options.failOnAlert: ' + this.options.failOnAlert );
    }
};

/** 'error' Event handler that saves html from the errored page.
 *  @private
 */
SpaceGhost.prototype._saveHtmlOnErrorHandler = function _saveHtmlOnErrorHandler( msg, backtrace ){
    // needs to output to a file in GALAXY_SAVE
    //this.debugHTML();
};

/** 'error' Event handler that saves text from the errored page.
 *  @private
 */
SpaceGhost.prototype._saveTextOnErrorHandler = function _saveTextOnErrorHandler( msg, backtrace ){
    // needs to output to a file in GALAXY_SAVE
    //this.debugPage();
};

/** 'error' Event handler that saves a screenshot of the errored page.
 *  @private
 */
SpaceGhost.prototype._saveScreenOnErrorHandler = function _saveScreenOnErrorHandler( msg, backtrace ){
    // needs to output to a pic in GALAXY_SAVE
    //var filename = ...??
    //?? this.getCurrentUrl(), this.getCurrent
    //this.capture( filename );
};

/** Sets up event handlers.
 *  @private
 */
SpaceGhost.prototype._setUpEventHandlers = function _setUpEventHandlers(){
    //console.debug( '_setUpEventHandlers' );

    // ........................ page errors
    this.on( 'page.error',  this._pageErrorHandler );
    //this.on( 'load.failed', this._loadFailedHandler );
    this.on( 'timeout',  this._timeoutHandler );
    this.on( 'step.timeout',  this._timeoutHandler );
    this.on( 'waitFor.timeout',  this._timeoutHandler );

    // ........................ page info/debugging
    this.on( 'remote.alert',    this._alertHandler );

};

// ------------------------------------------------------------------- sub modules
/** Load sub modules (similar to casperjs.test)
 *  @requires User              modules/user.js
 *  @requires Tools             modules/tools.js
 *  @requires HistoryPanel      modules/historypanel.js
 *  @requires HistoryOptions    modules/historyoptions.js
 *  @private
 */
SpaceGhost.prototype._loadModules = function _loadModules(){
    this.user  = require( this.options.scriptDir + 'modules/user'  ).create( this );
    this.tools = require( this.options.scriptDir + 'modules/tools' ).create( this );
    this.historypanel = require( this.options.scriptDir + 'modules/historypanel' ).create( this );
    this.historyoptions = require( this.options.scriptDir + 'modules/historyoptions' ).create( this );
};

// =================================================================== PAGE CONTROL
/** An override of casper.start for additional set up.
 *      (Currently only used to change viewport)
 *  @see Casper#start
 */
SpaceGhost.prototype.start = function start(){
    var returned = Casper.prototype.start.apply( this, arguments );
    this.viewport( 1024, 728 );
    return returned;
};

/** An override of casper.open for additional page control.
 *      (Currently only used to change language headers)
 *  @see Casper#open
 */
SpaceGhost.prototype.open = function open(){
    //TODO: this can be moved to start (I think...?)
    //!! override bc phantom has it's lang as 'en-US,*' and galaxy doesn't handle the '*' well (server error)
    this.page.customHeaders = { 'Accept-Language': 'en-US' };
    return Casper.prototype.open.apply( this, arguments );
};

/** An override to provide json output and more informative error codes.
 *      Exits with 2 if a test has failed.
 *      Exits with 1 if some error has occurred.
 *      Exits with 0 if all tests passed.
 *  @see Casper#run run, boy, run (doesn't he fly?)
 */
SpaceGhost.prototype.run = function run( onComplete, time ){
    var new_onComplete = function(){
            onComplete.call( this );
            var returnCode = ( this.test.testResults.failed )?( 2 ):( 0 );

            // if --return-json is used: output json and exit
            //NOTE: used by the test runner to gather JSON test info from stdout
            if( this.options.returnJsonOnly ){
                // echo a string to indicate that tests are complete (used in casperjs_runner.py to stop process)
                this.echo( '# Tests complete' );
                this.outputStateAsJson();
                this.exit( returnCode );

            // otherwise, render the nice casper output and exit
            } else {
                this.test.renderResults( true, returnCode );
            }
        };
    Casper.prototype.run.call( this, new_onComplete, time );
};

/** Install a function as an error handler temporarily, run a function with steps, then remove the handler.
 *      A rough stand-in for try catch with steps.
 *      CatchFn will be passed error's msg and trace.
 *  @param {Function} stepsFn   a function that puts casper steps on the stack (then, thenOpen, etc.)
 *  @param {Function} catchFn   some portion of the correct error msg
 */
SpaceGhost.prototype.tryStepsCatch = function tryStepsCatch( stepsFn, catchFn ){
    // create three steps: 1) set up new error handler, 2) try the fn, 3) check for errors and rem. handler
    var originalExitOnError,
        originalErrorHandlers = [],
        errorMsg = '', errorTrace = [],
        recordError = function( msg, trace ){
            errorMsg = msg; errorTrace = trace;
        };

    // dont bail on the error (but preserve option), uninstall other handlers,
    //  and install hndlr to simply record msg, trace
    this.then( function(){
        originalExitOnError = this.options.exitOnError;
        this.options.exitOnError = false;
        originalErrorHandlers = this.popAllListeners( 'error' );
        this.on( 'error', recordError );
    });

    // try the step...
    this.then( stepsFn );

    this.then( function(){
        // ...and if an error was recorded call the catch with the info
        if( errorMsg ){
            catchFn.call( this, errorMsg, errorTrace );
        }
        // remove that listener either way, restore original handlers, and restore the bail option
        this.removeListener( 'error', recordError );
        this.addListeners( 'error', originalErrorHandlers );
        this.options.exitOnError = originalExitOnError;
    });
};

/** Hover over an element.
 *      NOTE: not for use with iframes (main, tool, history) - they need to re-calc
 *      for the iframe bounds and should be implemented in their own modules
 *  @param {String} selector        a css or xpath selector for an historyItemWrapper
 *  @param {Function} whenHovering  a function to call after the hover (will be scoped to spaceghost)
 */
SpaceGhost.prototype.hoverOver = function hoverOver( selector, whenHovering ){
    var elementInfo = this.getElementInfo( selector );
    this.page.sendEvent( 'mousemove', elementInfo.x + 1, elementInfo.y + 1 );
    whenHovering.call( this );
    return this;
};


// =================================================================== TESTING
//TODO: form fill doesn't work as casperjs would want it - often a button -> controller url
//TODO: saveScreenshot (to GALAXY_TEST_SAVE)
//TODO: saveHtml (to GALAXY_TEST_SAVE)

/** Casper has an (undocumented?) skip test feature. This is a conv. wrapper for that.
 */
SpaceGhost.prototype.skipTest = function(){
    throw this.test.SKIP_MESSAGE;
};

/** Test helper - within frame, assert selector, and assert text in selector
 *  @param {CasperJS selector} selector     what element in which to search for the text
 *  @param {String} text                    what text to search for
 *  @param {String} frame                   frame selector (gen. name) in which to search for selector (defaults to top)
 */
SpaceGhost.prototype.assertSelectorAndTextInFrame = function assertSelectorAndTextInFrame( selector, text, frame ){
    var spaceghost = this;
    function assertSelectorAndText( selector, text ){
        spaceghost.test.assertExists( selector,
            format( "found '%s' in %s", selector, frame ) );
        spaceghost.test.assertSelectorHasText( selector, text,
            format( "%s contains '%s'", selector, text ) );
    }
    if( frame ){
        this.withFrame( frame, function(){
            assertSelectorAndText( selector, text );
        });
    } else {
        assertSelectorAndText( selector, text );
    }
}

/** Test helper - within frame, assert errormessage, and assert text in errormessage
 *      *message is a common UI feedback motif in Galaxy (often displayed in the main panel)
 *  @param {String} message     what the message should contain
 *  @param {String} frame       frame selector (gen. name) in which to search for selector
 *      (defaults to 'galaxy_main')
 *  @param {CasperJS selector} messageSelector what element in which to search for the text
 *      (defaults to '.errormessage')
 */
SpaceGhost.prototype.assertErrorMessage = function assertSelectorAndTextInFrame( message, frame, messageSelector ){
    messageSelector = messageSelector || this.data.selectors.messages.error;
    frame = frame || this.data.selectors.frames.main;
    this.assertSelectorAndTextInFrame( messageSelector, message, frame );
};

/** Assert that stepsFn (which contains casper.then or some other casper step function) raises an error with
 *      a msg that contains some text (msgContains).
 *  @param {String} msgContains     some portion of the correct error msg
 *  @param {Function} stepsFn       a function that puts casper steps on the stack (then, thenOpen, etc.)
 */
SpaceGhost.prototype.assertStepsRaise = function assertStepsRaise( msgContains, stepsFn, removeOtherListeners ){
    // casper provides an assertRaises but this doesn't work well with steps
    //TODO:  *  @param {Boolean} removeOtherListeners option to remove other listeners while this fires
    var spaceghost = this;
    function testTheError( msg, backtrace ){
        spaceghost.test.assert( msg.indexOf( msgContains ) != -1, 'Raised correct error: ' + msg );
    }
    this.tryStepsCatch( stepsFn, testTheError );
};

/** Assert that a function causes a navigation request with (at least partially) the given url.
 *      NOTE: _should_ play well with steps (e.g. then, thenOpen, etc.)
 *  @param {String} url                 some portion of the expected url for the nav request
 *  @param {String} message             the assertion message
 *  @param {Function} fnThatRequests    a function that causes a navigation request (e.g. click a link)
 */
SpaceGhost.prototype.assertNavigationRequested = function assertNavigationRequested( expectedUrl, message,
                                                                                     fnThatRequests ){
    var requested = false;
    function captureNavReq( url, navigationType, navigationLocked, isMainFrame ){
        this.debug( 'Checking navigation.requested for url: ' + expectedUrl );
        // use || here to handle multiple requests, if any one url works -> test will pass
        requested = requested || ( url.indexOf( expectedUrl ) !== -1 );
    }
    this.then( function(){
        this.on( 'navigation.requested', captureNavReq );
    });
    this.then( function(){
        fnThatRequests.call( this );
    });
    this.then( function(){
        this.removeListener( 'navigation.requested', captureNavReq );
        this.test.assert( requested, message );
    });
};

/** Assert that a given string (toSearch) contains some given string (searchFor).
 *  @param {String} toSearch    the string to search
 *  @param {String} searchFor   the string to search for
 *  @param {String} msg         assertion msg to display
 */
SpaceGhost.prototype.assertTextContains = function assertTextContains( toSearch, searchFor, msg ){
    this.test.assert( toSearch.indexOf( searchFor ) !== -1, msg );
};

/** Assert that a given element has a given class.
 *  @param {CasperJS selector} selector what element to test
 *  @param {String} className  the class to test for (classes passed in with a leading '.' will have it trimmed)
 */
SpaceGhost.prototype.assertHasClass = function assertHasClass( selector, className, msg ){
    className = ( className[0] == '.' )?( className.slice( 1 ) ):( className );
    msg = msg || 'selector "' + selector + '" has class: "' + className + '"';
    var classes = this.getElementAttribute( selector, 'class' );
    this.test.assert( classes.indexOf( className ) !== -1, msg );
};

/** Assert that a given element doesn't have a given class.
 *  @param {CasperJS selector} selector what element to test
 *  @param {String} className  the class to test for (classes passed in with a leading '.' will have it trimmed)
 */
SpaceGhost.prototype.assertDoesntHaveClass = function assertDoesntHaveClass( selector, className, msg ){
    className = ( className[0] == '.' )?( className.slice( 1 ) ):( className );
    msg = msg || 'selector "' + selector + '" has class: "' + className + '"';
    var classes = this.getElementAttribute( selector, 'class' );
    this.test.assert( classes.indexOf( className ) === -1, msg );
};

// =================================================================== CONVENIENCE
/** Wraps casper.getElementInfo in try, returning null if element not found instead of erroring.
 *  @param {String} selector    css or xpath selector for the element to find
 *  @returns {Object|null}      element info if found, null if not
 */
SpaceGhost.prototype.elementInfoOrNull = function elementInfoOrNull( selector ){
    var found = null;
    try {
        found = this.getElementInfo( selector );
    } catch( err ){}
    return found;
};

/** Wraps casper.click in try to prevent error if element isn't found
 *  @param {String} selector    css or xpath selector for the element to find
 *  @returns {Boolean}          true if element found and clicked, false if not instead of erroring
 */
SpaceGhost.prototype.tryClick = function tryClick( selector ){
    var done = false;
    try {
        found = this.click( selector );
        done = true;
    } catch( err ){}
    return done;
};

// =================================================================== GALAXY CONVENIENCE


// =================================================================== MISCELAIN
/** Override capture to save to environ: GALAXY_TEST_SAVE (or passed in from CLI)
 *  @param {String} filename    the image filename
 */
SpaceGhost.prototype.capture = function capture( filename, clipRect_or_selector ){
    //TODO: override with saved output dir
    if( clipRect_or_selector && ( !utils.isClipRect( clipRect_or_selector ) ) ){
        return this.captureSelector( filename, clipRect_or_selector );
    }
    return Casper.prototype.capture.apply( this, arguments );
};

/** Pop all handlers for eventName from casper and return them in order.
 *  @param {String} eventName   the name of the event from which to remove handlers
 *  @returns {Function[]}       the array of functions no longer bound to the event
 */
SpaceGhost.prototype.popAllListeners = function popAllListeners( eventName ){
    var returnedListeners = this.listeners( eventName );
    this.removeAllListeners( eventName );
    return returnedListeners;
};

/** Add the given list of handler functions to the listener for eventName in order.
 *  @param {String} eventName   the name of the event to which to add handlers
 *  @param {Function[]} handlerArray an array of event handler functions to add
 */
SpaceGhost.prototype.addListeners = function addListeners( eventName, handlerArray ){
    for( var i=0; i<handlerArray.length; i++ ){
        this.addListener( eventName, handlerArray[i] );
    }
};

/** Send message to stderr using the phantom fs module.
 *  @param {String} the msg to output
 */
SpaceGhost.prototype.stderr = function( msg ){
    var fs = require( 'fs' );
    fs.write( '/dev/stderr', msg + '\n', 'w' );
};

// ------------------------------------------------------------------- convenience logging funcs
/** log using level = 'debug' and default namespace = 'spaceghost'
 */
SpaceGhost.prototype.debug = function( msg, namespace ){
    namespace = namespace || 'spaceghost';
    this.log( msg, 'debug', namespace );
};

/** log using level = 'info' and default namespace = 'spaceghost'
 */
SpaceGhost.prototype.info = function( msg, namespace ){
    namespace = namespace || 'spaceghost';
    this.log( msg, 'info', namespace );
};

/** log using level = 'warning' and default namespace = 'spaceghost'
 */
SpaceGhost.prototype.warning = function( msg, namespace ){
    namespace = namespace || 'spaceghost';
    this.log( msg, 'warning', namespace );
};

/** log using level = 'error' and default namespace = 'spaceghost'
 */
SpaceGhost.prototype.error = function( msg, namespace ){
    namespace = namespace || 'spaceghost';
    this.log( msg, 'error', namespace );
};

/** log despite logLevel settings, unless returnJsonOnly is set
 */
SpaceGhost.prototype.out = function( msg, namespace ){
    namespace = namespace || 'spaceghost';
    if( !this.options.returnJsonOnly ){
        console.debug( msg );
    }
};

/** JSON formatter
 */
SpaceGhost.prototype.jsonStr = function( obj ){
    return JSON.stringify( obj, null, 2 );
};

/** output the JSON of the selector (or null if not found) to debug level
 */
SpaceGhost.prototype.debugElement = function debugElement( selector ){
    this.debug( selector + ':\n' + this.jsonStr( this.elementInfoOrNull( selector ) ) );
};

/** Debug SG itself
 */
SpaceGhost.prototype.debugMe = function(){
    console.debug( 'options:\n' + this.jsonStr( this.options ) );
    console.debug( 'cli:\n' + this.jsonStr( this.cli ) );
};

/** Get the last error on the stack.
 */
SpaceGhost.prototype.lastError = function(){
    return this.errors[( this.errors.length - 1 )];
};

/** String representation
 */
SpaceGhost.prototype.toString = function(){
    var currentUrl = '';
    try {
        currentUrl = this.getCurrentUrl();
    } catch( err ){}
    return 'SpaceGhost(' + currentUrl + ')';
};

/** Load and parse a JSON file into an object.
 *  @param filepath     filepath relative to the current scriptDir
 *  @returns the object parsed
 */
SpaceGhost.prototype.loadJSONFile = function loadJSONFile( filepath ){
    //precondition: filepath is relative to script dir
    filepath = this.options.scriptDir + filepath;
    return JSON.parse( require( 'fs' ).read( filepath ) );
};

/** Load and parse a JSON file into an object.
 *  @param filepath     filepath relative to the current scriptDir
 *  @param object       the object to write
 *  @param mode         'w' for a new file, 'a' for append
 */
SpaceGhost.prototype.writeJSONFile = function writeJSONFile( filepath, object, mode ){
    mode = mode || 'w';
    //precondition: filepath is relative to script dir
    filepath = this.options.scriptDir + filepath;
    return require( 'fs' ).write( filepath, this.jsonStr( object ), mode );
};


// =================================================================== TEST DATA
/** General use selectors, labels, and text. Kept here to allow a centralized location.
 */
SpaceGhost.prototype.data = {
    selectors : {
        tooltipBalloon          : '.bs-tooltip',
        editableText            : '.editable-text',
        editableTextInput       : 'input#renaming-active',
        masthead : {
            userMenu : {
                userEmail       : 'a #user-email',
                userEmail_xpath : '//a[contains(text(),"Logged in as")]/span["id=#user-email"]'
            }
        },
        frames : {
            main    : 'galaxy_main',
            tools   : 'galaxy_tools',
            history : 'galaxy_history'
        },
        messages : {
            all         : '[class*="message"]',
            error       : '.errormessage',
            done        : '.donemessage',
            donelarge   : '.donemessagelarge'
        },
        loginPage : {
            form            : 'form#login',
            submit_xpath    : "//input[@value='Login']",
            url_regex       : /\/user\/login/
        },
        registrationPage : {
            form            : 'form#registration',
            submit_xpath    : "//input[@value='Submit']"
        },
        tools : {
            general : {
                form : 'form#tool_form',
                executeButton_xpath : '//input[@value="Execute"]'
            },
            upload : {
                fileInput   : 'files_0|file_data'   // is this general?
            }
        }
    },
    labels : {
        masthead : {
            menus : {
                user : 'User'
            },
            userMenu : {
                register    : 'Register',
                login       : 'Login',
                logout      : 'Logout'
            }
        },
        tools : {
            upload : {
                panelLabel  : 'Upload File'
            }
        }
    },
    text : {
        registrationPage : {
            badEmailError   : 'Enter a real email address'
        },
        upload : {
            success : 'The following job has been successfully added to the queue'
        }
    }
};

/*
SpaceGhost.prototype.selectors = {
    tooltipBalloon          : '.bs-tooltip',
    editableText            : '.editable-text',
    editableTextInput       : 'input#renaming-active',
    masthead : {
        userMenu : {
            userEmail       : 'a #user-email',
            userEmail_xpath : '//a[contains(text(),"Logged in as")]/span["id=#user-email"]'
        }
    },
    frames : {
        main    : 'galaxy_main',
        tools   : 'galaxy_tools',
        history : 'galaxy_history'
    },
    messages : {
        all         : '[class*="message"]',
        error       : '.errormessage',
        done        : '.donemessage',
        donelarge   : '.donemessagelarge'
    },
    loginPage : {
        form            : 'form#login',
        submit_xpath    : "//input[@value='Login']",
        url_regex       : /\/user\/login/
    },
    registrationPage : {
        form            : 'form#registration',
        submit_xpath    : "//input[@value='Submit']"
    },
    tools : {
        general : {
            form : 'form#tool_form',
            executeButton_xpath : '//input[@value="Execute"]'
        },
        upload : {
            fileInput   : 'files_0|file_data'   // is this general?
        }
    }
};

SpaceGhost.prototype.labels = {
    masthead : {
        menus : {
            user : 'User'
        },
        userMenu : {
            register    : 'Register',
            login       : 'Login',
            logout      : 'Logout'
        }
    },
    tools : {
        upload : {
            panelLabel  : 'Upload File'
        }
    }
};

SpaceGhost.prototype.text = {
    registrationPage : {
        badEmailError   : 'Enter a real email address'
        //...
    },
    upload : {
        success : 'The following job has been successfully added to the queue'
    }
};
*/

// =================================================================== EXPORTS
exports.SpaceGhost  = SpaceGhost;
exports.PageError   = PageError;
exports.GalaxyError = GalaxyError;
exports.AlertError  = AlertError;
/** creation function
 */
exports.create = function create(options) {
    "use strict";
    return new SpaceGhost(options);
};
