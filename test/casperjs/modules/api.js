// =================================================================== module object, exports
/** User object constructor.
 *  @param {SpaceGhost} spaceghost  a spaceghost instance
 *  @param {String} apikey          apikey for use when not using session authentication
 */
var API = function API( spaceghost, apikey ){
    this.spaceghost = spaceghost;
    this.apikey = apikey;

    this.encodedIdExpectedLength = 16;
    this.jQueryLocation = '../../static/scripts/libs/jquery/jquery.js';

    this.configuration = new ConfigurationAPI( this );
    this.histories  = new HistoriesAPI( this );
    this.hdas       = new HDAAPI( this );
    this.tools      = new ToolsAPI( this );
    this.workflows  = new WorkflowsAPI( this );
    this.users      = new UsersAPI( this );
    this.visualizations = new VisualizationsAPI( this );
};
exports.API = API;

/** Creates a new api module object.
 *  @param {SpaceGhost} spaceghost a spaceghost instance
 *  @exported
 */
exports.create = function createAPI( spaceghost, apikey ){
    return new API( spaceghost );
};


API.prototype.toString = function toString(){
    return ( this.spaceghost + '.API:'
        + (( this.apikey )?( this.apikey ):( '(session)' )) );
};

// ------------------------------------------------------------------- APIError
/** @class Thrown when Galaxy the API returns an error from a request */
function APIError( msg, status ){
    Error.apply( this, arguments );
    this.name = "APIError";
    this.message = msg;
    this.status = status;
}
APIError.prototype = new Error();
APIError.prototype.constructor = Error;
API.prototype.APIError = APIError;
exports.APIError = APIError;

/* ------------------------------------------------------------------- TODO:
    can we component-ize this to become the basis for js-based api binding/resource

*/
// =================================================================== INTERNAL
var require = patchRequire( require ),
    utils = require( 'utils' );

API.prototype._ajax = function _ajax( url, options ){
    options = options || {};
    options.async = false;

    // PUT data needs to be stringified in jq.ajax and the content changed
    //TODO: server side handling could change this?
    if( ( options.type && [ 'PUT', 'POST' ].indexOf( options.type ) !== -1 )
    &&  ( options.data ) ){
        options.contentType = 'application/json';
        options.data = JSON.stringify( options.data );
    }

    this.ensureJQuery( '../../static/scripts/libs/jquery/jquery.js' );
    var resp = this.spaceghost.evaluate( function( url, options ){
        return jQuery.ajax( url, options );
    }, url, options );
    //this.spaceghost.debug( 'resp: ' + this.spaceghost.jsonStr( resp ) );

    if( resp.status !== 200 ){
        // grrr... this doesn't lose the \n\r\t
        //throw new APIError( resp.responseText.replace( /[\s\n\r\t]+/gm, ' ' ).replace( /"/, '' ) );
        this.spaceghost.debug( 'API error: code: ' + resp.status + ', response:\n' +
            ( resp.responseJSON? this.spaceghost.jsonStr( resp.responseJSON ) : resp.responseText ) );
        throw new APIError( resp.responseText, resp.status );
    }
    return JSON.parse( resp.responseText );
};

// =================================================================== TESTING
/** Checks whether fn raises an error with a message that contains a status and given string.
 *      NOTE: DOES NOT work with steps. @see SpaceGhost#assertStepsRaise
 *  @param {Function} testFn        a function that may throw an error
 *  @param {Integer} statusExpected the HTTP status code expected
 *  @param {String} errMsgContains  some portion of the correct error msg
 *  @private
 */
API.prototype._APIRaises = function _APIRaises( testFn, statusExpected, errMsgContains ){
    var failed = false;
    try {
        testFn.call( this.spaceghost );
    } catch( err ){
        if( ( err.name === 'APIError' )
        &&  ( err.status && err.status === statusExpected )
        &&  ( err.message.indexOf( errMsgContains ) !== -1 ) ){
            failed = true;

        // re-raise other, non-searched-for errors
        } else {
            throw err;
        }
    }
    return failed;
};

/** Simple assert raises.
 *      NOTE: DOES NOT work with steps. @see SpaceGhost#assertStepsRaise
 *  @param {Function} testFn        a function that may throw an error
 *  @param {Integer} statusExpected the HTTP status code expected
 *  @param {String} errMsgContains  some portion of the correct error msg
 *  @param {String} msg             assertion message to display
 */
