var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Test uploading data to a history', 0, function suite( test ){
    spaceghost.start();

// ===================================================================
/* TODO:

    find a way to error on bad upload?
    general tool execution
*/
// =================================================================== globals and helpers
var email = spaceghost.user.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
}

// =================================================================== TESTS
// ------------------------------------------------------------------- start a new user
spaceghost.user.loginOrRegisterUser( email, password ).openHomePage( function(){
    var loggedInAs = spaceghost.user.loggedInAs();
    this.test.assert( loggedInAs === email, 'loggedInAs() matches email: "' + loggedInAs + '"' );
});

// ------------------------------------------------------------------- api upload
spaceghost.then( function(){
    this.test.comment( 'Test API function' );

    var currHistoryId = spaceghost.api.histories.index()[0].id;
    spaceghost.api.tools.thenUpload( currHistoryId, {
        filepath : '../../test-data/1.sam'
    }, function(){
        var hdas = spaceghost.api.hdas.index( currHistoryId );
        spaceghost.test.assert( hdas.length === 1, 'One dataset uploaded: ' + hdas.length );
        spaceghost.test.assert( hdas[0].state === 'ok', 'State is: ' + hdas[0].state );
        spaceghost.test.assert( hdas[0].name === '1.sam', 'Name is: ' + hdas[0].name );
    });
});

// ===================================================================
    spaceghost.run( function(){ test.done(); });
});
