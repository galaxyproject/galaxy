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
var normKeys = [
        'enable_unique_workflow_defaults',
        'ftp_upload_site',
        'ftp_upload_dir',
        'wiki_url',
        'support_url',
        'logo_url',
        'terms_url',
        'allow_user_dataset_purge'
    ],
    adminKeys = normKeys.concat([
        'library_import_dir',
        'user_library_import_dir',
        'allow_library_path_paste',
        'allow_user_creation',
        'allow_user_deletion'
    ]);


// ------------------------------------------------------------------------------------------- INDEX
spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){

    this.test.comment( 'index should get a (shortened) list of configuration settings '
                     + 'when requested by a normal user' );
    var configIndex = this.api.configuration.index();
    this.debug( this.jsonStr( configIndex ) );
    this.test.assert( utils.isObject( configIndex ), "index returned an object" );
    this.test.assert( hasKeys( configIndex, normKeys ), 'Has the proper keys' );

});
spaceghost.user.logout();

// ------------------------------------------------------------------------------------------- INDEX (admin)
spaceghost.tryStepsCatch( function tryAdminLogin(){
    spaceghost.user.loginAdmin();
});

//}, function failedLoginRegister(){
//    this.info( 'Admin level configuration API tests not run: no admin account available' );
spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){

    if( spaceghost.user.userIsAdmin() ){
        this.test.comment( 'index should get a (full) list of configuration settings '
                         + 'when requested by an admin user' );
        configIndex = this.api.configuration.index();
        this.debug( this.jsonStr( configIndex ) );
        this.test.assert( utils.isObject( configIndex ), "index returned an object" );
        this.test.assert( hasKeys( configIndex, adminKeys ), 'Has the proper keys' );

    } else {
        this.info( 'Admin level configuration API tests not run: no admin account available' );
    }
});

// ===================================================================
spaceghost.run( function(){
});