API.prototype.assertRaises = function assertRaises( testFn, statusExpected, errMsgContains, msg ){
    return this.spaceghost.test.assert( this._APIRaises( testFn, statusExpected, errMsgContains ), msg  );
};

/** Simple assert does not raise.
 *      NOTE: DOES NOT work with steps. @see SpaceGhost#assertStepsRaise
 *  @param {Function} testFn        a function that may throw an error
 *  @param {Integer} statusExpected the HTTP status code expected
 *  @param {String} errMsgContains  some portion of the correct error msg
 *  @param {String} msg             assertion message to display
 */
API.prototype.assertDoesntRaise = function assertDoesntRaise( testFn, statusExpected, errMsgContains, msg ){
    return this.spaceghost.test.assert( !this._APIRaises( testFn, statusExpected, errMsgContains ), msg  );
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
        var absLoc = this.jQueryLocation,
            injected = this.spaceghost.page.injectJs( absLoc );
        if( !injected ){
            throw new APIError( 'Could not inject jQuery' );
        }
    }
};


// =================================================================== CONFIGURATION
var ConfigurationAPI = function ConfigurationAPI( api ){
    this.api = api;
};
ConfigurationAPI.prototype.toString = function toString(){
    return this.api + '.ConfigurationAPI';
};

// -------------------------------------------------------------------
ConfigurationAPI.prototype.urlTpls = {
    index   : 'api/configuration'
};

ConfigurationAPI.prototype.index = function index( deleted ){
    this.api.spaceghost.info( 'configuration.index' );

    return this.api._ajax( this.urlTpls.index, {
        data : {}
    });
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
    undelete: 'api/histories/deleted/%s/undelete',
    update  : 'api/histories/%s',
};

HistoriesAPI.prototype.index = function index( deleted ){
    this.api.spaceghost.info( 'histories.index: ' + (( deleted )?( 'w deleted' ):( '(wo deleted)' )) );

    deleted = deleted || false;
    return this.api._ajax( this.urlTpls.index, {
        data : { deleted: deleted }
    });
};

HistoriesAPI.prototype.show = function show( id, deleted ){
    this.api.spaceghost.info( 'histories.show: ' + [ id, (( deleted )?( 'w deleted' ):( '' )) ] );

    id = ( id === 'most_recently_used' || id === 'current' )?( id ):( this.api.ensureId( id ) );
    deleted = deleted || false;
    return this.api._ajax( utils.format( this.urlTpls.show, id ), {
        data : { deleted: deleted }
    });
};

HistoriesAPI.prototype.create = function create( payload ){
    this.api.spaceghost.info( 'histories.create: ' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create ), {
        type : 'POST',
        data : payload
    });
};

HistoriesAPI.prototype.delete_ = function delete_( id, purge ){
    this.api.spaceghost.info( 'histories.delete: ' + [ id, (( purge )?( '(purge!)' ):( '' )) ] );

    // py.payload <-> ajax.data
    var payload = ( purge )?({ purge: true }):({});
    return this.api._ajax( utils.format( this.urlTpls.delete_, this.api.ensureId( id ) ), {
        type : 'DELETE',
        data : payload
    });
};

HistoriesAPI.prototype.undelete = function undelete( id ){
    //throw ( 'unimplemented' );
    this.api.spaceghost.info( 'histories.undelete: ' + id );

    return this.api._ajax( utils.format( this.urlTpls.undelete, this.api.ensureId( id ) ), {
        type : 'POST'
    });
};

