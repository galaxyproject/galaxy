/* TODO:

    normalize names of steps to 'then<action>' or with
    support method chaining pattern
    move selectors, text to class level (spaceghost.data, module.data)
    make any callbacks optional (that can be)

    BUGS:
        bug: filenames in backtrace not bubbling up properly
        bug: assertStepsRaise used with wait throws more than once
        trace filename not showing for errors here
        ?: assertStepsRaise raise errors (all the way) when used in 'casperjs test .'

    Does casperjs_runner:
        work with fail on first = false

    FEATURE CREEP:
        assertTooltip( selector, textShouldBe ){
            hoverover selector
            assert tooltip
            assert tooltip text
            hoverover 0, 0 // clear tooltip
        }
        screenshotting on all step.complete (see captureSteps.js)
        save html/sshots to GALAXY_TEST_SAVE (test_runner)

    Use in test command
    can we pass the entire test_env (instead of just url) from test_runner to sg?
*/
// ===================================================================
/** Extended version of casper object for use with Galaxy
 */

// ------------------------------------------------------------------- modules
var require = patchRequire( require ),
    Casper = require( 'casper' ).Casper,
    system = require( 'system' ),
    fs = require( 'fs' ),
    utils = require( 'utils' );

// ------------------------------------------------------------------- inheritance
/** @class An extension of the Casper object with methods and overrides specifically
 *      for interacting with a Galaxy web page.
 */
function SpaceGhost(){
    // an empty object just to store functions in a prototype for patching onto a casper isntance
}

exports.fromCasper = function fromCasper( casper, options ){
    "use strict";
    // patch the sg prototype over the casper instance proto
    for( var k in SpaceGhost.prototype ){
        if( SpaceGhost.prototype.hasOwnProperty( k ) ){
            // monkey patch directly onto the casper instance - we need the prototype
            casper[ k ] = SpaceGhost.prototype[ k ];
        }
    }
    casper._init( options );
    return casper;
};

// =================================================================== METHODS / OVERRIDES
/** String representation */
SpaceGhost.prototype.toString = function(){
    var currentUrl = '';
    try {
        currentUrl = this.getCurrentUrl();
    } catch( err ){}
    return 'SpaceGhost(' + currentUrl + ')';
};

// ------------------------------------------------------------------- set up
/** More initialization: cli, event handlers, etc.
 *  @param {Object} options  option hash
 *  @private
 */
SpaceGhost.prototype._init = function _init( options ){
    ////console.debug( 'init, options:', JSON.stringify( options, null, 2 ) );
    //
    //NOTE: cli will override in-script options
    this._setOptionsFromCli();

    this.on( 'step.error', function stepErrorHandler( error ){
        //console.debug( 'step.error: ' + error.name + ', ' + error.message );
        this.errors.push({ msg: error.message, backtrace: error.stackArray });
        //if( error.name !== 'AssertionError' ){
        //    throw error;
        //}
    });
    // save errors for later output
    //  set this now so ALL errors are processed well (including errors during set up)
    /** cache of errors that have occurred */
    this.errors = [];
    this.on( 'error', function pushErrorToStack( msg, backtrace ){
        //this.debug( 'adding error to stack: ' + msg + ', trace:' + this.jsonStr( backtrace ) );
        this.errors.push({ msg: msg, backtrace: backtrace });
    });
    this._processCLIArguments();
    this._setUpEventHandlers();

    /** cache of test failures */
    this.failures = [];
    /** cache of test passes */
    this.passes = [];

    // inject these scripts by default
    this.options.clientScripts = [
        //'../../static/scripts/libs/jquery/jquery.js'
        //...
    ].concat( this.options.clientScripts );
    this.debug( 'clientScripts: ' + this.jsonStr( this.options.clientScripts ) );

    this.changeToScriptDir();
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
            //console.debug( optionName + ': '
            //    + '(was) ' + this.options[ optionName ]
            //    + ', (now) ' + this.cli.get( optionName ) );
            this.options[ optionName ] = this.cli.get( optionName );
            this.cli.drop( optionName );
        }
    }
};

