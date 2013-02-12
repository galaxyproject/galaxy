// have to handle errors here - or phantom/casper won't bail but _HANG_
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
    pass email, etc. for first (successful) registration (for use with other tests)


*/
// =================================================================== globals and helpers
var email = spaceghost.getRandomEmail(),
    password = '123456',
    confirm = password,
    username = 'test' + Date.now();

// =================================================================== TESTS
spaceghost.thenOpen( spaceghost.baseUrl, function(){
    this.test.comment( 'loading galaxy homepage' );
    // can we load galaxy?
    this.test.assertTitle( 'Galaxy' );
    // xpath selector use:
    this.test.assertExists( xpath( "//div[@id='masthead']" ), 'found masthead' );
});

// failing tests for...testing...the tests
//spaceghost.thenOpen( spaceghost.baseUrl, function(){
//    this.test.comment( 'loading galaxy homepage' );
//    // can we load galaxy?
//    this.test.assertTitle( 'Blorgo' );
//    // xpath selector use:
//    this.test.assertExists( xpath( "//div[@id='facebook']" ), 'found facebook' );
//});


// ------------------------------------------------------------------- register a new user
spaceghost.then( function(){
    this.test.comment( 'registering user: ' + email );
    this._submitUserRegistration( email, password, username, confirm );
});
spaceghost.thenOpen( spaceghost.baseUrl, function(){
    this.clickLabel( 'User' );
    this.test.assertSelectorHasText( 'a #user-email', email, '#user-email === ' + email );
});


// ------------------------------------------------------------------- log out that user
spaceghost.then( function(){
    this.test.comment( 'logging out user: ' + email );
    this.logout();
});
spaceghost.then( function(){
    this.debug( 'email:' + this.getElementInfo( 'a #user-email' ).html );
    this.test.assert( !this.getElementInfo( 'a #user-email' ).html, '#user-email is empty' );
});


// ------------------------------------------------------------------- bad user registrations
spaceghost.then( function(){
    this.test.comment( 'attempting to re-register user: ' + email );
    this._submitUserRegistration( email, password, username, confirm );
});
spaceghost.then(function(){
    this.assertErrorMessage( 'User with that email already exists' );
});

// emails must be in the form -@-.- (which is an email on main, btw)
var badEmails = [ 'bob', 'bob@', 'bob@idontwanttocleanup', 'bob.cantmakeme' ];
spaceghost.each( badEmails, function( self, badEmail ){
    self.then( function(){
        this.test.comment( 'attempting bad email: ' + badEmail );
        this._submitUserRegistration( badEmail, password, username, confirm );
    });
    self.then(function(){
        this.assertErrorMessage( 'Enter a real email address' );
    });
});

// passwords must be at least 6 chars long
var badPasswords = [ '1234' ];
spaceghost.each( badPasswords, function( self, badPassword ){
    self.then( function(){
        this.test.comment( 'attempting bad password: ' + badPassword );
        this._submitUserRegistration( spaceghost.getRandomEmail(), badPassword, username, confirm );
    });
    self.then(function(){
        this.assertErrorMessage( 'Use a password of at least 6 characters' );
    });
});

// and confirm must match
var badConfirms = [ '1234', '12345678', '123456 7', '' ];
spaceghost.each( badConfirms, function( self, badConfirm ){
    self.then( function(){
        this.test.comment( 'attempting bad password confirmation: ' + badConfirm );
        this._submitUserRegistration( spaceghost.getRandomEmail(), password, username, badConfirm );
    });
    self.then(function(){
        this.assertErrorMessage( 'Passwords do not match' );
    });
});

// usernames must be >=4 chars...
//NOTE: that short username errors only show AFTER checking for existing/valid emails
//  so: we need to generate new emails for each one
spaceghost.then( function(){
    var newEmail = spaceghost.getRandomEmail(),
        badUsername = 'bob';
    this.test.comment( 'attempting short username: ' + badUsername );
    this._submitUserRegistration( newEmail, password, badUsername, confirm );
});
spaceghost.then(function(){
    this.assertErrorMessage( 'Public name must be at least 4 characters in length' );
});

// ...and be lower-case letters, numbers and '-'...
var badUsernames = [ 'BOBERT', 'Robert Paulson', 'bobert!', 'bob_dobbs' ];
spaceghost.each( badUsernames, function( self, badUsername ){
    self.then( function(){
        var newEmail = spaceghost.getRandomEmail();
        this.test.comment( 'attempting bad username: ' + badUsername );
        this._submitUserRegistration( newEmail, password, badUsername, confirm );
    });
    self.then(function(){
        this.assertErrorMessage( "Public name must contain only lower-case letters, numbers and '-'" );
    });
});

// ...and the name can't be used already
spaceghost.then( function(){
    var newEmail = spaceghost.getRandomEmail();
    this.test.comment( 'attempting previously used username with new user: ' + newEmail );
    this._submitUserRegistration( newEmail, password, username, confirm );
});
spaceghost.then(function(){
    this.assertErrorMessage( 'Public name is taken; please choose another' );
});


// ------------------------------------------------------------------- test the tests
// these versions are for conv. use in other tests, they should throw errors if used improperly
spaceghost.then( function(){
    this.assertStepsRaise( 'GalaxyError: RegistrationError', function(){
        this.then( function(){
            this.test.comment( 'testing (js) error thrown on bad email' );
            this.registerUser( '@internet', '123456', 'ignobel' );
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