HistoriesAPI.prototype.update = function update( id, payload ){
    this.api.spaceghost.info( 'histories.update: ' + id + ',' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    id = this.api.ensureId( id );
    payload = this.api.ensureObject( payload );
    url = utils.format( this.urlTpls.update, id );

    return this.api._ajax( url, {
        type : 'PUT',
        data : payload
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
    create  : 'api/histories/%s/contents',
    update  : 'api/histories/%s/contents/%s'
};

HDAAPI.prototype.index = function index( historyId, ids ){
    this.api.spaceghost.info( 'hdas.index: ' + [ historyId, ids ] );
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
    this.api.spaceghost.info( 'hdas.show: ' + [ historyId, id, (( deleted )?( 'w/deleted' ):( '' )) ] );

    id = ( id === 'most_recently_used' )?( id ):( this.api.ensureId( id ) );
    deleted = deleted || false;
    return this.api._ajax( utils.format( this.urlTpls.show, this.api.ensureId( historyId ), id ), {
        data : { deleted: deleted }
    });
};

HDAAPI.prototype.create = function create( historyId, payload ){
    this.api.spaceghost.info( 'hdas.create: ' + [ historyId, this.api.spaceghost.jsonStr( payload ) ] );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create, this.api.ensureId( historyId ) ), {
        type : 'POST',
        data : payload
    });
};

HDAAPI.prototype.update = function create( historyId, id, payload ){
    this.api.spaceghost.info( 'hdas.update: ' + [ historyId, id, this.api.spaceghost.jsonStr( payload ) ] );

    // py.payload <-> ajax.data
    historyId = this.api.ensureId( historyId );
    id = this.api.ensureId( id );
    payload = this.api.ensureObject( payload );
    url = utils.format( this.urlTpls.update, historyId, id );

    return this.api._ajax( url, {
        type : 'PUT',
        data : payload
    });
};

HDAAPI.prototype.delete_ = function create( historyId, id, purge ){
    this.api.spaceghost.info( 'hdas.delete_: ' + [ historyId, id ] );
    historyId = this.api.ensureId( historyId );
    id = this.api.ensureId( id );

    // have to attach like GET param - due to body loss in jq
    url = utils.format( this.urlTpls.update, historyId, id );
    if( purge ){
        url += '?purge=True';
    }
    return this.api._ajax( url, {
        type : 'DELETE'
    });
};

//TODO: delete_


// =================================================================== TOOLS
var ToolsAPI = function HDAAPI( api ){
    this.api = api;
};
ToolsAPI.prototype.toString = function toString(){
    return this.api + '.ToolsAPI';
};

// -------------------------------------------------------------------
ToolsAPI.prototype.urlTpls = {
    index   : 'api/tools',
    show    : 'api/tools/%s',
    create  : 'api/tools'
};

ToolsAPI.prototype.index = function index( in_panel, trackster ){
    this.api.spaceghost.info( 'tools.index: ' + [ in_panel, trackster ] );
    var data = {};
    // in_panel defaults to true, trackster defaults to false
    if( in_panel !== undefined ){
        data.in_panel = ( in_panel )?( true ):( false );
    }
    if( in_panel !== undefined ){
        data.trackster = ( trackster )?( true ):( false );
    }
    return this.api._ajax( utils.format( this.urlTpls.index ), {
        data : data
    });
};

ToolsAPI.prototype.show = function show( id ){
    this.api.spaceghost.info( 'tools.show: ' + [ id ] );
    var data = {};

    data.io_details = true;

    return this.api._ajax( utils.format( this.urlTpls.show, id ), {
        data : data
    });
};

ToolsAPI.prototype.create = function create( payload ){
    this.api.spaceghost.info( 'tools.create: ' + [ this.api.spaceghost.jsonStr( payload ) ] );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create ), {
        type : 'POST',
        data : payload
    });
};

//ToolsAPI.prototype.uploadByForm = function upload( historyId, options ){
//    this.api.spaceghost.debug( '-------------------------------------------------' );
//    this.api.spaceghost.info( 'tools.upload: ' + [ historyId, '(contents)', this.api.spaceghost.jsonStr( options ) ] );
//    this.api.ensureId( historyId );
//    options = options || {};
//
//    this.api.spaceghost.evaluate( function( url ){
//        var html = [
//            '<form action="', url, '" method="post" enctype="multipart/form-data">',
//                '<input type="file" name="files_0|file_data">',
//                '<input type="hidden" name="tool_id" />',
//                '<input type="hidden" name="history_id" />',
//                '<input type="hidden" name="inputs" />',
//                '<button type="submit">Submit</button>',
//            '</form>'
//        ];
//        document.write( html.join('') );
//        //document.getElementsByTagName( 'body' )[0].innerHTML = html.join('');
//    }, utils.format( this.urlTpls.create ) );
//
//    this.api.spaceghost.fill( 'form', {
//        'files_0|file_data' : '1.txt',
//        'tool_id'           : 'upload1',
//        'history_id'        : historyId,
//        'inputs'            : JSON.stringify({
//            'file_type'         : 'auto',
//            'files_0|type'      : 'upload_dataset',
//            'to_posix_lines'    : true,
//            'space_to_tabs'     : false,
//            'dbkey'             : '?'
//        })
//    }, true );
//    // this causes the page to switch...I think
//};