/** Change the working directory to that of the current script */
SpaceGhost.prototype.changeToScriptDir = function changeToScriptDir(){
    var fs = require( 'fs' ),
        args = require( 'system' ).args,
        scriptPathArray = args[4].split( '/' );
    //console.debug( this.jsonStr( scriptPathArray ) );

    if( scriptPathArray.length > 1 ){
        scriptPathArray.pop();
        //console.debug( this.jsonStr( scriptPathArray.join( '/' ) ) );
        fs.changeWorkingDirectory( scriptPathArray.join( '/' ) );
    }
};

// ------------------------------------------------------------------- cli args and options
/** Set up any SG specific options passed in on the cli.
 *  @private
 */
SpaceGhost.prototype._processCLIArguments = function _processCLIArguments(){
    //this.debug( 'cli: ' + this.jsonStr( this.cli ) );

    //TODO: init these programmitically
    //TODO: need to document these
    var CLI_OPTIONS = {
        returnJsonOnly  : { defaultsTo: false, flag: 'return-json',    help: 'send output to stderr, json to stdout' },
        raisePageError  : { defaultsTo: true,  flag: 'page-error',     help: 'raise errors thrown on the page' },
        errorOnAlert    : { defaultsTo: false, flag: 'error-on-alert', help: 'throw errors when a page calls alert' },
        failOnAlert     : { defaultsTo: true,  flag: 'fail-on-alert',  help: 'fail a test when a page calls alert' },
        //screenOnError   : { defaultsTo: false, flag: 'error-screen',   help: 'capture a screenshot on a page error' },
        //textOnError     : { defaultsTo: false, flag: 'error-text',     help: 'output page text on a page error' },
        //htmlOnError     : { defaultsTo: false, flag: 'error-html',   help: 'output page html on a page error' }
        //htmlOnFail      : { defaultsTo: false, flag: 'fail-html',   help: 'output page html on a test failure' },
        //screenOnFail    : { defaultsTo: false, flag: 'fail-screen',   help: 'capture a screenshot on a test failure' }
        logNamespace    : { defaultsTo: false,  flag: 'log-namespace', help: 'filter log messages to this namespace' },

        adminUser       : { defaultsTo: null,   flag: 'admin', help: 'JSON string with email and password of admin' }
    };

    // no switches/hardcoded options:
    this.options.adminPassword = 'testuser';

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
        this.test.removeAllListeners( 'tests.complete' );

        // output json on fail-first error
        this.on( 'error', function outputJSONOnError( msg, backtrace ){
            if( spaceghost.options.exitOnError ){
                this._sendStopSignal();
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

    // get any fixture data passed in as JSON (e.g. --data='{ "one": 1 }')
    this.fixtureData = ( this.cli.has( 'data' ) )?( JSON.parse( this.cli.get( 'data' ) ) ):( {} );
    this.debug( 'fixtureData:' + this.jsonStr( this.fixtureData ) );

    /** only output log messages with the given namespace */
    this.options.logNamespace = CLI_OPTIONS.logNamespace.defaultsTo;
    if( this.cli.has( CLI_OPTIONS.logNamespace.flag ) ){
        this.options.logNamespace = this.cli.get( CLI_OPTIONS.logNamespace.flag );
        this._setLogNamespaceFilter( this.options.logNamespace );
    }

    /** email and password JSON string for admin user */
    this.options.adminUser = CLI_OPTIONS.adminUser.defaultsTo;
    if( this.cli.has( CLI_OPTIONS.adminUser.flag ) ){
        this.options.adminUser = JSON.parse( this.cli.get( CLI_OPTIONS.adminUser.flag ) );
        this.warning( 'Using admin user from CLI: ' + this.jsonStr( this.options.adminUser ) );
    }

};

/** Suppress the normal output from the casper object (echo, errors)
 *  @param {String} namespace   the namespace to filter log msgs to
 *  @private
 */
SpaceGhost.prototype._setLogNamespaceFilter = function _setLogNamespaceFilter( namespace ){
    var regex = RegExp( '\\[' + namespace + '\\]' );
    // this will fail if there's [namespace] in the actual message - NBD
    this.setFilter( 'log.message', function( message ) {
        return ( message.match( regex ) )?( message ):( ' ' );
    });
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

    // clear the casper listener that outputs formatted error messages
    this.removeListener( 'error', this.listeners( 'error' )[0] );
    //this.removeListener( 'error', this.listeners( 'error' )[1] );
};

/** Outputs logs, test results and errors in a single JSON formatted object to the console.
 */
SpaceGhost.prototype.outputStateAsJson = function outputStateAsJson(){
    var returnedJSON = {
        logs        : this.result,
        passes      : this.passes,
        failures    : this.failures,
        errors      : this.errors
    };
    // use phantomjs console since echo can't be used (suppressed - see init)
    console.debug( JSON.stringify( returnedJSON, null, 2 ) );
};


// ------------------------------------------------------------------- event handling
/** Sets up event handlers.
 *  @private
 */
SpaceGhost.prototype._setUpEventHandlers = function _setUpEventHandlers(){
    //console.debug( '_setUpEventHandlers' );
    var spaceghost = this;

    // ........................ page errors
    this.on( 'page.error',  this._pageErrorHandler );
    //this.on( 'load.failed', this._loadFailedHandler );

    // ........................ page info/debugging
    this.on( 'remote.alert',    this._alertHandler );
    //this.on( 'remote.message',       function( msg ){ this.debug( 'remote: ' + msg ); });
    //this.on( 'navigation.requested', function( url ){ this.debug( 'navigation: ' + url ); });

    // ........................ timeouts
    this._setUpTimeoutHandlers();

    // ........................ test results
    this.test.on( "fail", function( failure ){
        spaceghost.failures.push( failure );
    });
    this.test.on( "success", function( pass ){
        spaceghost.passes.push( pass );
    });
};

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

/** 'timeout' Event handler for step/casper timeouts - raises as PageError
 *  @throws {PageError} Timeout occurred
 *  @private
 */
SpaceGhost.prototype._timeoutHandler = function _timeoutHandler(){
    //msg = msg.replace( 'PageError: ', '' );
    throw new PageError( 'Timeout occurred' );
};

/** By default, Casper dies on timeouts - which kills our runner. Throw errors instead.
 *  @private
 */
SpaceGhost.prototype._setUpTimeoutHandlers = function _setUpTimeoutHandlers(){
    this.options.onStepTimeout = function _onStepTimeout( timeout, stepNum ){
        throw new PageError( "Maximum step execution timeout exceeded for step " + stepNum );
    };
    this.options.onTimeout = function _onTimeout( timeout ){
        throw new PageError( "Script timeout reached: " + timeout );
    };
    this.options.onWaitTimeout = function _onWaitTimeout( timeout ){
        throw new PageError( "Wait timeout reached: " + timeout );
    };
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
    this.user           = require( './modules/user'  ).create( this );
    this.tools          = require( './modules/tools' ).create( this );
    this.historypanel   = require( './modules/historypanel' ).create( this );
    this.historyoptions = require( './modules/historyoptions' ).create( this );
    this.api            = require( './modules/api' ).create( this );
};

// =================================================================== PAGE CONTROL
// ------------------------------------------------------------------- overrides
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
    //!! override bc phantom has its lang as 'en-US,*' and galaxy doesn't handle the '*' well (server error)
    this.page.customHeaders = { 'Accept-Language': 'en-US' };
    return Casper.prototype.open.apply( this, arguments );
};

/** Send a signal that we're done - used by py wrapper subprocess.
 *  @private
 */
SpaceGhost.prototype._sendStopSignal = function _sendStopSignal(){
    this.echo( '# Stopping' );
};

/** An override to provide json output and more informative error codes.
 *      Exits with 2 if a test has failed.
 *      Exits with 1 if some error has occurred.
 *      Exits with 0 if all tests passed.
 */
SpaceGhost.prototype.run = function run( onComplete, time ){
    var oldFn = spaceghost.test.done;
    spaceghost.test.done = function(){
        oldFn.call( spaceghost.test );
    }
    var new_onComplete = function(){
        onComplete.call( this );
        //var returnCode = ( this.test.getFailures() )?( 2 ):( 0 );
        var returnCode = ( this.failures.length )?( 2 ):( 0 );

        // if --return-json is used: output json and exit
        //NOTE: used by the test runner to gather JSON test info from stdout
        if( this.options.returnJsonOnly ){
            // echo a string to indicate that tests are complete (used in casperjs_runner.py to stop process)
            this._sendStopSignal();
            this.outputStateAsJson();
            this.exit( returnCode );

        // otherwise, render the nice casper output and exit
        //} else {
        //    this.test.renderResults( true, returnCode );
        }
    };
    Casper.prototype.run.call( this, new_onComplete, time );
    //Casper.prototype.run.call( this, onComplete, time );
};

// ------------------------------------------------------------------- home page
/** Wait for the homepage/index/Analyze Data to load fully.
 */
SpaceGhost.prototype.openHomePage = function openHomePage( then, delay ){
//TODO: delay doesn't seem to work
    this.thenOpen( this.baseUrl, function _openHomePage(){
        this.waitFor(
            function waitForCheck(){
                return this.homePageIsLoaded();
            },
            then,
            function openHomePageTimeout(){
                throw new GalaxyError( 'Homepage timed out' );
            },
            delay
        );
    });
    return this;
};

/** Check for visibility of main home page elements: masthead, tool menu, history panel.
 */
SpaceGhost.prototype.homePageIsLoaded = function homePageIsLoaded(){
    //this.debug( 'homePageIsLoaded: ' + [
    //    this.visible( '#masthead' ),
    //    this.visible( this.data.selectors.toolMenu.container ),
    //    this.visible( '#current-history-panel' )].join( ', ' ) );
    return ( this.visible( '#masthead' )
          && this.visible( this.data.selectors.toolMenu.container )
          && this.visible( '#current-history-panel' ) );
};

// ------------------------------------------------------------------- try step
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
        errorCaught,
        recordError = function( error ){
            errorCaught = error;
        };

    // dont bail on the error (but preserve option), uninstall other handlers,
    //  and install hndlr to simply record msg, trace
    this.then( function replaceHandlers(){
        originalExitOnError = this.options.exitOnError;
        this.options.exitOnError = false;
        originalErrorHandlers = this.popAllListeners( 'step.error' );
        this.on( 'step.error', recordError );
    });

    // try the step...
    this.then( stepsFn );
    //TODO: this doesn't work well with wait for (see upload-tests.js)
    //  possibly combine above and below?

    this.then( function catchWrapper(){
        // remove that listener either way, restore original handlers, and restore the bail option
        this.removeListener( 'step.error', recordError );
        this.addListeners( 'step.error', originalErrorHandlers );
        this.options.exitOnError = originalExitOnError;
        // ...and if an error was recorded call the catch with the info
        if( errorCaught ){
            catchFn.call( this, errorCaught );
        }
    });
};


// ------------------------------------------------------------------- misc
/** Hover over an element.
 *      NOTE: not for use with iframes (main, tool, history) - they need to re-calc
 *      for the iframe bounds and should be implemented in their own modules
 *  @param {String} selector        a css or xpath selector for an historyItemWrapper
 *  @param {Function} whenHovering  a function to call after the hover (will be scoped to spaceghost)
 */
SpaceGhost.prototype.hoverOver = function hoverOver( selector, whenHovering ){
    var elementInfo = this.getElementInfo( selector );
    this.page.sendEvent( 'mousemove', elementInfo.x + 1, elementInfo.y + 1 );
    if( whenHovering ){ whenHovering.call( this ); }
    return this;
};

/** Wait for a navigation request then call a function.
 *      NOTE: uses string indexOf - doesn't play well with urls like [ 'history', 'history/bler' ]
 *  @param {String} urlToWaitFor    the url to wait for (rel. to spaceghost.baseUrl)
 *  @param {Function} then          the function to call after the nav request
 *  @param {Function} timeoutFn     the function to call on timeout (optional)
 *  @param {Integer} waitMs         manual setting of ms to wait (optional)
 */
SpaceGhost.prototype.waitForNavigation = function waitForNavigation( urlToWaitFor, then, timeoutFn, waitMs ){
    return this.waitForMultipleNavigation( [ urlToWaitFor ], then, timeoutFn, waitMs );
};

/** Wait for a multiple navigation requests then call a function.
 *      NOTE: waitFor time is set to <number of urls> * options.waitTimeout
 *      NOTE: uses string indexOf - doesn't play well with urls like [ 'history', 'history/bler' ]
 *  @param {String[]} urlsToWaitFor the relative urls to wait for
 *  @param {Function} then          the function to call after the nav request
 *  @param {Function} timeoutFn     the function to call on timeout (optional)
 *  @param {Integer} waitMs         manual setting of ms to wait (optional)
 */
SpaceGhost.prototype.waitForMultipleNavigation = function waitForMultipleNavigation( urlsToWaitFor,
        then, timeoutFn, waitMs ){
    waitMs = waitMs || ( this.options.waitTimeout * urlsToWaitFor.length );

    this.info( 'waiting for navigation: ' + this.jsonStr( urlsToWaitFor ) + ', timeout after: ' + waitMs );
    function urlMatches( urlToMatch, url ){
        return ( url.indexOf( spaceghost.baseUrl + '/' + urlToMatch ) !== -1 );
    }

    function catchNavReq( url ){
        this.debug( 'nav.req: ' + url );
        for( var i=( urlsToWaitFor.length - 1 ); i>=0; i -= 1 ){
            //this.debug( '\t checking: ' + urlsToWaitFor[i] );
            if( urlMatches( urlsToWaitFor[i], url ) ){
                this.info( 'Navigation (' + urlsToWaitFor[i] + ') found: ' + url );
                urlsToWaitFor.splice( i, 1 );
            }
        }
        //this.debug( 'urlsToWaitFor: ' + this.jsonStr( urlsToWaitFor ) );
    }
    this.on( 'navigation.requested', catchNavReq );

    this.waitFor(
        function checkForNav(){
            if( urlsToWaitFor.length === 0 ){
                this.removeListener( 'navigation.requested', catchNavReq );
                return true;
            }
            return false;
        },
        function callThen(){
            if( utils.isFunction( then ) ){ then.call( this ); }
        },
        function timeout(){
            this.removeListener( 'navigation.requested', catchNavReq );
            if( utils.isFunction( timeoutFn ) ){ timeoutFn.call( this, urlsToWaitFor ); }
        },
        waitMs
    );
    return this;
};


// ------------------------------------------------------------------- iframes, damnable iframes
/** Version of Casper#withFrame for the main iframe.
 *  @param {Function} then  function called when in the frame
 */
SpaceGhost.prototype.withMainPanel = function withMainPanel( then ){
    return this.withFrame( this.data.selectors.frames.main, then );
};

/** Jumps into given frame, exectutes fn, and jumps back to original frame.
 *      NOTE: this doesn't use steps like casper's withFrame but uses phantom's switchTo[Main]Frame,
 *      so you can safely return values from fn
 *  @param {Selector} frame the selector for the frame to jump to (use 'top' to jump to top frame)
 *  @param {Function} fn    function called when in the frame
 *  @returns {Any} the return value of fn
 */
SpaceGhost.prototype.jumpToFrame = function jumpToFrame( frame, fn ){
    //TODO: plainly maintains that main frame has no frameName, namely: ''
    var origFrameName = this.page.frameName || 'top';
    //(??) if we're already there...
    if( origFrameName === frame ){ return fn.call( this ); }

    if( origFrameName ){
        // if there's a frame name we assume we're in some child frame,
        //  we need to move up before moving into the new frame
        this.page.switchToMainFrame();
    }
    if( frame !== 'top' ){ this.page.switchToFrame( frame ); }
    var returned = fn.call( this );

    // move back into main, then into the orig child frame if given
    if( frame !== 'top' ){ this.page.switchToMainFrame(); }
    if( origFrameName ){
        this.page.switchToFrame( origFrameName );
    }
    return returned;
};

/** Jumps into main frame, exectutes fn, and jumps back to original frame.
 *  @param {Selector} frame the selector for the frame to jump to
 *  @param {Function} fn    function called when in the frame
 *  @returns {Any} the return value of fn
 */
SpaceGhost.prototype.jumpToMain = function jumpToMain( fn ){
    return this.jumpToFrame( this.data.selectors.frames.main, fn );
};

/** Jumps into top frame, exectutes fn, and jumps back to original frame.
 *  @param {Selector} frame the selector for the frame to jump to
 *  @param {Function} fn    function called when in the frame
 *  @returns {Any} the return value of fn
 */
SpaceGhost.prototype.jumpToTop = function jumpToTop( fn ){
    return this.jumpToFrame( 'top', fn );
};


// =================================================================== TESTING
//TODO: form fill doesn't work as casperjs would want it - often a button -> controller url
//TODO: saveScreenshot (to GALAXY_TEST_SAVE)
//TODO: saveHtml (to GALAXY_TEST_SAVE)

/** Checks whether fn raises an error with a message that contains a given string.
 *      NOTE: DOES NOT work with steps. @see SpaceGhost#assertStepsRaise
 *  @param {Function} testFn        a function that may throw an error
 *  @param {String} errMsgContains  some portion of the correct error msg
 *  @private
 */
SpaceGhost.prototype._raises = function _raises( testFn, errMsgContains ){
    var failed = false;
    try {
        testFn.call( this );
    } catch( err ){
        if( err.message.indexOf( errMsgContains ) !== -1 ){
            failed = true;

        // re-raise other, non-searched-for errors
        } else {
            throw err;
        }
    }
    return failed;
};

/** Simple assert raises.
 *      NOTE: DOES NOT work with steps. @see SpaceGhost#assertStepsRaise
 *  @param {Function} testFn        a function that may throw an error
 *  @param {String} errMsgContains  some portion of the correct error msg
 *  @param {String} msg             assertion message to display
 */
SpaceGhost.prototype.assertRaises = function assertRaises( testFn, errMsgContains, msg ){
    return this.test.assert( this._raises( testFn, errMsgContains ), msg  );
};

/** Simple assert does not raise.
 *      NOTE: DOES NOT work with steps. @see SpaceGhost#assertStepsRaise
 *  @param {Function} testFn        a function that may throw an error
 *  @param {String} errMsgContains  some portion of the correct error msg
 *  @param {String} msg             assertion message to display
 */
SpaceGhost.prototype.assertDoesntRaise = function assertDoesntRaise( testFn, errMsgContains, msg ){
    return this.test.assert( !this._raises( testFn, errMsgContains ), msg  );
};

/** Casper has an (undocumented?) skip test feature. This is a conv. wrapper for that.
 */
SpaceGhost.prototype.skipTest = function skipTest( msg ){
    this.warn( 'Skipping test. ' + msg );
    //throw this.test.SKIP_MESSAGE;
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
};

/** Test helper - assert selector exists, is visible, and has text
 *  @param {CasperJS selector} selector     what element in which to search for the text
 *  @param {String} text                    what text to search for (optional)
 */
SpaceGhost.prototype.assertVisibleWithText = function assertVisibleWithText( selector, text, msg ){
    var visible = this.test.casper.visible( selector ),
        hasText = this.test.casper.fetchText( selector ).indexOf( text ) !== -1;
    this.test.assert( visible && hasText, msg );
};

/** Test helper - within frame, assert errormessage, and assert text in errormessage
 *      *message is a common UI feedback motif in Galaxy (often displayed in the main panel)
 *  @param {String} message     what the message should contain
 *  @param {String} frame       frame selector (gen. name) in which to search for selector
 *      (defaults to 'galaxy_main')
 *  @param {CasperJS selector} messageSelector what element in which to search for the text
 *      (defaults to '.errormessage')
 */
SpaceGhost.prototype.assertErrorMessage = function assertErrorMessage( message, frame, messageSelector ){
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
    function testTheError( errorCaught ){
        if( errorCaught.message.indexOf( msgContains ) !== -1 ){
            spaceghost.test.pass( 'Raised correct error: ' + errorCaught.message );
        } else {
            throw errorCaught;
        }
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
    className = ( className[0] === '.' )?( className.slice( 1 ) ):( className );
    msg = msg || 'selector "' + selector + '" has class: "' + className + '"';
    var classes = this.getElementAttribute( selector, 'class' );
    this.test.assert( classes.indexOf( className ) !== -1, msg );
};

/** Assert that a given element doesn't have a given class.
 *  @param {CasperJS selector} selector what element to test
 *  @param {String} className  the class to test for (classes passed in with a leading '.' will have it trimmed)
 */
SpaceGhost.prototype.assertDoesntHaveClass = function assertDoesntHaveClass( selector, className, msg ){
    className = ( className[0] === '.' )?( className.slice( 1 ) ):( className );
    msg = msg || 'selector "' + selector + '" has class: "' + className + '"';
    var classes = this.getElementAttribute( selector, 'class' );
    this.test.assert( classes.indexOf( className ) === -1, msg );
};

/** Return true if object has all keys in keysArray (useful in API testing of return values).
 *  @param {Object} object       the object to test
 *  @param {String[]} keysArray  an array of expected keys
 */
SpaceGhost.prototype.hasKeys = function hasKeys( object, keysArray ){
    if( !utils.isObject( object ) ){ return false; }
    for( var i=0; i<keysArray.length; i += 1 ){
        if( !object.hasOwnProperty( keysArray[i] ) ){
            return false;
        }
    }
    return true;
};

/** Returns count of keys in object. */
SpaceGhost.prototype.countKeys = function countKeys( object ){
    if( !utils.isObject( object ) ){ return 0; }
    var count = 0;
    for( var key in object ){
        if( object.hasOwnProperty( key ) ){ count += 1; }
    }
    return count;
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
/** Override echo to not print empty lines (only way to do log filtering)
 *  @param {String} msg    the msg to output
 *  @param {String} style  the casper style to use
 */
SpaceGhost.prototype.echo = function echo( msg, style ){
    if( msg.trim() ){
        Casper.prototype.echo.call( this, msg, style );
    }
};

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

/** Capture a progression of sshots with a delay inbetween.
 *  @param {String} filepath
 *  @param {String} filename
 *  @param {String} ext
 *  @param {Integer} count
 *  @param {Integer} delay
 */
SpaceGhost.prototype.captureProgression = function captureProgression( filepath, filename, ext, count, delay ){
    if( !count ){ return this; }
    var spaceghost = this,
        interval = setInterval( function(){
            var imageName = filepath + filename + '.' + count + '.' + ext;
            spaceghost.capture( imageName );
            count -= 1;
            if( count <= 0 ){ clearInterval( interval ); }
        }, delay );
    return this;
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
    if( msg.trim() ){
        system.stderr.writeLine( msg );
    }
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

// ------------------------------------------------------------------- debugging
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

/** return a more limited version of a Casper ElementInfo object.
 *  @params {Casper ElementInfo} info   the Casper ElementInfo object to simplify
 *  @returns {Object} of the form { attributes: <attributes>, text: <text> }
 */
SpaceGhost.prototype.quickInfo = function quickInfo( info ){
    return { attributes: info.attributes, text: info.text };
};

/** Debug SG itself
 */
SpaceGhost.prototype.debugMe = function(){
    console.debug( 'options:\n' + this.jsonStr( this.options ) );
    console.debug( 'cli:\n' + this.jsonStr( this.cli ) );
};

/** Get the last error on the stack.
 *  @returns {Error} the last error
 */
SpaceGhost.prototype.lastError = function(){
    return this.errors[( this.errors.length - 1 )];
};

// ------------------------------------------------------------------- file system
/** Load and parse a JSON file into an object.
 *  @param {String} filepath     filepath relative to the current script
 *  @returns {Object} the object parsed
 */
SpaceGhost.prototype.loadJSONFile = function loadJSONFile( filepath ){
    //precondition: filepath is relative to script dir
    return JSON.parse( fs.read( filepath ) );
};

/** Write an object to a JSON file.
 *  @param {String} filepath     filepath relative to the current script
 *  @param {Object} object       the object to write
 *  @param {String} mode         'w' for a new file, 'a' for append
 */
SpaceGhost.prototype.writeJSONFile = function writeJSONFile( filepath, object, mode ){
    mode = mode || 'w';
    //precondition: filepath is relative to script dir
    return fs.write( filepath, this.jsonStr( object ), mode );
};

/** Save the HTML from the current page to file.
 *  @param {String} filepath    filepath relative to the current script
 *  @param {String} selector    A DOM CSS3/XPath selector (optional)
 *  @param {Boolean} outer      Whether to fetch outer HTML contents (default: false)
 */
SpaceGhost.prototype.writeHTMLFile = function writeHTMLFile( filepath, selector, outer ){
    return fs.write( filepath, this.getHTML( selector, outer ), 'w' );
};

/** Read and search a file for the given regex.
 *  @param {String} filepath     filepath relative to the current script
 *  @param {Regex} searchFor     regex to search for
 *  @returns {Object} search results
 */
SpaceGhost.prototype.searchFile = function searchFile( filepath, regex ){
    //precondition: filepath is relative to script dir
    var read = fs.read( filepath );
    return read.match( regex );
};

/** Read a configuration setting from the galaxy.ini file.
 *  @param {String} iniKey     the setting key to find
 *  @returns {String} value from file for iniKey (or null if not found or commented out)
 */
SpaceGhost.prototype.getUniverseSetting = function getUniverseSetting( iniKey ){
    var iniFilepath = '../../config/galaxy.ini',
        regex = new RegExp( '^([#]*)\\\s*' + iniKey + '\\\s*=\\\s*(.*)$', 'm' ),
        match = this.searchFile( iniFilepath, regex );
    this.debug( 'regex: ' + regex );
    // if nothing found or found and first group (the ini comment char) is not empty
    if( match === null || match[1] || !match[2] ){
        return null;
    }
    return match[2];
};

SpaceGhost.prototype.waitForMasthead = function wait( then ) {
    return this.waitForText( this.data.labels.masthead.menus.user, then );
};


// =================================================================== TEST DATA
/** General use selectors, labels, and text. Kept here to allow a centralized location.
 */
SpaceGhost.prototype.data = {
    selectors : {
        tooltipBalloon          : '.tooltip',

        editableText            : '.editable-text',

        messages : {
            all         : '[class*="message"]',
            error       : '.errormessage',
            done        : '.donemessage',
            info        : '.infomessage',
            donelarge   : '.donemessagelarge',
            infolarge   : '.infomessagelarge'
        },

        frames : {
            main    : 'galaxy_main'
        },

        masthead : {
            id          : '#masthead',
            adminLink   : '#masthead a[href="/admin/index"]',
            userMenu    : {
                userEmail_xpath : '//a[contains(text(),"Logged in as")]'
            }
        },
        toolMenu : {
            container   : '.toolMenuContainer'
        },
        historyPanel : {
            current     : '#current-history-panel'
        },

        loginPage : {
            form            : 'form#login',
            submit_xpath    : "//input[@value='Login']",
            url_regex       : /\/user\/login/
        },
        registrationPage : {
            form            : 'form#registration',
            submit_xpath    : "//input[@value='Submit']",
            returnLink      : '//a[contains(text(),"Return to the home page")]'
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
            success : 'Your upload has been queued'
        },
        tool : {
            success : 'The following job has been successfully added to the queue'
        }
    }
};


// =================================================================== error types
/** @class Represents a javascript error on the page casper is browsing
 *      (as opposed to an error in the test script).
 */
function PageError(){
    CasperError.apply( this, arguments );
    this.name = "PageError";
}
//TODO: change to inheriting from Error
PageError.prototype = new CasperError();
PageError.prototype.constructor = CasperError;
SpaceGhost.prototype.PageError = PageError;

/** @class Thrown when Galaxy has (gracefully?) indicated pilot error. */
function GalaxyError(){
    CasperError.apply( this, arguments );
    this.name = "GalaxyError";
}
GalaxyError.prototype = new CasperError();
GalaxyError.prototype.constructor = CasperError;
SpaceGhost.prototype.GalaxyError = GalaxyError;

/** @class Thrown when Galaxy has displayed a javascript alert. */
function AlertError(){
    CasperError.apply( this, arguments );
    this.name = "AlertError";
}
AlertError.prototype = new CasperError();
AlertError.prototype.constructor = CasperError;
SpaceGhost.prototype.AlertError = AlertError;

exports.PageError   = PageError;
exports.GalaxyError = GalaxyError;
exports.AlertError  = AlertError;
