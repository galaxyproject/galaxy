define([
    'mvc/user/user-model',
    'utils/metrics-logger',
    'utils/add-logging',
    'utils/localization',
    'mvc/base-mvc',
    'bootstrapped-data'
], function( userModel, metricsLogger, addLogging, localize, BASE_MVC, bootstrapped ){

// TODO: move into a singleton pattern and have dependents import Galaxy
// ============================================================================
/** Base galaxy client-side application.
 *      Iniitializes:
 *          logger      : the logger/metrics-logger
 *          localize    : the string localizer
 *          config      : the current configuration (any k/v in
 *              galaxy.ini available from the configuration API)
 *          user        : the current user (as a mvc/user/user-model)
 */
function GalaxyApp( options ){
    var self = this;
    return self._init( options || {} );
}

// add logging shortcuts for this object
addLogging( GalaxyApp, 'GalaxyApp' );

// a debug flag can be set via local storage and made available during script/page loading
var DEBUGGING_KEY = 'galaxy:debug',
    NAMESPACE_KEY = DEBUGGING_KEY + ':namespaces',
    localDebugging = false;
try {
    localDebugging = localStorage.getItem( DEBUGGING_KEY ) == 'true';
} catch( storageErr ){
    console.log( localize( 'localStorage not available for debug flag retrieval' ) );
}

/** initalize options and sub-components */
GalaxyApp.prototype._init = function init( options ){
    var self = this;
    _.extend( self, Backbone.Events );
    if( localDebugging ){
        self.logger = console;
    }

    self._processOptions( options );
    self.debug( 'GalaxyApp.options: ', self.options );

    self._initConfig( options.config || bootstrapped.config || {} );
    self.debug( 'GalaxyApp.config: ', self.config );

    self._patchGalaxy( window.Galaxy );

    self._initLogger( self.options.loggerOptions || {} );
    self.debug( 'GalaxyApp.logger: ', self.logger );

    self._initLocale();
    self.debug( 'GalaxyApp.localize: ', self.localize );

    self._initUser( options.user || bootstrapped.user || {} );
    self.debug( 'GalaxyApp.user: ', self.user );

    //TODO: temp
    self.trigger( 'ready', self );
    //if( typeof options.onload === 'function' ){
    //    options.onload();
    //}

    self._setUpListeners();

    return self;
};

/** default options */
GalaxyApp.prototype.defaultOptions = {
    /** monkey patch attributes from existing window.Galaxy object? */
    patchExisting   : true,
    /** root url of this app */
    // move to self.root?
    root            : '/',
    /** options for the logger */
    loggerOptions   : {}
};

/** add an option from options if the key matches an option in defaultOptions */
GalaxyApp.prototype._processOptions = function _processOptions( options ){
    var self = this,
        defaults = self.defaultOptions;
    self.debug( '_processOptions: ', options );

    self.options = {};
    for( var k in defaults ){
        if( defaults.hasOwnProperty( k ) ){
            self.options[ k ] = ( options.hasOwnProperty( k ) )?( options[ k ] ):( defaults[ k ] );
        }
    }
    return self;
};

/** parse the config and any extra info derived from it */
GalaxyApp.prototype._initConfig = function _initConfig( config ){
    var self = this;
    self.debug( '_initConfig: ', config );
    self.config = config;

    // give precendence to localdebugging for this setting
    self.config.debug = localDebugging || self.config.debug;

    return self;
};

/** add an option from options if the key matches an option in defaultOptions */
GalaxyApp.prototype._patchGalaxy = function _processOptions( patchWith ){
    var self = this;
    // in case req or plain script tag order has created a prev. version of the Galaxy obj...
    if( self.options.patchExisting && patchWith ){
        self.debug( 'found existing Galaxy object:', patchWith );
        // ...(for now) monkey patch any added attributes that the previous Galaxy may have had
        //TODO: move those attributes to more formal assignment in GalaxyApp
        for( var k in patchWith ){
            if( patchWith.hasOwnProperty( k ) ){
                self.debug( '\t patching in ' + k + ' to Galaxy' );
                self[ k ] = patchWith[ k ];
            }
        }
    }
};

/** set up the metrics logger (utils/metrics-logger) and pass loggerOptions */
GalaxyApp.prototype._initLogger = function _initLogger( loggerOptions ){
    var self = this;
    // default to console logging at the debug level if the debug flag is set
    if( self.config.debug ){
        loggerOptions.consoleLogger = loggerOptions.consoleLogger || console;
        loggerOptions.consoleLevel = loggerOptions.consoleLevel || metricsLogger.MetricsLogger.ALL;
        // load any logging namespaces from localStorage if we can
        try {
            loggerOptions.consoleNamespaceWhitelist = localStorage.getItem( NAMESPACE_KEY ).split( ',' );
        } catch( storageErr ){}
    }
    self.debug( '_initLogger:', loggerOptions );
    self.logger = new metricsLogger.MetricsLogger( loggerOptions );

    if( self.config.debug ){
        // add this logger to mvc's loggable mixin so that all models can use the logger
        BASE_MVC.LoggableMixin.logger = self.logger;
    }
    return self;
};

/** add the localize fn to this object and the window namespace (as '_l') */
GalaxyApp.prototype._initLocale = function _initLocale( options ){
    var self = this;
    self.debug( '_initLocale:', options );
    self.localize = localize;
    // add to window as global shortened alias
    window._l = self.localize;
    return self;
};

/** set up the current user as a Backbone model (mvc/user/user-model) */
GalaxyApp.prototype._initUser = function _initUser( userJSON ){
    var self = this;
    self.debug( '_initUser:', userJSON );
    self.user = new userModel.User( userJSON );
    self.user.logger = self.logger;
    //TODO: temp - old alias
    self.currUser = self.user;
    return self;
};

/** Set up DOM/jQuery/Backbone event listeners enabled for all pages */
GalaxyApp.prototype._setUpListeners = function _setUpListeners(){
    var self = this;

    // hook to jq beforeSend to record the most recent ajax call and cache some data about it
    /** cached info about the last ajax call made through jQuery */
    self.lastAjax = {};
    $( document ).bind( 'ajaxSend', function( ev, xhr, options ){
        var data = options.data;
        try {
            data = JSON.parse( data );
        } catch( err ){}

        self.lastAjax = {
            url     : location.href.slice( 0, -1 ) + options.url,
            data    : data
        };
        //TODO:?? we might somehow manage to *retry* ajax using either this hook or Backbone.sync
    });
    return self;
};

/** Turn debugging/console-output on/off by passing boolean. Pass nothing to get current setting. */
GalaxyApp.prototype.debugging = function _debugging( setting ){
    var self = this;
    try {
        if( setting === undefined ){
            return localStorage.getItem( DEBUGGING_KEY ) === 'true';
        }
        if( setting ){
            localStorage.setItem( DEBUGGING_KEY, true );
            return true;
        }

        localStorage.removeItem( DEBUGGING_KEY );
        // also remove all namespaces
        self.debuggingNamespaces( null );

    } catch( storageErr ){
        console.log( localize( 'localStorage not available for debug flag retrieval' ) );
    }
    return false;
};

/** Add, remove, or clear namespaces from the debugging filters
 *  Pass no arguments to retrieve the existing namespaces as an array.
 *  Pass in null to clear all namespaces (all logging messages will show now).
 *  Pass in an array of strings or single string of the namespaces to filter to.
 *  Returns the new/current namespaces as an array;
 */
GalaxyApp.prototype.debuggingNamespaces = function _debuggingNamespaces( namespaces ){
    var self = this;
    try {
        if( namespaces === undefined ){
            var csv = localStorage.getItem( NAMESPACE_KEY );
            return typeof( csv ) === 'string'? csv.split( ',' ) : [];
        } else if( namespaces === null ) {
            localStorage.removeItem( NAMESPACE_KEY );
        } else {
            localStorage.setItem( NAMESPACE_KEY, namespaces );
        }
        var newSettings = self.debuggingNamespaces();
        if( self.logger ){
            self.logger.options.consoleNamespaceWhitelist = newSettings;
        }
        return newSettings;
    } catch( storageErr ){
        console.log( localize( 'localStorage not available for debug namespace retrieval' ) );
    }
};

/** string rep */
GalaxyApp.prototype.toString = function toString(){
    var userEmail = this.user? ( this.user.get( 'email' ) || '(anonymous)' ) : 'uninitialized';
    return 'GalaxyApp(' + userEmail + ')';
};


// ============================================================================
    return {
        GalaxyApp : GalaxyApp
    };
});