/** paste a file - either from a string (options.paste) or from a filesystem file (options.filepath) */
ToolsAPI.prototype.uploadByPaste = function upload( historyId, options ){
    this.api.spaceghost.info( 'tools.upload: ' + [ historyId, this.api.spaceghost.jsonStr( options ) ] );
    this.api.ensureId( historyId );
    options = options || {};

    var inputs = {
        'files_0|NAME'      : options.name  || 'Test Dataset',
        'dbkey'             : options.dbkey || '?',
        'file_type'         : options.ext   || 'auto'
    };
    if( options.filepath ){
        var fs = require( 'fs' );
        inputs[ 'files_0|url_paste' ] = fs.read( options.filepath );

    } else if( options.paste ){
        inputs[ 'files_0|url_paste' ] = options.paste;
    }
    if( options.posix ){
        inputs[ 'files_0|to_posix_lines' ] = 'Yes';
    }
    if( options.tabs ){
        inputs[ 'files_0|space_to_tab' ] = 'Yes';
    }
    return this.api._ajax( utils.format( this.urlTpls.create ), {
        type : 'POST',
        data : {
            tool_id     : 'upload1',
            upload_type : 'upload_dataset',
            history_id  : historyId,
            inputs      : inputs
        }
    });
};

/** post a file to the upload1 tool over ajax */
ToolsAPI.prototype.upload = function upload( historyId, options ){
    this.api.spaceghost.info( 'tools.upload: ' + [ historyId, this.api.spaceghost.jsonStr( options ) ] );
    this.api.ensureId( historyId );
    options = options || {};

    // We can post an upload using jquery and formdata (see below), the more
    //  difficult part is attaching the file without user intervention.
    //  To do this we need to (unfortunately) create a form phantom can attach the file to first.
    this.api.spaceghost.evaluate( function(){
        $( 'body' ).append( '<input type="file" name="casperjs-upload-file" />' );
    });
    this.api.spaceghost.page.uploadFile( 'input[name="casperjs-upload-file"]', options.filepath );

    var inputs = {
        'file_type'         : options.ext || 'auto',
        'files_0|type'      : 'upload_dataset',
        'dbkey'             : options.dbkey || '?'
    };
    if( options.posix ){
        inputs[ 'files_0|to_posix_lines' ] = 'Yes';
    }
    if( options.tabs ){
        inputs[ 'files_0|space_to_tab' ] = 'Yes';
    }
    var response = this.api.spaceghost.evaluate( function( url, historyId, inputs ){
        var file = $( 'input[name="casperjs-upload-file"]' )[0].files[0],
            formData = new FormData();

        formData.append( 'files_0|file_data', file );
        formData.append( 'history_id', historyId );
        formData.append( 'tool_id', 'upload1' );
        formData.append( 'inputs', JSON.stringify( inputs ) );
        return $.ajax({
            url         : url,
            async       : false,
            type        : 'POST',
            data        : formData,
            // when sending FormData don't have jq process or cache the data
            cache       : false,
            contentType : false,
            processData : false,
            // if we don't add this, payload isn't processed as JSON
            headers     : { 'Accept': 'application/json' }
        });
    }, utils.format( this.urlTpls.create ), historyId, inputs );

    if( response.status !== 200 ){
        // grrr... this doesn't lose the \n\r\t
        //throw new APIError( response.responseText.replace( /[\s\n\r\t]+/gm, ' ' ).replace( /"/, '' ) );
        this.api.spaceghost.debug( 'API error: code: ' + response.status + ', response:\n' +
            ( response.responseJSON? this.api.spaceghost.jsonStr( response.responseJSON ) : response.responseText ) );
        throw new APIError( response.responseText, response.status );
    }
    return JSON.parse( response.responseText );
};

/** amount of time allowed to upload a file (before erroring) */
ToolsAPI.prototype.DEFAULT_UPLOAD_TIMEOUT = 30 * 1000;

