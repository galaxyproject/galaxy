define([
], function(){
//==============================================================================
var LOGGING_FNS = [ 'log', 'debug', 'info', 'warn', 'error', 'metric' ];
/** adds logging functions to an obj.prototype (or obj directly) adding a namespace for filtering
 *  @param {Object} obj
 *  @param {String} namespace
 */
function addLogging( obj, namespace ){
    var addTo = ( obj.prototype !== undefined )?( obj.prototype ):( obj );
    if( namespace !== undefined ){
        addTo._logNamespace = namespace;
    }
    //yagni?: without this, may not capture Galaxy.config.debug and add Galaxy.logger properly
    // if( window.Galaxy && window.Galaxy.config && window.Galaxy.config.debug ){
    //     addTo.logger = window.Galaxy.logger;
    // }

    // give the object each
    LOGGING_FNS.forEach( function( logFn ){
        addTo[ logFn ] = function(){
            if( !this.logger ){
                return undefined;
            }
            if( this.logger.emit ){
                return this.logger.emit( logFn, this._logNamespace, arguments );
            }
            if( this.logger[ logFn ] ){
//TODO:! there has to be a way to get the lineno/file into this
// http://stackoverflow.com/questions/13815640/a-proper-wrapper-for-console-log-with-correct-line-number
// http://www.paulirish.com/2009/log-a-lightweight-wrapper-for-consolelog/
                return this.logger[ logFn ].apply( this.logger, arguments );
            }
            return undefined;
        };
    });
    return obj;
}

//==============================================================================
return addLogging;
});
