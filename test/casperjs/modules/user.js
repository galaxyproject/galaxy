// =================================================================== module object, exports
/** Creates a new user module object.
 *  @exported
 */
exports.create = function createUser( spaceghost ){
    return new User( spaceghost );
};

/** User object constructor.
 *  @param {SpaceGhost} spaceghost a spaceghost instance
 */
var User = function User( spaceghost ){
    //??: circ ref?
    this.spaceghost = spaceghost;
};
exports.User = User;

User.prototype.toString = function toString(){
    return this.spaceghost + '.User';
};


// =================================================================== INTERNAL
var xpath = require( 'casper' ).selectXPath;

/** Tests registering a new user on the Galaxy instance by submitting the registration form.
 *      NOTE: this version does NOT throw an error on a bad registration.
 *      It is meant for testing the registration functionality and, therefore, is marked as private.
 *      Other tests should use registerUser
 *  @param {String} email       the users email address
 *  @param {String} password    the users password
 *  @param {String} username    the users ...username! (optional: will use 1st part of email)
 *  @param {String} confirm     password confirmation (optional: defaults to password)
 */
User.prototype._submitRegistration = function _submitRegistration( email, password, username, confirm ){
    var spaceghost = this.spaceghost,
        userInfo = {
            email   : email,
            password: password,
            // default username to first part of email
            username:( !username && email.match( /^\w*/ ) )?( email.match( /^\w*/ )[0] ):( username ),
            // default confirm: duplicate of password
            confirm : ( confirm !== undefined )?( confirm ):( password )
        };

    spaceghost.thenOpen( spaceghost.baseUrl, function(){
        this.clickLabel( spaceghost.data.labels.masthead.menus.user );
        this.clickLabel( spaceghost.data.labels.masthead.userMenu.register );

        this.withMainPanel( function mainBeforeRegister(){
            spaceghost.debug( '(' + spaceghost.getCurrentUrl() + ') registering user:\n'
                + spaceghost.jsonStr( userInfo ) );
            this.fill( spaceghost.data.selectors.registrationPage.form, userInfo, false );
            // need manual submit (not a normal html form)
            this.click( xpath( spaceghost.data.selectors.registrationPage.submit_xpath ) );
        });

        //// debugging
        //spaceghost.withFrame( spaceghost.data.selectors.frames.main, function mainAfterRegister(){
        //    var messageInfo = spaceghost.getElementInfo( spaceghost.data.selectors.messages.all );
        //    spaceghost.debug( 'post registration message:\n' + spaceghost.jsonStr( messageInfo ) );
        //});
    });
};

/** Tests logging in a user on the Galaxy instance by submitting the login form.
 *      NOTE: this version does NOT throw an error on a bad login.
 *      It is meant for testing the login functionality and, therefore, is marked as private.
 *      Other tests should use login
 *  @param {String} email       the users email address
 *  @param {String} password    the users password
 */
User.prototype._submitLogin = function _submitLogin( email, password ){
    var spaceghost = this.spaceghost,
        loginInfo = {
        //NOTE: keys are used as name selectors in the fill fn - must match the names of the inputs
            email: email,
            password: password
        };

    spaceghost.thenOpen( spaceghost.baseUrl, function(){
        spaceghost.clickLabel( spaceghost.data.labels.masthead.menus.user );
        spaceghost.clickLabel( spaceghost.data.labels.masthead.userMenu.login );

        spaceghost.withMainPanel( function mainBeforeLogin(){
            spaceghost.debug( '(' + spaceghost.getCurrentUrl() + ') logging in user:\n'
                + spaceghost.jsonStr( loginInfo ) );
            spaceghost.fill( spaceghost.data.selectors.loginPage.form, loginInfo, false );
            spaceghost.click( xpath( spaceghost.data.selectors.loginPage.submit_xpath ) );
        });

        //// debugging
        //spaceghost.withFrame( spaceghost.data.selectors.frames.main, function mainAfterLogin(){
        //    //TODO: prob. could use a more generalized form of this for url breakdown/checking
        //    if( spaceghost.getCurrentUrl().search( spaceghost.data.selectors.loginPage.url_regex ) != -1 ){
        //        var messageInfo = spaceghost.getElementInfo( spaceghost.data.selectors.messages.all );
        //        spaceghost.debug( 'post login message:\n' + spaceghost.jsonStr( messageInfo ) );
        //    }
        //});
    });
};


