/* Utility to load a specific page and output html, page text, or a screenshot
 *  Optionally wait for some time, text, or dom selector
 */
try {
    //...if there's a better way - please let me know, universe
    var scriptDir = require( 'system' ).args[3]
            // remove the script filename
            .replace( /[\w|\.|\-|_]*$/, '' )
            // if given rel. path, prepend the curr dir
            .replace( /^(?!\/)/, './' ),
        spaceghost = require( scriptDir + 'spaceghost' ).create({
            // script options here (can be overridden by CLI)
            //verbose: true,
            //logLevel: debug,
            scriptDir: scriptDir
        });

} catch( error ){
    console.debug( error );
    phantom.exit( 1 );
}
spaceghost.start();

// =================================================================== SET UP
var utils = require( 'utils' );

var email = spaceghost.user.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
}
spaceghost.user.loginOrRegisterUser( email, password );

function hasKeys( object, keysArray ){
    if( !utils.isObject( object ) ){ return false; }
    for( var i=0; i<keysArray.length; i += 1 ){
        if( !object.hasOwnProperty( keysArray[i] ) ){
            spaceghost.debug( 'key not found: ' + keysArray[i] );
            return false;
        }
    }
    return true;
}

function compareObjs( obj1, where ){
    for( var key in where ){
        if( where.hasOwnProperty( key ) ){
            if( !obj1.hasOwnProperty( key )  ){ return false; }
            if( obj1[ key ] !== where[ key ] ){ return false; }
        }
    }
    return true;
}

function findObject( objectArray, where, start ){
    start = start || 0;
    for( var i=start; i<objectArray.length; i += 1 ){
        if( compareObjs( objectArray[i], where ) ){ return objectArray[i]; }
    }
    return null;
}

// =================================================================== TESTS
var workflowSummaryKeys = [
        'id', 'model_class', 'name', 'published', 'tags', 'url'
    ],
    workflowDetailKeys = workflowSummaryKeys.concat([
        'inputs', 'steps'
    ]);


spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){

    // ------------------------------------------------------------------------------------------- INDEX
    this.test.comment( 'index should get a list of workflows' );
    var workflowIndex = this.api.workflows.index();
    this.debug( this.jsonStr( workflowIndex ) );
    this.test.assert( utils.isArray( workflowIndex ), "index returned an array: length " + workflowIndex.length );

    // need a way to import/create a workflow here for testing
    if( workflowIndex.length <= 0 ){
        log.warn( 'No workflows available' );
        return;
    }
    this.test.assert( workflowIndex.length >= 1, 'Has at least one workflow' );

    // ------------------------------------------------------------------------------------------- SHOW
    this.test.comment( 'show should get detailed data about the workflow with the given id' );
    var workflowShow = this.api.workflows.show( workflowIndex[0].id );
    this.debug( this.jsonStr( workflowShow ) );


    // ------------------------------------------------------------------------------------------- CREATE

    // ------------------------------------------------------------------------------------------- MISC
});

// ===================================================================
spaceghost.run( function(){
});
