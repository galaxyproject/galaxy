define([], function(){
// ============================================================================
function get( key, queryString ){
    queryString = queryString || window.location.search.substr( 1 );
    var keyRegex = new RegExp( key + '=([^&#$]+)' ),
        matches = queryString.match( keyRegex );
    if( !matches || !matches.length ){
        return undefined;
    }
    matches = matches.splice( 1 );
    if( matches.length === 1 ){
        return matches[0];
    }
    return matches;
}

// ============================================================================
    return {
        get : get
    };
});