/** add two casperjs steps - upload a file, wait for the job to complete, and run 'then' when they are */
ToolsAPI.prototype.thenUpload = function thenUpload( historyId, options, then ){
    var spaceghost = this.api.spaceghost,
        uploadedId;

    spaceghost.then( function(){
        var returned = this.api.tools.upload( historyId, options );
        this.debug( 'returned: ' + this.jsonStr( returned ) );
        uploadedId = returned.outputs[0].id;
        this.debug( 'uploadedId: ' + uploadedId );
    });

    spaceghost.debug( '---------------------------------------------------------- timeout: ' + ( options.timeout || spaceghost.api.tools.DEFAULT_UPLOAD_TIMEOUT ) );
    spaceghost.debug( 'timeout: ' + options.timeout );
    spaceghost.debug( 'timeout: ' + spaceghost.api.tools.DEFAULT_UPLOAD_TIMEOUT );
    spaceghost.then( function(){
        this.waitFor(
            function testHdaState(){
                var hda = spaceghost.api.hdas.show( historyId, uploadedId );
                spaceghost.debug( spaceghost.jsonStr( hda.state ) );
                return !( hda.state === 'upload' || hda.state === 'queued' || hda.state === 'running' );
            },
            function _then(){
                spaceghost.info( 'upload finished: ' + uploadedId );
                if( then ){
                    then.call( spaceghost, uploadedId );
                }
                //var hda = spaceghost.api.hdas.show( historyId, uploadedId );
                //spaceghost.debug( spaceghost.jsonStr( hda ) );
            },
            function timeout(){
                throw new APIError( 'timeout uploading file', 408 );
            },
            options.timeout || spaceghost.api.tools.DEFAULT_UPLOAD_TIMEOUT
        );
    });
    return spaceghost;
};

/** add two casperjs steps - upload multiple files (described in optionsArray) and wait for all jobs to complete */
ToolsAPI.prototype.thenUploadMultiple = function thenUploadMultiple( historyId, optionsArray, then ){
    var spaceghost = this.api.spaceghost,
        uploadedIds = [];

    this.api.spaceghost.then( function(){
        var spaceghost = this;
        optionsArray.forEach( function( options ){
            var returned = spaceghost.api.tools.upload( historyId, options );
            spaceghost.debug( 'uploaded:' + spaceghost.jsonStr( returned ) );
            uploadedIds.push( returned.outputs[0].id );
        });
    });

    // wait for every hda to finish running - IOW, don't use uploadedIds
    this.api.spaceghost.then( function(){
        this.debug( this.jsonStr( uploadedIds ) );
        this.waitFor(
            function testHdaStates(){
                var hdas = spaceghost.api.hdas.index( historyId ),
                    running = hdas.filter( function( hda ){
                        return ( hda.state === 'upload' || hda.state === 'queued' || hda.state === 'running' );
                    }).map( function( hda ){
                        return hda.id;
                    });
                //spaceghost.debug( 'still uploading: ' + spaceghost.jsonStr( running ) );
                return running.length === 0;
            },
            function _then(){
                var hdas = spaceghost.api.hdas.index( historyId );
                spaceghost.debug( spaceghost.jsonStr( hdas ) );
                if( then ){
                    then.call( spaceghost, uploadedIds );
                }
            },
            function timeout(){
                throw new APIError( 'timeout uploading files', 408 );
            },
            ( options.timeout || spaceghost.api.tools.DEFAULT_UPLOAD_TIMEOUT ) * optionsArray.length
        );
    });
    return spaceghost;
};


// =================================================================== WORKFLOWS
var WorkflowsAPI = function WorkflowsAPI( api ){
    this.api = api;
};
WorkflowsAPI.prototype.toString = function toString(){
    return this.api + '.WorkflowsAPI';
};

// -------------------------------------------------------------------
WorkflowsAPI.prototype.urlTpls = {
    index   : 'api/workflows',
    show    : 'api/workflows/%s',
    // run a workflow
    create  : 'api/workflows',
    update  : 'api/workflows/%s',

    upload  : 'api/workflows/upload', // POST
    download: 'api/workflows/download/%s' // GET
};

WorkflowsAPI.prototype.index = function index(){
    this.api.spaceghost.info( 'workflows.index: ' + [] );
    var data = {};

    return this.api._ajax( utils.format( this.urlTpls.index ), {
        data : data
    });
};

WorkflowsAPI.prototype.show = function show( id ){
    this.api.spaceghost.info( 'workflows.show: ' + [ id ] );
    var data = {};

    id = ( id === 'most_recently_used' )?( id ):( this.api.ensureId( id ) );
    return this.api._ajax( utils.format( this.urlTpls.show, this.api.ensureId( id ) ), {
        data : data
    });
};

WorkflowsAPI.prototype.create = function create( payload ){
    this.api.spaceghost.info( 'workflows.create: ' + [ this.api.spaceghost.jsonStr( payload ) ] );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create ), {
        type : 'POST',
        data : payload
    });
};

WorkflowsAPI.prototype.upload = function create( workflowJSON ){
    this.api.spaceghost.info( 'workflows.upload: ' + [ this.api.spaceghost.jsonStr( workflowJSON ) ] );

    return this.api._ajax( utils.format( this.urlTpls.upload ), {
        type : 'POST',
        data : { 'workflow': this.api.ensureObject( workflowJSON ) }
    });
};


