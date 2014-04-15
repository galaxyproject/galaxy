define([
    'mvc/user/user-model',
    'utils/metrics-logger',
    'utils/add-logging',
    'utils/localization'
], function( userModel, metricsLogger, addLogging, localize ){
// ============================================================================
/** Base galaxy client-side application.
 *      Iniitializes:
 *          logger      : the logger/metrics-logger
 *          localize    : the string localizer
 *          config      : the current configuration (any k/v in
 *              universe_wsgi.ini available from the configuration API)
 *          user        : the current user (as a mvc/user/user-model)
 */
function GalaxyApp( options ){
    var self = this;
    return self._init( options || {} );
}
// add logging shortcuts for this object
addLogging( GalaxyApp, 'GalaxyApp' );

/** default options */
GalaxyApp.defaultOptions = {
    /** root url of this app */
    // move to self.root?
    root        : '/'
};

/** initalize options and sub-components */
GalaxyApp.prototype._init = function init( options ){
    var self = this;

    self._processOptions( options );
    self.debug( 'GalaxyApp.options: ', self.options );

    self._initLogger( options.loggerOptions || {} );
    self.debug( 'GalaxyApp.logger: ', self.logger );

    self._initLocale();
    self.debug( 'GalaxyApp.localize: ', self.localize );

    self.config = options.config || {};
    self.debug( 'GalaxyApp.config: ', self.config );

    self._initUser( options.userJSON || {} );
    self.debug( 'GalaxyApp.user: ', self.user );

    return self;
};

/** add an option from options if the key matches an option in defaultOptions */
GalaxyApp.prototype._processOptions = function _processOptions( options ){
    var self = this,
        defaults = GalaxyApp.defaultOptions;
    self.debug( '_processOptions: ', options );

    self.options = {};
    for( var k in defaults ){
        if( defaults.hasOwnProperty( k ) ){
            self.options[ k ] = ( options.hasOwnProperty( k ) )?( options[ k ] ):( defaults[ k ] );
        }
    }
    return self;
};

/** set up the current user as a Backbone model (mvc/user/user-model) */
GalaxyApp.prototype._initUser = function _initUser( userJSON ){
    var self = this;
    self.debug( '_initUser:', userJSON );
    self.user = new userModel.User( userJSON );
    return self;
};

/** set up the metrics logger (utils/metrics-logger) and pass loggerOptions */
GalaxyApp.prototype._initLogger = function _initLogger( loggerOptions ){
    var self = this;
    self.debug( '_initLogger:', loggerOptions );
    self.logger = new metricsLogger.MetricsLogger( loggerOptions );
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

/** string rep */
GalaxyApp.prototype.toString = function toString(){
    var userEmail = this.user.get( 'email' ) || '(anonymous)';
    return 'GalaxyApp(' + userEmail + ')';
};


// ============================================================================
    return {
        GalaxyApp : GalaxyApp
    };
});