// =================================================================== API (external)
/** Register a new user on the Galaxy instance.
 *  @param {String} email       the users email address
 *  @param {String} password    the users password
 *  @param {String} username    the users ...username! (optional: will use 1st part of email)
 *  @returns {SpaceGhost} the spaceghost instance (for chaining)
 */
User.prototype.registerUser = function registerUser( email, password, username ){
    //TODO: callback
    var spaceghost = this.spaceghost;
    this._submitRegistration( email, password, username );
    spaceghost.withMainPanel( function mainAfterRegister(){
        var messageInfo = this.getElementInfo( spaceghost.data.selectors.messages.all );
        this.debug( 'post registration message:\n' + this.jsonStr( this.quickInfo( messageInfo ) ) );

        if( messageInfo.attributes[ 'class' ] === 'errormessage' ){
            this.warning( 'Registration failed: ' + messageInfo.text );
            throw new spaceghost.GalaxyError( 'RegistrationError: ' + messageInfo.text );
        }
    });
    return spaceghost;
};

/** Logs in a user. Throws error on bad log in.
 *  @param {String} email       the users email address
 *  @param {String} password    the users password
 *  @returns {SpaceGhost} the spaceghost instance (for chaining)
 */
User.prototype.login = function login( email, password ){
    var spaceghost = this.spaceghost;

    this._submitLogin( email, password );
    spaceghost.withMainPanel( function mainAfterLogin(){
        if( spaceghost.getCurrentUrl().search( spaceghost.data.selectors.loginPage.url_regex ) != -1 ){
            var messageInfo = spaceghost.getElementInfo( spaceghost.data.selectors.messages.all );
            if( messageInfo && messageInfo.attributes[ 'class' ] === 'errormessage' ){
                this.warning( 'Login failed: ' + messageInfo.text );
                throw new spaceghost.GalaxyError( 'LoginError: ' + messageInfo.text );
            }
        }
        if( spaceghost.user.loggedInAs() === email ){
            spaceghost.info( 'logged in as ' + email );
        }
    });
    return spaceghost;
};

/** Fetch the email of the currently logged in user (or '' if not logged in)
 *  @returns {String} email of currently logged in user or '' if no one logged in
 */
User.prototype.loggedInAs = function loggedInAs(){
    var spaceghost = this.spaceghost,
        userEmail = '';
    try {
        var loggedInInfo = spaceghost.getElementInfo(
            xpath( spaceghost.data.selectors.masthead.userMenu.userEmail_xpath ) );
        userEmail = loggedInInfo.text;
    } catch( err ){
        spaceghost.error( err );
    }
    //console.debug( 'loggedInInfo:', spaceghost.jsonStr( loggedInInfo ) );
    return userEmail;
};

/** Log out the current user
 *  @returns {SpaceGhost} the spaceghost instance (for chaining)
 */
User.prototype.logout = function logout(){
    var spaceghost = this.spaceghost;
    spaceghost.thenOpen( spaceghost.baseUrl, function(){
        //TODO: handle already logged out
        spaceghost.clickLabel( spaceghost.data.labels.masthead.menus.user );
        spaceghost.clickLabel( spaceghost.data.labels.masthead.userMenu.logout );
    });
    return spaceghost;
};

/** Attempts to login a user - if that raises an error (LoginError), register the user
 *  @param {String} email       the users email address
 *  @param {String} password    the users password
 *  @param {String} username    the users ...username! (optional: will use 1st part of email)
 *  @returns {SpaceGhost} the spaceghost instance (for chaining)
 */
User.prototype.loginOrRegisterUser = function loginOrRegisterUser( email, password, username ){
    var spaceghost = this.spaceghost;
    // attempt a login, if that fails - register
    spaceghost.tryStepsCatch( function tryToLogin(){
        spaceghost.open( spaceghost.baseUrl ).user.login( email, password );

    }, function failedLoginRegister(){
        spaceghost.open( spaceghost.baseUrl ).user.registerUser( email, password, username );
    });
    return spaceghost;
};

/** Gets a psuedo-random (unique?) email based on the time stamp.
 *      Helpful for testing registration.
 *  @param {String} username    email user (defaults to 'test')
 *  @param {String} domain      email domain (defaults to 'test.test')
 *  @returns {String}           new email as string
 */
User.prototype.getRandomEmail = function getRandomEmail( username, domain ){
    username = username || 'test';
    domain = domain || 'test.test';
    return username + Date.now() + '@' + domain;
};
