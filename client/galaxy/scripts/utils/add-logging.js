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

    // give the object each
    LOGGING_FNS.forEach( function( logFn ){
        addTo[ logFn ] = function(){
            if( !this.logger ){
                // if Galaxy is set for debugging, set it on the first time it's noticed as missing
                if( ( Galaxy.config || {} ).debug ){
                    this.logger = Galaxy.logger || console;
                } else {
                    return undefined;
                }
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
