define([
], function(){
//==============================================================================
function addLogging( obj, namespace ){
    var addTo = ( obj.prototype !== undefined )?( obj.prototype ):( obj );
    if( namespace !== undefined ){
        addTo._logNamespace = namespace;
    }

    [ 'debug', 'info', 'warn', 'error', 'metric' ].forEach( function( logFn ){
        addTo[ logFn ] = function(){
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
