try {
    var utils = require( 'utils' ),
        xpath = require( 'casper' ).selectXPath,
        format = utils.format,

        //...if there's a better way - please let me know, universe
        scriptDir = require( 'system' ).args[3]
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

    spaceghost.start();

} catch( error ){
    console.debug( error );
    phantom.exit( 1 );
}

// =================================================================== globals and helpers
var email = spaceghost.user.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
}

var userEmailSelector = '//a[contains(text(),"Logged in as")]';

// =================================================================== TESTS
// register a user (again...)
spaceghost.openHomePage()
    .user.registerUser( email, password )
    .user.logout();

spaceghost.openHomePage( function(){
    this.test.comment( 'log out should be reflected in user menu' );
    this.test.assertDoesntExist( xpath( userEmailSelector ) );
    this.test.assert( spaceghost.user.loggedInAs() === '', 'loggedInAs() is empty string' );
});

// log them back in - check for email in logged in text
spaceghost.then( function(){
    this.test.comment( 'logging back in: ' + email );
    spaceghost.user._submitLogin( email, password ); //No such user
});
spaceghost.openHomePage( function(){
    this.test.assertSelectorHasText( xpath( userEmailSelector ), email );
    this.test.assert( spaceghost.user.loggedInAs() === email, 'loggedInAs() matches email' );
});

// finally log back out for next tests
spaceghost.user.logout();

// ------------------------------------------------------------------- shouldn't work
// can't log in: users that don't exist, bad emails, sql injection (hurhur)
var badEmails = [ 'test2@test.org', 'test', '', "'; SELECT * FROM galaxy_user WHERE 'u' = 'u';" ];
spaceghost.each( badEmails, function( self, badEmail ){
    self.then( function(){
        this.test.comment( 'attempting bad email: ' + badEmail );
        this.user._submitLogin( badEmail, password );
    });
    self.then(function(){
        this.assertErrorMessage( 'No such user' );
    });
});

// can't use passwords that wouldn't be accepted in registration
var badPasswords = [ '1234', '', '; SELECT * FROM galaxy_user' ];
spaceghost.each( badPasswords, function( self, badPassword ){
    self.then( function(){
        this.test.comment( 'attempting bad password: ' + badPassword );
        this.user._submitLogin( email, badPassword );
    });
    self.then(function(){
        this.assertErrorMessage( 'Invalid password' );
    });
});

// ------------------------------------------------------------------- test yoself
// these versions are for conv. use in other tests, they should throw errors if used improperly
spaceghost.then( function(){
    this.assertStepsRaise( 'GalaxyError: LoginError', function(){
        this.then( function(){
            this.test.comment( 'testing (js) error thrown on bad email' );
            this.user.login( 'nihilist', '1234' );
        });
    });
});

spaceghost.then( function(){
    this.assertStepsRaise( 'GalaxyError: LoginError', function(){
        this.then( function(){
            this.test.comment( 'testing (js) error thrown on bad password' );
            this.user.login( email, '1234' );
        });
    });
});
/*
*/
// ===================================================================
spaceghost.run( function(){
    this.test.done();
});