// =================================================================== USERS
var UsersAPI = function UsersAPI( api ){
    this.api = api;
};
UsersAPI.prototype.toString = function toString(){
    return this.api + '.UsersAPI';
};

// -------------------------------------------------------------------
//NOTE: lots of admin only functionality in this section
UsersAPI.prototype.urlTpls = {
    index   : 'api/users',
    show    : 'api/users/%s',
    create  : 'api/users',
    delete_ : 'api/users/%s',
    undelete: 'api/users/deleted/%s/undelete',
    update  : 'api/users/%s'
};

UsersAPI.prototype.index = function index( deleted ){
    this.api.spaceghost.info( 'users.index: ' + (( deleted )?( 'w deleted' ):( '(wo deleted)' )) );

    deleted = deleted || false;
    return this.api._ajax( this.urlTpls.index, {
        data : { deleted: deleted }
    });
};

UsersAPI.prototype.show = function show( id, deleted ){
    this.api.spaceghost.info( 'users.show: ' + [ id, (( deleted )?( 'w deleted' ):( '' )) ] );

    id = ( id === 'current' )?( id ):( this.api.ensureId( id ) );
    deleted = deleted || false;
    return this.api._ajax( utils.format( this.urlTpls.show, id ), {
        data : { deleted: deleted }
    });
};

UsersAPI.prototype.create = function create( payload ){
    this.api.spaceghost.info( 'users.create: ' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create ), {
        type : 'POST',
        data : payload
    });
};

UsersAPI.prototype.delete_ = function delete_( id, purge ){
    this.api.spaceghost.info( 'users.delete: ' + [ id, (( purge )?( '(purge!)' ):( '' )) ] );

    // py.payload <-> ajax.data
    var payload = ( purge )?({ purge: true }):({});
    return this.api._ajax( utils.format( this.urlTpls.delete_, this.api.ensureId( id ) ), {
        type : 'DELETE',
        data : payload
    });
};

UsersAPI.prototype.undelete = function undelete( id ){
    //throw ( 'unimplemented' );
    this.api.spaceghost.info( 'users.undelete: ' + id );

    return this.api._ajax( utils.format( this.urlTpls.undelete, this.api.ensureId( id ) ), {
        type : 'POST'
    });
};

UsersAPI.prototype.update = function create( id, payload ){
    this.api.spaceghost.info( 'users.update: ' + id + ',' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    id = this.api.ensureId( id );
    payload = this.api.ensureObject( payload );
    url = utils.format( this.urlTpls.update, id );

    return this.api._ajax( url, {
        type : 'PUT',
        data : payload
    });
};


// =================================================================== VISUALIZATIONS
var VisualizationsAPI = function VisualizationsAPI( api ){
    this.api = api;
};
VisualizationsAPI.prototype.toString = function toString(){
    return this.api + '.VisualizationsAPI';
};

// -------------------------------------------------------------------
VisualizationsAPI.prototype.urlTpls = {
    index   : 'api/visualizations',
    show    : 'api/visualizations/%s',
    create  : 'api/visualizations',
    //delete_ : 'api/visualizations/%s',
    //undelete: 'api/visualizations/deleted/%s/undelete',
    update  : 'api/visualizations/%s'
};

VisualizationsAPI.prototype.index = function index(){
    this.api.spaceghost.info( 'visualizations.index' );

    return this.api._ajax( this.urlTpls.index );
};

VisualizationsAPI.prototype.show = function show( id ){
    this.api.spaceghost.info( 'visualizations.show' );

    return this.api._ajax( utils.format( this.urlTpls.show, this.api.ensureId( id ) ) );
};

VisualizationsAPI.prototype.create = function create( payload ){
    this.api.spaceghost.info( 'visualizations.create: ' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    payload = this.api.ensureObject( payload );
    return this.api._ajax( utils.format( this.urlTpls.create ), {
        type : 'POST',
        data : payload
    });
};

VisualizationsAPI.prototype.update = function create( id, payload ){
    this.api.spaceghost.info( 'visualizations.update: ' + id + ',' + this.api.spaceghost.jsonStr( payload ) );

    // py.payload <-> ajax.data
    id = this.api.ensureId( id );
    payload = this.api.ensureObject( payload );
    url = utils.format( this.urlTpls.update, id );

    return this.api._ajax( url, {
        type : 'PUT',
        data : payload
    });
};
