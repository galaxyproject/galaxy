var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Test the user API', 0, function suite( test ){
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
spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){

    // ------------------------------------------------------------------------------------------- INDEX
    this.test.comment( 'index should get a list of users' );
    var userIndex = this.api.users.index();
    this.debug( this.jsonStr( userIndex ) );
    this.test.assert( utils.isArray( userIndex ), "index returned an array: length " + userIndex.length );

    // need a way to import/create a user here for testing
    if( userIndex.length <= 0 ){
        log.warn( 'No users available' );
        return;
    }
    this.test.assert( userIndex.length >= 1, 'Has at least one user' );

    //TODO: index( deleted )

    // ------------------------------------------------------------------------------------------- SHOW
    this.test.comment( 'show should get detailed data about the user with the given id' );
    var userShow = this.api.users.show( userIndex[0].id );
    this.debug( this.jsonStr( userShow ) );

    //TODO: show( current )
    //TODO: show( deleted )

    // ------------------------------------------------------------------------------------------- CREATE

    // ------------------------------------------------------------------------------------------- MISC
});

// ===================================================================
    spaceghost.run( function(){ test.done(); });
});
