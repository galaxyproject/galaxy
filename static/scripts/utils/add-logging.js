define([
], function(){
//==============================================================================
function addLogging( obj, namespace ){
    if( namespace !== undefined ){
        obj._logNamespace = namespace;
    }

    [ 'debug', 'info', 'warn', 'error', 'metric' ].forEach( function( logFn ){
        ( obj.prototype || obj )[ logFn ] = function(){
            if( !this.logger ){ return undefined; }
            if( this.logger.emit ){
                return this.logger.emit( logFn, this._logNamespace, arguments );
            }
            if( this.logger[ logFn ] ){
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
