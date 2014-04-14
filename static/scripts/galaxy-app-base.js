define([
    'mvc/user/user-model',
    'utils/metrics-logger',
    'utils/add-logging'
], function( userModel, metricsLogger, addLogging ){
// ============================================================================
/**
 *
 */
function GalaxyApp( options ){
    var self = this;
    return self._init( options || {} );
}
addLogging( GalaxyApp, 'GalaxyApp' );

/**  */
GalaxyApp.defaultOptions = {
    // move to self.root?
    root        : '/'
};

/**  */
GalaxyApp.prototype._init = function init( options ){
    var self = this;

    self._initLogger( options.loggerOptions || {} );
    self.debug( 'GalaxyApp.logger: ', self.logger );

    self._processOptions( options );
    self.debug( 'GalaxyApp.options: ', self.options );

    self.config = options.config || {};
    self.debug( 'GalaxyApp.config: ', self.config );

    self._initUser( options.userJSON || {} );
    self.debug( 'GalaxyApp.user: ', self.user );

    return self;
};

/**  */
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

/**  */
GalaxyApp.prototype._initUser = function _initUser( userJSON ){
    var self = this;
    self.debug( '_initUser:', userJSON );
    self.user = new userModel.User( userJSON );
    return self;
};

/**  */
GalaxyApp.prototype._initLogger = function _initLogger( loggerOptions ){
    var self = this;
    self.debug( '_initLogger:', loggerOptions );
    self.logger = new metricsLogger.MetricsLogger( loggerOptions );
    return self;
};

/**  */
GalaxyApp.prototype.toString = function toString(){
    var userEmail = this.user.get( 'email' ) || '(anonymous)';
    return 'GalaxyApp(' + userEmail + ')';
};


// ============================================================================
    return {
        GalaxyApp : GalaxyApp
    };
});
