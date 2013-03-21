// =================================================================== module object, exports
/** Creates a new api module object.
 *  @param {SpaceGhost} spaceghost a spaceghost instance
 *  @exported
 */
exports.create = function createAPI( spaceghost, apikey ){
    return new API( spaceghost );
};

/** User object constructor.
 *  @param {SpaceGhost} spaceghost  a spaceghost instance
 *  @param {String} apikey          apikey for use when not using session authentication
 */
var API = function API( spaceghost, apikey ){
    this.spaceghost = spaceghost;
    this.apikey = apikey;

    this.encodedIdExpectedLength = 16;
    this.jQueryLocation = '../../static/scripts/libs/jquery/jquery.js';

    this.histories  = new HistoriesAPI( this );
    this.hdas       = new HDAAPI( this );
};
exports.API = API;

API.prototype.toString = function toString(){
    return ( this.spaceghost + '.API:'
        + (( this.apikey )?( this.apikey ):( '(session)' )) );
};

// ------------------------------------------------------------------- APIError
APIError.prototype = new Error();
APIError.prototype.constructor = Error;
/** @class Thrown when Galaxy the API returns an error from a request */
function APIError( msg ){
    Error.apply( this, arguments );
    this.name = "APIError";
    this.message = msg;
}
exports.APIError = APIError;

/* ------------------------------------------------------------------- TODO:
    can we component-ize this to become the basis for js-based api binding/resource

*/
// =================================================================== INTERNAL
var utils = require( 'utils' );

API.prototype._ajax = function _ajax( url, options ){
    options = options || {};
    options.async = false;

    this.ensureJQuery( '../../static/scripts/libs/jquery/jquery.js' );
    var resp = this.spaceghost.evaluate( function( url, options ){
        return jQuery.ajax( url, options );
    }, url, options );
    //this.spaceghost.debug( 'resp: ' + this.spaceghost.jsonStr( resp ) );

    if( resp.status !== 200 ){
        // grrr... this doesn't lose the \n\r\t
        throw new APIError( resp.responseText.replace( /[\s\n\r\t]+/gm, ' ' ).replace( /"/, '' ) );
    }
    return JSON.parse( resp.responseText );
};

// =================================================================== MISC
API.prototype.isEncodedId = function isEncodedId( id ){
    if( typeof id !== 'string' ){ return false; }
    if( id.match( /[g-zG-Z]/ ) ){ return false; }
    return ( id.length === this.encodedIdExpectedLength );
};

// ------------------------------------------------------------------- is type or throw err
API.prototype.ensureId = function ensureId( id ){
    if( !this.isEncodedId( id ) ){
        throw new APIError( 'ID is not a valid encoded id: ' + id );
    }
    return id;
};

API.prototype.ensureObject = function ensureObject( obj ){
    if( !utils.isObject( obj ) ){
        throw new APIError( 'Not a valid object: ' + obj );
    }
    return obj;
};

// ------------------------------------------------------------------- jquery
// using jq for the ajax in this module - that's why these are here
//TODO:?? could go in spaceghost
API.prototype.hasJQuery = function hasJQuery(){
    return this.spaceghost.evaluate( function pageHasJQuery(){
        var has = false;
        try {
            has = typeof ( jQuery + '' ) === 'string';
        } catch( err ){}
        return has;
    });
};

API.prototype.ensureJQuery = function ensureJQuery(){
    if( !this.hasJQuery() ){
        var absLoc = this.spaceghost.options.scriptDir + this.jQueryLocation,
            injected = this.spaceghost.page.injectJs( absLoc );
        if( !injected ){
            throw new APIError( 'Could not inject jQuery' );
        }
    }
};


// =================================================================== HISTORIES
var HistoriesAPI = function HistoriesAPI( api ){
    this.api = api;
};
HistoriesAPI.prototype.toString = function toString(){
    return this.api + '.HistoriesAPI';
};

// -------------------------------------------------------------------
HistoriesAPI.prototype.urlTpls = {
    index   : 'api/histories',
    show    : 'api/histories/%s',
    create  : 'api/histories',
    delete_ : 'api/histories/%s',
    undelete: 'api/histories/deleted/%s/undelete'
};

HistoriesAPI.prototype.index = function index( deleted ){
    this.api.spaceghost.info( 'history.index: ' + (( deleted )?( 'w deleted' ):( '(wo deleted)' )) );

    deleted = deleted || false;
    return this.api._ajax( this.urlTpls.index, {
        data : { deleted: deleted }
    });
};

HistoriesAPI.prototype.show = function show( id, deleted ){
    this.api.spaceghost.info( 'history.show: ' + [ id, (( deleted )?( 'w deleted' ):( '' )) ] );

    id = ( id === 'most_recently_used' )?( id ):( this.api.ensureId( id ) );
    deleted = deleted || false;
    return this.api._ajax( utils.format( this.urlTpls.show, id ), {
        data : { deleted: deleted }
    });
};

HistoriesAPI.prototype.create = function create( payload ){
    this.api.spaceghost.info( 'history.create: ' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create ), {
        type : 'POST',
        data : payload
    });
};

HistoriesAPI.prototype.delete_ = function delete_( id, purge ){
    this.api.spaceghost.info( 'history.delete: ' + [ id, (( purge )?( '(purge!)' ):( '' )) ] );

    // py.payload <-> ajax.data
    var payload = ( purge )?({ purge: true }):({});
    return this.api._ajax( utils.format( this.urlTpls.delete_, this.api.ensureId( id ) ), {
        type : 'DELETE',
        data : payload
    });
};

HistoriesAPI.prototype.undelete = function undelete( id ){
    //throw ( 'unimplemented' );
    this.api.spaceghost.info( 'history.undelete: ' + id );

    return this.api._ajax( utils.format( this.urlTpls.undelete, this.api.ensureId( id ) ), {
        type : 'POST'
    });
};


// =================================================================== HDAS
var HDAAPI = function HDAAPI( api ){
    this.api = api;
};
HDAAPI.prototype.toString = function toString(){
    return this.api + '.HDAAPI';
};

// -------------------------------------------------------------------
HDAAPI.prototype.urlTpls = {
    index   : 'api/histories/%s/contents',
    show    : 'api/histories/%s/contents/%s',
    create  : 'api/histories/%s/contents'//,
    // not implemented
    //delete_ : 'api/histories/%s',
    //undelete: 'api/histories/deleted/%s/undelete'
};

HDAAPI.prototype.index = function index( historyId, ids ){
    this.api.spaceghost.info( 'history.index: ' + [ historyId, ids ] );
    var data = {};
    if( ids ){
        ids = ( utils.isArray( ids ) )?( ids.join( ',' ) ):( ids );
        data.ids = ids;
    }

    return this.api._ajax( utils.format( this.urlTpls.index, this.api.ensureId( historyId ) ), {
        data : data
    });
};

HDAAPI.prototype.show = function show( historyId, id, deleted ){
    this.api.spaceghost.info( 'history.show: ' + [ id, (( deleted )?( 'w deleted' ):( '' )) ] );

    id = ( id === 'most_recently_used' )?( id ):( this.api.ensureId( id ) );
    deleted = deleted || false;
    return this.api._ajax( utils.format( this.urlTpls.show, id ), {
        data : { deleted: deleted }
    });
};

HDAAPI.prototype.create = function create( historyId, payload ){
    this.api.spaceghost.info( 'history.create: ' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create ), {
        type : 'POST',
        data : payload
    });
};

