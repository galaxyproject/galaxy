/* TODO:
    Use in test command

    bug: assertStepsRaise raise errors (all the way) when used in 'casperjs test .'

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
/**
 */
function SpaceGhost(){
    SpaceGhost.super_.apply( this, arguments );
    this.init.apply( this, arguments );
}
utils.inherits( SpaceGhost, Casper );

//console.debug( 'CasperError:' + CasperError );

// ------------------------------------------------------------------- error types
PageError.prototype = new CasperError();
PageError.prototype.constructor = CasperError;
function PageError(){
    CasperError.apply( this, arguments );
    this.name = "PageError";
}

GalaxyError.prototype = new CasperError();
GalaxyError.prototype.constructor = CasperError;
function GalaxyError(){
    CasperError.apply( this, arguments );
    this.name = "GalaxyError";
}

AlertError.prototype = new CasperError();
AlertError.prototype.constructor = CasperError;
function AlertError(){
    CasperError.apply( this, arguments );
    this.name = "AlertError";
}

// =================================================================== METHODS / OVERRIDES
// ------------------------------------------------------------------- set up
/** More initialization: cli, event handlers, etc.
 * @param {Object} options  option hash
 */
SpaceGhost.prototype.init = function init( options ){
    //console.debug( 'init, options:', JSON.stringify( options, null, 2 ) );

    //NOTE: cli will override in-script options
    this._setOptionsFromCli();

    // save errors for later output (needs to go before process CLI)
    this.errors = [];
    this.on( 'error', function( msg, backtrace ){
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

};

/** Allow CLI arguments to set options if the proper option name is used.
 *  @example:
 *      casperjs myscript.js --verbose=true --logLevel=debug
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
SpaceGhost.prototype._saveHtmlOnErrorHandler = function _saveHtmlOnErrorHandler( msg, backtrace ){
    // needs to output to a file in GALAXY_SAVE
    //this.debugHTML();
};

SpaceGhost.prototype._saveTextOnErrorHandler = function _saveTextOnErrorHandler( msg, backtrace ){
    // needs to output to a file in GALAXY_SAVE
    //this.debugPage();
};

SpaceGhost.prototype._saveScreenOnErrorHandler = function _saveScreenOnErrorHandler( msg, backtrace ){
    // needs to output to a pic in GALAXY_SAVE
    //var filename = ...??
    //?? this.getCurrentUrl(), this.getCurrent
    //this.capture( filename );
};


/** Set up any SG specific options passed in on the cli.
 */
SpaceGhost.prototype._processCLIArguments = function _processCLIArguments(){
    //TODO: init these programmitically
    var CLI_OPTIONS = {
        returnJsonOnly  : { defaultsTo: false, flag: 'return-json',    help: 'send output to stderr, json to stdout' },
        raisePageError  : { defaultsTo: true,  flag: 'page-error',     help: 'raise errors thrown on the page' },
        errorOnAlert    : { defaultsTo: false, flag: 'error-on-alert', help: 'throw errors when a page calls alert' },
        failOnAlert     : { defaultsTo: true,  flag: 'fail-on-alert',  help: 'fail a test when a page calls alert' }
        //screenOnError   : { defaultsTo: false, flag: 'error-screen',   help: 'capture a screenshot on a page error' },
        //textOnError     : { defaultsTo: false, flag: 'error-text',     help: 'output page text on a page error' },
        //htmlOnError     : { defaultsTo: false, flag: 'error-html',   help: 'output page html on a page error' }
    };

    // --url parameter required (the url of the server to test with)
    if( !this.cli.has( 'url' ) ){
        this.die( 'Test server URL is required - ' +
                  'Usage: capserjs <test_script.js> --url=<test_server_url>', 1 );
    }
    this.baseUrl = this.cli.get( 'url' );

    // --return-json: supress all output except for JSON logs, test results, and errors at finish
    //  this switch allows a testing suite to send JSON data back via stdout (w/o logs, echos interferring)
    this.options.returnJsonOnly = CLI_OPTIONS.returnJsonOnly.defaultsTo;
    if( this.cli.has( CLI_OPTIONS.returnJsonOnly.flag ) ){
        this.options.returnJsonOnly = true;

        //this._suppressOutput();
        this._redirectOutputToStderr();

        // output json on fail-first error
        this.on( 'error', function( msg, backtrace ){
            //console.debug( 'return-json caught error' );
            if( spaceghost.options.exitOnError ){
                this.outputStateAsJson();
                spaceghost.exit( 1 );
            }
        });
        // non-error finshes/json-output are handled in run() for now
    }

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

    // --error-screen: print the casper.debugPage (the page's text) output on an error
    if( this.cli.has( 'error-screen' ) ){
        this.on( 'page.error', this._saveScreenOnErrorHandler );
    }
    */

    // get any fixture data passed in as JSON in args
    //  (NOTE: currently the 2nd arg (with the url being 1st?)
    this.fixtureData = ( this.cli.has( 1 ) )?( JSON.parse( this.cli.get( 1 ) ) ):( {} );
    this.debug( 'fixtureData:' + this.jsonStr( this.fixtureData ) );

};

/** Suppress the normal output from the casper object (echo, errors)
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

/** Outputs logs, test results and errors in a single JSON formatted object.
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
// most of these are stubs (w logging) for later expansion

/** Event handler for failed page loads
 */
SpaceGhost.prototype._loadFailedHandler = function _loadFailedHandler( object ){
    this.error( 'load.failed: ' + spaceghost.jsonStr( object ) );
    //TODO: throw error?
};

/** Event handler for page errors (js) - throws test scope as PageError
 *      NOTE: this has some special handling for DOM exc 12 which some casper selectors are throwing
 *          (even tho the selector still works)
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

/** Event handler for console messages from the page.
 */
SpaceGhost.prototype._pageConsoleHandler = function _pageConsoleHandler(){
    // remote.message
    var DELIM = '-';
    this.debug( this + '(page console) "' + Array.prototype.join.call( arguments, DELIM ) + '"' );
};

/** Event handler for alerts
 */
SpaceGhost.prototype._alertHandler = function _alertHandler( message ){
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

/** Event handler for navigation requested (loading of frames, redirects(?))
 */
SpaceGhost.prototype._navHandler = function _navHandler( url, navigationType, navigationLocked, isMainFrame ){
    this.debug( 'navigation.requested: ' + url );
};

/** Set up event handlers.
 */
SpaceGhost.prototype._setUpEventHandlers = function _setUpEventHandlers(){
    //console.debug( '_setUpEventHandlers' );

    // ........................ page errors
    this.on( 'page.error',  this._pageErrorHandler );
    //this.on( 'load.failed', this._loadFailedHandler );

    // ........................ page info/debugging
    // these are already displayed at the casper info level

    //this.on( 'remote.message',  this._pageConsoleHandler );
    this.on( 'remote.alert',    this._alertHandler );

    // these are already displayed at the casper debug level
    //this.on( 'navigation.requested',    this._navHandler );

};

// ------------------------------------------------------------------- page control
/** An override of casper.open specifically for Galaxy.
 *      (Currently only used to change language headers)
 */
SpaceGhost.prototype.open = function open(){
    //TODO: this can be moved to start (I think...?)
    //!! override bc phantom has it's lang as 'en-US,*' and galaxy doesn't handle the '*' well (server error)
    this.page.customHeaders = { 'Accept-Language': 'en-US' };
    return Casper.prototype.open.apply( this, arguments );
};

/** An override to provide json output and more informative error codes
 */
SpaceGhost.prototype.run = function run( onComplete, time ){
    // wrap the onComplete to:
    //  return code 2 on test failure
    //              0 on success
    //              (1 on js error - in error handler)
    var new_onComplete = function(){
            onComplete.call( this );
            var returnCode = ( this.test.testResults.failed )?( 2 ):( 0 );

            // if --return-json is used: output json and exit
            if( this.options.returnJsonOnly ){
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
    //TODO:  *  @param {Boolean} removeOtherListeners option to remove other listeners while this fires
    // create three steps: 1) set up new error handler, 2) try the fn, 3) check for errors and rem. handler
    var originalExitOnError,
        errorMsg = '', errorTrace = [],
        recordError = function( msg, trace ){
            errorMsg = msg; errorTrace = trace;
        };

    // dont bail on the error (but preserve option), install hndlr to simply record msg, trace
    //NOTE: haven't had to remove other listeners yet
    this.then( function(){
        originalExitOnError = this.options.exitOnError;
        this.options.exitOnError = false;
        this.on( 'error', recordError );
    });

    // try the step...
    this.then( stepsFn );

    this.then( function(){
        // ...and if an error was recorded call the catch with the info
        if( errorMsg ){
            catchFn.call( this, errorMsg, errorTrace );
        }
        // remove that listener either way and restore the bail option
        this.removeListener( 'error', recordError );
        this.options.exitOnError = originalExitOnError;
    });
};


// =================================================================== TESTING
//TODO: form fill doesn't work as casperjs would want it - often a button -> controller url
//TODO: saveScreenshot (to GALAXY_TEST_SAVE)
//TODO: saveHtml (to GALAXY_TEST_SAVE)

/** Casper has an (undocumented?) skip test feature. This is a conv. wrapper for that.
 */
SpaceGhost.prototype.skipTest = function(){
    //TODO: does this work? seems to...
    throw this.test.SKIP_MESSAGE;
};

/** test helper - within frame, assert selector, and assert text in selector
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

/** test helper - within frame, assert errormessage, and assert text in errormessage
 *      *message is a common UI feedback motif in Galaxy (often displayed in the main panel)
 *  @param {String} message                     what the message should contain
 *  @param {String} frame                       frame selector (gen. name) in which to search for selector (defaults to 'galaxy_main')
 *  @param {CasperJS selector} messageSelector  what element in which to search for the text (defaults to '.errormessage')
 */
SpaceGhost.prototype.assertErrorMessage = function assertSelectorAndTextInFrame( message, frame, messageSelector ){
    messageSelector = messageSelector || this.selectors.messages.error;
    frame = frame || this.selectors.frames.main;
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

// =================================================================== CONVENIENCE
/** Wraps casper.getElementInfo in try, returning null if element not found instead of erroring.
 *  @param {String} selector    css or xpath selector for the element to find
 */
SpaceGhost.prototype.elementInfoOrNull = function elementInfoOrNull( selector ){
    var found = null;
    try {
        found = this.getElementInfo( selector );
    } catch( err ){}
    return found;
};

/** Wraps casper.click in try, returning true if element found and clicked, false if not instead of erroring.
 *  @param {String} selector    css or xpath selector for the element to find
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
/** Gets a psuedo-random (unique?) email based on the time stamp.
 *      Helpful for testing registration.
 *  @param {String} username    email user (defaults to 'test')
 *  @param {String} domain      email domain (defaults to 'test.test')
 */
SpaceGhost.prototype.getRandomEmail = function getRandomEmail( username, domain ){
    username = username || 'test';
    domain = domain || 'test.test';
    return username + Date.now() + '@' + domain;
};


/** Tests registering a new user on the Galaxy instance by submitting the registration form.
 *      NOTE: this version does NOT throw an error on a bad registration.
 *      It is meant for testing the registration functionality and, therefore, is marked as private.
 *      Other tests should use registerUser
 *  @param {String} email       the users email address
 *  @param {String} password    the users password
 *  @param {String} username    the users ...username! (optional: will use 1st part of email)
 *  @param {String} confirm     password confirmation (optional: defaults to password)
 */
SpaceGhost.prototype._submitUserRegistration = function _submitUserRegistration( email, password, username, confirm ){
    var userInfo = {
            email   : email,
            password: password,
            // default username to first part of email
            username:( !username && email.match( /^\w*/ ) )?( email.match( /^\w*/ ) ):( username ),
            // default confirm duplicate of password
            confirm : ( confirm !== undefined )?( confirm ):( password )
        };
    this.debug( 'registering user:\n' + this.jsonStr( userInfo ) );

    this.thenOpen( this.baseUrl, function(){

        this.clickLabel( this.labels.masthead.menus.user );
        this.clickLabel( this.labels.masthead.userMenu.register );

        this.withFrame( this.selectors.frames.main, function mainBeforeRegister(){
            this.debug( 'submitting registration... ' + this.getCurrentUrl() );
            this.fill( this.selectors.registrationPage.form, userInfo, false );
            // need manual up
            this.click( xpath( this.selectors.registrationPage.submit_xpath ) );
        });

        this.withFrame( this.selectors.frames.main, function mainAfterRegister(){
            var messageInfo = this.getElementInfo( this.selectors.messages.all );
            this.debug( 'post registration message:\n' + this.jsonStr( messageInfo ) );
        });
    });
};

/** Register a new user on the Galaxy instance.
 *  @param {String} email       the users email address
 *  @param {String} password    the users password
 *  @param {String} username    the users ...username! (optional: will use 1st part of email)
 */
SpaceGhost.prototype.registerUser = function registerUser( email, password, username ){
    this._submitUserRegistration( email, password, username );
    this.then( function(){
        this.withFrame( this.selectors.frames.main, function mainAfterRegister(){
            var messageInfo = this.getElementInfo( this.selectors.messages.all );
            this.debug( 'post registration message:\n' + this.jsonStr( messageInfo ) );

            if( messageInfo.attributes[ 'class' ] === 'errormessage' ){
                throw new GalaxyError( 'RegistrationError: ' + messageInfo.html );
            }
        });
    });
    return this;
};

/** Log out the current user
 */
SpaceGhost.prototype.logout = function logoutUser(){
    this.clickLabel( this.labels.masthead.menus.user );
    this.clickLabel( this.labels.masthead.userMenu.login );
    this.thenOpen( this.baseUrl, function(){
        //TODO: handle already logged out
        this.clickLabel( this.labels.masthead.menus.user );
        this.clickLabel( this.labels.masthead.userMenu.logout );
    });
};

/** Tests logging in a user on the Galaxy instance by submitting the login form.
 *      NOTE: this version does NOT throw an error on a bad login.
 *      It is meant for testing the login functionality and, therefore, is marked as private.
 *      Other tests should use login
 *  @param {String} email       the users email address
 *  @param {String} password    the users password
 */
SpaceGhost.prototype._submitLogin = function logoutUser( email, password ){
    var loginInfo = {
        //NOTE: keys are used as name selectors in the fill fn - must match the names of the inputs
            email: email,
            password: password
        };

    this.thenOpen( this.baseUrl, function(){

        this.clickLabel( this.labels.masthead.menus.user );
        this.clickLabel( this.labels.masthead.userMenu.login );

        this.withFrame( this.selectors.frames.main, function mainBeforeLogin(){
            this.debug( '(' + this.getCurrentUrl() + ') logging in user:\n' + this.jsonStr( loginInfo ) );
            this.fill( this.selectors.loginPage.form, loginInfo, false );
            this.click( xpath( this.selectors.loginPage.submit_xpath ) );
        });
        this.withFrame( this.selectors.frames.main, function mainAfterLogin(){
            //TODO: prob. could use a more generalized form of this for url breakdown/checking
            if( this.getCurrentUrl().search( this.selectors.loginPage.url_regex ) != -1 ){
                var messageInfo = this.getElementInfo( this.selectors.messages.all );
                this.debug( 'post login message:\n' + this.jsonStr( messageInfo ) );
            }
        });
    });
};

/** Logs in a user. Throws error on bad log in.
 *  @param {String} email       the users email address
 *  @param {String} password    the users password
 */
SpaceGhost.prototype.login = function login( email, password ){
    this._submitLogin( email, password );
    this.then( function(){
        this.withFrame( this.selectors.frames.main, function mainAfterLogin(){
            if( this.getCurrentUrl().search( this.selectors.loginPage.url_regex ) != -1 ){
                var messageInfo = this.getElementInfo( this.selectors.messages.all );
                if( messageInfo && messageInfo.attributes[ 'class' ] === 'errormessage' ){
                    throw new GalaxyError( 'LoginError: ' + messageInfo.html );
                }
            }
        });
        if( this.loggedInAs() === email ){
            this.debug( 'logged in as ' + email );
        }
    });
    return this;
};

/** Fetch the email of the currently logged in user (or '' if not logged in)
 *  @returns {String} email of currently logged in user or '' if no one logged in
 */
SpaceGhost.prototype.loggedInAs = function loggedInAs(){
    var userEmail = '';
    try {
        var loggedInInfo = this.getElementInfo( xpath( this.selectors.masthead.userMenu.userEmail_xpath ) );
        userEmail = loggedInInfo.text;
    } catch( err ){
        this.error( err );
    }
    //console.debug( 'loggedInInfo:', this.jsonStr( loggedInInfo ) );
    return userEmail;
};

/** Attempts to login a user - if that raises an error (LoginError), register the user
 *  @param {String} email       the users email address
 *  @param {String} password    the users password
 *  @param {String} username    the users ...username! (optional: will use 1st part of email)
 */
SpaceGhost.prototype.loginOrRegisterUser = function loginOrRegisterUser( email, password, username ){
    // attempt a login, if that fails - register
    this.tryStepsCatch( function tryToLogin(){
        this.open( this.baseUrl ).login( email, password );

    }, function failedLoginRegister(){
        this.open( this.baseUrl ).registerUser( email, password, username );
    });
    return this;
};

/** Tests uploading a file.
 *      NOTE: this version does NOT throw an error on a bad upload.
 *      It is meant for testing the upload functionality and, therefore, is marked as private.
 *      Other tests should use uploadFile
 *  @param {String} filepath    the local filesystem path of the file to upload (absolute (?))
 */
SpaceGhost.prototype._uploadFile = function _uploadFile( filepath ){
    var uploadInfo = {};
    //TODO: check file exists using phantom.fs
    //TODO: pull from test data
    uploadInfo[ this.tools.upload.fileInput ] = filepath;
    this.debug( 'uploading file: ' + filepath );

    spaceghost.then( function(){
        spaceghost.withFrame( this.selectors.frames.tools, function(){
            this.clickLabel( this.tools.upload.panelLabel );
        });
    });

    this.then( function beginUpload(){
        spaceghost.withFrame( this.selectors.frames.main, function(){
            this.fill( this.tools.general.form, uploadInfo, false );

            // the following throws:
            //  [error] [remote] Failed dispatching clickmouse event on xpath selector: //input[@value="Execute"]:
            //  PageError: TypeError: 'undefined' is not a function (evaluating '$(this).formSerialize()')

            // ...and yet the upload still seems to work
            this.click( xpath( this.tools.general.executeButton_xpath ) );
        });
    });
    this.withFrame( this.selectors.frames.main, function afterUpload(){
        var messageInfo = this.elementInfoOrNull( this.selectors.messages.all );
        this.debug( 'post upload message:\n' + this.jsonStr( messageInfo ) );
    });
};

/** Uploads a file.
 *  @param {String} filepath     the local filesystem path of the file to upload (absolute (?))
 */
SpaceGhost.prototype.uploadFile = function uploadFile( filepath ){
    this._uploadFile( filepath );
    this.then( function(){
        this.withFrame( this.selectors.frames.main, function mainAfterUpload(){
            var messageInfo = this.elementInfoOrNull( this.selectors.messages.all );
            if( ( !messageInfo )
            ||  ( messageInfo.attributes[ 'class' ] !== 'donemessagelarge' )
            ||  ( messageInfo.text.indexOf( this.text.upload.success ) === -1 ) ){
                throw new GalaxyError( 'UploadError: ' + this.jsonStr( messageInfo ) );
            }
        });
    });
    return this;
};

/** Parses the hid and name of a newly uploaded file from the tool execution donemessagelarge
 *  @param {String} doneMsgText     the text extracted from the donemessagelarge after a tool execution
 */
SpaceGhost.prototype.parseDoneMessageForTool = function parseDoneMessageForTool( doneMsgText ){
    //TODO: test on non-upload
    var executionInfo = {};
    var textMatch = doneMsgText.match( /added to the queue:\n\n(\d+)\: (.*)\n/m );
    if( textMatch ){
        if( textMatch.length > 1 ){
            executionInfo.hid = parseInt( textMatch[1], 10 );
        }
        if( textMatch.length > 2 ){
            executionInfo.name = textMatch[2];
        }
        executionInfo.name = textMatch[2];
    }
    return executionInfo;
};

/** Find the casper element info of the hda wrapper given the hda title and hid.
 *      NOTE: if more than one is found, will return the first found.
 *      precondition: you should wrap this with withFrame( 'galaxy_history' ) :(
 *  @param {String} title   the title of the hda
 *  @param {Int} hid        (optional) the hid of the hda to look for
 *  @returns {Object|null} ElementInfo of the historyItemWrapper found, null if not found
 */
SpaceGhost.prototype.hdaElementInfoByTitle = function hdaElementInfoByTitle( title, hid ){
    var spaceghost = this,
        titleContains = ( hid !== undefined )?( hid + ': ' + title ):( title ),
        wrapperInfo = null;

    wrapperInfo = spaceghost.evaluate( function( titleContains ){
        // find the title, then the wrapper (2 containers up)
        var $title = $( '.historyItemTitle:contains(' + titleContains + ')' );
        var $wrapper = $title.parent().parent();
        return (( $wrapper.attr( 'id' ) )?( __utils__.getElementInfo(  '#' + $wrapper.attr( 'id' ) )):( null ));
    }, titleContains );

    return wrapperInfo;
};

/** Wait for the hda with given id to move into the given state.
 *  @param {String} hdaSelector     selector for hda (should be historyItemWrapper)
 *  @param {String} finalState      hda state to wait for (e.g. 'ok', 'error', 'running', 'queued', etc.)
 *  @param {Function} whenInStateFn called when hda goes into finalState
 *  @param {Function} timeoutFn     called when maxWaitMs have passed without the desired state
 *  @param {Int} maxWaitMs          number of milliseconds to wait before timing out (defaults to options.waitTimeout)
 */
SpaceGhost.prototype.waitForHdaState = function waitForHdaState( hdaSelector, finalState,
                                                                 whenInStateFn, timeoutFn, maxWaitMs ){
    //TODO:?? explicitly a historyWrapper id?
    maxWaitMs = maxWaitMs || this.options.waitTimeout;
    var finalStateClass = '.historyItem-' + finalState;

    this.then( function(){
        this.withFrame( this.selectors.frames.history, function(){
            // wait for state, preferrably debugging intermediate states
            var spaceghost = this,

                // we need a larger timeout for these - it can take a bit
                oldWaitTimeout = this.options.waitTimeout,

                // output some progress indicator within the test (debug)
                progressIntervalId = setInterval( function progress(){
                    var state = spaceghost.evaluate( function( hdaSelector ){
                        var $wrapperClasses = $( hdaSelector ).attr( 'class' );
                        return $wrapperClasses.match( /historyItem\-(\w+)/ )[1];
                    }, hdaSelector );
                    spaceghost.debug( hdaSelector + ': ' + state );
                }, 1000 ),

                // when done, close down the progress reporter and reset the wait timeout to what it was
                finallyFn = function(){
                    spaceghost.options.waitTimeout = oldWaitTimeout;
                    clearInterval( progressIntervalId );
                };

            this.options.waitTimeout = maxWaitMs;
            this.waitForSelector( hdaSelector + finalStateClass, function _whenInState(){
                    this.debug( 'HDA now in state ' + finalState + ':\n'
                        + this.jsonStr( this.elementInfoOrNull( hdaSelector ) ) );
                    whenInStateFn.call( this );
                    finallyFn();

                }, function timeout(){
                    this.debug( 'timed out:\n'
                        + this.jsonStr( this.elementInfoOrNull( hdaSelector ) ) );
                    timeoutFn.call( this );
                    finallyFn();
                }
            );
        });
    });
};

// =================================================================== MISCELAIN
/** Send message to stderr
 */
SpaceGhost.prototype.stderr = function( msg ){
    var fs = require( 'fs' );
    fs.write( '/dev/stderr', msg + '\n', 'w' );
};

// convenience logging funcs
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

/** log using level = 'info' and default namespace = 'spaceghost'
 */
SpaceGhost.prototype.warning = function( msg, namespace ){
    namespace = namespace || 'spaceghost';
    this.log( msg, 'warning', namespace );
};

/** log using level = 'info' and default namespace = 'spaceghost'
 */
SpaceGhost.prototype.error = function( msg, namespace ){
    namespace = namespace || 'spaceghost';
    this.log( msg, 'error', namespace );
};

/** log despite logLevel settings, unless returnJsonOnly is set
 */
SpaceGhost.prototype.out = function( msg, namespace ){
    if( !this.options.returnJsonOnly ){
        console.debug( msg );
    }
};

/** JSON formatter
 */
SpaceGhost.prototype.jsonStr = function( obj ){
    return JSON.stringify( obj, null, 2 );
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

/** Get the last error from an assertRaises test (gen. for the message)
 */
SpaceGhost.prototype.getLastAssertRaisesError = function(){
    // assuming the test passed here...
    var testsThatPassed = this.test.testResults.passes;
    var test = null;
    for( var i=( testsThatPassed.length - 1 ); i>=0; i-- ){
        currTest = testsThatPassed[i];
        if( currTest.type === 'assertRaises' ){
            test = currTest; break;
        }
    }
    return ( ( test && test.values )?( test.values.error ):( undefined ) );
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


// =================================================================== TEST DATA
// maintain selectors, labels, text here in one central location

//TODO: to separate file?
SpaceGhost.prototype.selectors = {
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
        all             : '[class*="message"]',
        error       : '.errormessage',
        done        : '.donemessage'
    },
    loginPage : {
        form            : 'form#login',
        submit_xpath    : "//input[@value='Login']",
        url_regex       : /\/user\/login/
    },
    registrationPage : {
        form            : 'form#registration',
        submit_xpath    : "//input[@value='Submit']"
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
    }
};

SpaceGhost.prototype.tools = {
    general : {
        form : 'form#tool_form',
        executeButton_xpath : '//input[@value="Execute"]'
    },
    upload : {
        panelLabel  : 'Upload File',
        fileInput   : 'files_0|file_data'   // is this general?
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

// =================================================================== EXPORTS
/**
 */
exports.SpaceGhost  = SpaceGhost;
exports.PageError   = PageError;
exports.GalaxyError = GalaxyError;
exports.AlertError  = AlertError;
/**
 */
exports.create = function create(options) {
    "use strict";
    return new SpaceGhost(options);
};

// ------------------------------------------------------------------- included libs
//??: can we require underscore, etc. from the ../../static/scripts/lib?
// yep!
//var _ = require( '../../static/scripts/libs/underscore' );
//var stooges = [{name : 'moe', age : 40}, {name : 'larry', age : 50}, {name : 'curly', age : 60}];
//console.debug( JSON.stringify( _.pluck(stooges, 'name') ) );
//exports._ = _;
