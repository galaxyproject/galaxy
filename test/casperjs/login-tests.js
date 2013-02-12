// have to handle errors here - or phantom/casper won't bail but _HANG_
//TODO: global error handler?
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

// ===================================================================
/* TODO:
    move selectors and assertText strings into global object for easier editing


*/
// =================================================================== globals and helpers
var email = spaceghost.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
}

// =================================================================== TESTS
spaceghost.thenOpen( spaceghost.baseUrl, function(){
    this.test.comment( 'loading galaxy homepage' );
    // can we load galaxy?
    this.test.assertTitle( 'Galaxy' );
});

// ------------------------------------------------------------------- should work

// register a user (again...)
spaceghost.then( function(){
    this.test.comment( 'registering: ' + email );
    spaceghost.registerUser( email, password );
});
// capture a sshot
//spaceghost.then( function(){
//    this.clickLabel( 'User' );
//    this.capture( 'register.png' );
//});

// log them out - check for empty logged in text
spaceghost.then( function(){
    this.test.comment( 'logging out: ' + email );
    spaceghost.logout();
});
spaceghost.then( function(){
    this.test.assertSelectorDoesntHaveText(
        xpath( '//a[contains(text(),"Logged in as")]/span["id=#user-email"]' ), /\w/ );
    this.test.assert( spaceghost.loggedInAs() === '', 'loggedInAs() is empty string' );
});

// log them back in - check for email in logged in text
spaceghost.then( function(){
    this.test.comment( 'logging back in: ' + email );
    spaceghost._submitLogin( email, password ); //No such user
});
spaceghost.then( function(){
    this.test.assertSelectorHasText(
        xpath( '//a[contains(text(),"Logged in as")]/span["id=#user-email"]' ), email );
    this.test.assert( spaceghost.loggedInAs() === email, 'loggedInAs() matches email' );
});

// finally log back out for next tests
spaceghost.then( function(){
    this.test.comment( 'logging out: ' + email );
    spaceghost.logout();
});

// ------------------------------------------------------------------- shouldn't work
// can't log in: users that don't exist, bad emails, sql injection (hurhur)
var badEmails = [ 'test2@test.org', 'test', '', "'; SELECT * FROM galaxy_user WHERE 'u' = 'u';" ];
spaceghost.each( badEmails, function( self, badEmail ){
    self.then( function(){
        this.test.comment( 'attempting bad email: ' + badEmail );
        this._submitLogin( badEmail, password );
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
        this._submitLogin( email, badPassword );
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
            this.login( 'nihilist', '1234' );
        });
    });
});

spaceghost.then( function(){
    this.assertStepsRaise( 'GalaxyError: LoginError', function(){
        this.then( function(){
            this.test.comment( 'testing (js) error thrown on bad password' );
            this.login( email, '1234' );
        });
    });
});

spaceghost.then( function(){
    this.logout();
});

// ===================================================================
spaceghost.run( function(){
    this.test.done();
});
