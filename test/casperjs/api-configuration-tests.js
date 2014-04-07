var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Test the Galaxy configuration API', 0, function suite( test ){
    spaceghost.start();

// =================================================================== SET UP
var email = spaceghost.user.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
}
spaceghost.user.loginOrRegisterUser( email, password );

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
    this.test.assert( this.hasKeys( configIndex, normKeys ), 'Has the proper keys' );

});
spaceghost.user.logout();

// ------------------------------------------------------------------------------------------- INDEX (admin)
spaceghost.tryStepsCatch( function tryAdminLogin(){
    spaceghost.user.loginAdmin();
}, function(){} );

//}, function failedLoginRegister(){
//    this.info( 'Admin level configuration API tests not run: no admin account available' );
spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){
    spaceghost.waitForMasthead( function() {
        if( spaceghost.user.userIsAdmin() ){
            this.test.comment( 'index should get a (full) list of configuration settings '
                             + 'when requested by an admin user' );
            configIndex = this.api.configuration.index();
            this.debug( this.jsonStr( configIndex ) );
            this.test.assert( utils.isObject( configIndex ), "index returned an object" );
            this.test.assert( this.hasKeys( configIndex, adminKeys ), 'Has the proper keys' );

        } else {
            this.info( 'Admin level configuration API tests not run: no admin account available' );
        }
    });
});

// ===================================================================
    spaceghost.run( function(){ test.done(); });
});

