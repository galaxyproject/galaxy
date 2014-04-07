var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Testing registration of new users', 0, function suite( test ){
    spaceghost.start();

    // =================================================================== globals and helpers
    var email = spaceghost.user.getRandomEmail(),
        password = '123456',
        confirm = password,
        username = 'test' + Date.now();

    // =================================================================== TESTS
    spaceghost.openHomePage( function(){
        this.test.comment( 'loading galaxy homepage' );
        this.test.assertTitle( 'Galaxy' );
        this.test.assertExists( xpath( "//div[@id='masthead']" ), 'found masthead' );
    });

    // ------------------------------------------------------------------- register a new user
    spaceghost.then( function(){
        this.test.comment( 'registering user: ' + email );
        this.user._submitRegistration( email, password, username, confirm );
    });
    spaceghost.openHomePage( function(){
        this.clickLabel( 'User' );
        var loggedInAs = this.fetchText( xpath( spaceghost.data.selectors.masthead.userMenu.userEmail_xpath ) );
        this.test.assert( loggedInAs.indexOf( email ) !== -1, 'found proper email in user menu: ' + loggedInAs );
    });

    // ------------------------------------------------------------------- log out that user
    spaceghost.user.logout().openHomePage( function(){
        var emailSelector = xpath( this.data.selectors.masthead.userMenu.userEmail_xpath );
        this.test.assert( !this.elementInfoOrNull( emailSelector ), 'user email not found' );
    });

    // ------------------------------------------------------------------- bad user registrations
    spaceghost.then( function(){
        this.test.comment( 'attempting to re-register user: ' + email );
        this.user._submitRegistration( email, password, username, confirm );
    });
    spaceghost.then(function(){
        this.assertErrorMessage( 'User with that email already exists' );
    });

    // emails must be in the form -@-.- (which is an email on main, btw)
    var badEmails = [ 'bob', 'bob@', 'bob@idontwanttocleanup', 'bob.cantmakeme' ];
    spaceghost.each( badEmails, function( self, badEmail ){
        self.then( function(){
            this.test.comment( 'attempting bad email: ' + badEmail );
            this.user._submitRegistration( badEmail, password, username, confirm );
        });
        self.then(function(){
            this.assertErrorMessage( 'Please enter your valid email address' );
        });
    });

    // passwords must be at least 6 chars long
    var badPasswords = [ '1234' ];
    spaceghost.each( badPasswords, function( self, badPassword ){
        self.then( function(){
            this.test.comment( 'attempting bad password: ' + badPassword );
            this.user._submitRegistration( spaceghost.user.getRandomEmail(), badPassword, username, badPassword );
        });
        self.then(function(){
            this.assertErrorMessage( 'Please use a password of at least 6 characters' );
        });
    });

    // and confirm must match
    var badConfirms = [ '1234', '12345678', '123456 7', '' ];
    spaceghost.each( badConfirms, function( self, badConfirm ){
        self.then( function(){
            this.test.comment( 'attempting bad password confirmation: ' + badConfirm );
            this.user._submitRegistration( spaceghost.user.getRandomEmail(), password, username, badConfirm );
        });
        self.then(function(){
            this.assertErrorMessage( 'Passwords don\'t match' );
        });
    });

    // usernames must be >=4 chars...
    //NOTE: that short username errors only show AFTER checking for existing/valid emails
    //  so: we need to generate new emails for each one
    spaceghost.then( function(){
        var newEmail = spaceghost.user.getRandomEmail(),
            badUsername = 'bob';
        this.test.comment( 'attempting short username: ' + badUsername );
        this.user._submitRegistration( newEmail, password, badUsername, confirm );
    });
    spaceghost.then(function(){
        this.assertErrorMessage( 'Public name must be at least 4 characters in length' );
    });

    // ...and be lower-case letters, numbers and '-'...
    var badUsernames = [ 'BOBERT', 'Robert Paulson', 'bobert!', 'bob_dobbs' ];
    spaceghost.each( badUsernames, function( self, badUsername ){
        self.then( function(){
            var newEmail = spaceghost.user.getRandomEmail();
            this.test.comment( 'attempting bad username: ' + badUsername );
            this.user._submitRegistration( newEmail, password, badUsername, confirm );
        });
        self.then(function(){
            this.assertErrorMessage( 'Public name must contain only lowercase letters, numbers and "-"' );
        });
    });

    // ...and the name can't be used already
    spaceghost.then( function(){
        var newEmail = spaceghost.user.getRandomEmail();
        this.test.comment( 'attempting previously used username with new user: ' + newEmail );
        this.user._submitRegistration( newEmail, password, username, confirm );
    });
    spaceghost.then(function(){
        this.assertErrorMessage( 'Public name is taken; please choose another' );
    });

    // ------------------------------------------------------------------- test the convenience fns
    // these versions are for conv. use in other tests, they should throw errors if used improperly
    spaceghost.then( function(){
        this.assertStepsRaise( 'RegistrationError', function(){
            this.then( function(){
                this.test.comment( 'testing (js) error thrown on bad email' );
                this.user.registerUser( '@internet', '123456', 'ignobel' );
            });
        });
    });

    // ===================================================================
    spaceghost.run( function(){
        test.done();
    });
});

