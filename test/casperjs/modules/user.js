// =================================================================== module object, exports
/** User object constructor.
 *  @param {SpaceGhost} spaceghost a spaceghost instance
 */
var User = function User( spaceghost ){
    //??: circ ref?
    this.spaceghost = spaceghost;
};
exports.User = User;

/** Creates a new user module object.
 *  @exported
 */
exports.create = function createUser( spaceghost ){
    return new User( spaceghost );
};

User.prototype.toString = function toString(){
    return this.spaceghost + '.User';
};


// =================================================================== INTERNAL
var require = patchRequire( require ),
    xpath = require( 'casper' ).selectXPath;

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

    spaceghost.openHomePage( function(){
        this.clickLabel( spaceghost.data.labels.masthead.menus.user );
        this.clickLabel( spaceghost.data.labels.masthead.userMenu.register );

        this.waitForNavigation( 'user/create', function beforeRegister(){
            this.withMainPanel( function mainBeforeRegister(){
                spaceghost.debug( '(' + spaceghost.getCurrentUrl() + ') registering user:\n'
                    + spaceghost.jsonStr( userInfo ) );
                this.fill( spaceghost.data.selectors.registrationPage.form, userInfo, false );
                // need manual submit (not a normal html form)
                this.click( xpath( spaceghost.data.selectors.registrationPage.submit_xpath ) );
            });
            this.waitForNavigation( 'user/create', function afterRegister(){
            //    this.withMainPanel( function mainAfterRegister(){
            //        var messageInfo = spaceghost.getElementInfo( spaceghost.data.selectors.messages.all );
            //        spaceghost.debug( 'post registration message:\n' + spaceghost.jsonStr( messageInfo ) );
            //    });
            });
        });

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

    spaceghost.openHomePage( function(){
        this.clickLabel( spaceghost.data.labels.masthead.menus.user );
        this.clickLabel( spaceghost.data.labels.masthead.userMenu.login );

        this.waitForNavigation( 'user/login', function beforeLogin(){
            this.withMainPanel( function mainBeforeLogin(){
                spaceghost.debug( '(' + spaceghost.getCurrentUrl() + ') logging in user:\n'
                    + spaceghost.jsonStr( loginInfo ) );
                spaceghost.fill( spaceghost.data.selectors.loginPage.form, loginInfo, false );
                spaceghost.click( xpath( spaceghost.data.selectors.loginPage.submit_xpath ) );
            });
        });

        this.waitForNavigation( 'user/login', function afterLogin(){
            //this.withMainPanel( function mainAfterLogin(){
            //    var messageInfo = spaceghost.getElementInfo( spaceghost.data.selectors.messages.all );
            //    spaceghost.debug( 'post login message:\n' + spaceghost.jsonStr( messageInfo ) );
            //});
        });
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
        
        this.clickLabel( 'Return to the home page.' );
        this.waitForNavigation( '' );
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
    //spaceghost.withMainPanel( function mainAfterLogin(){
    //    if( spaceghost.getCurrentUrl().search( spaceghost.data.selectors.loginPage.url_regex ) !== -1 ){
    //        var messageInfo = spaceghost.getElementInfo( spaceghost.data.selectors.messages.all );
    //        if( messageInfo && messageInfo.attributes[ 'class' ] === 'errormessage' ){
    //            this.warning( 'Login failed: ' + messageInfo.text );
    //            throw new spaceghost.GalaxyError( 'LoginError: ' + messageInfo.text );
    //        }
    //    }
    //});
    this.spaceghost.then( function checkLogin(){
        if( spaceghost.user.loggedInAs() !== email ){
            throw new spaceghost.GalaxyError( 'LoginError' );
        } else {
            spaceghost.info( 'logged in as ' + email );
        }
    });
    return spaceghost;
};

/** Fetch the email of the currently logged in user (or '' if not logged in)
 *  @returns {String} email of currently logged in user or '' if no one logged in
 */
User.prototype.loggedInAs = function loggedInAs(){
    var currUser = this.spaceghost.api.users.show( 'current' );
    //this.spaceghost.debug( this.spaceghost.jsonStr( currUser ) );
    return currUser.email || '';
//TODO: due to late rendering of masthead this is no longer reliable - need a wait for in the main page
    //return this.spaceghost.jumpToTop( function(){
    //    var userEmail = '';
    //    try {
    //        var emailSelector = xpath( this.data.selectors.masthead.userMenu.userEmail_xpath ),
    //            loggedInInfo = this.elementInfoOrNull( emailSelector );
    //        this.debug( '\n\n' + this.jsonStr( loggedInInfo ) + '\n' );
    //        if( loggedInInfo !== null ){
    //            userEmail = loggedInInfo.text.replace( 'Logged in as ', '' );
    //        }
    //    } catch( err ){
    //        this.warn( err );
    //    }
    //    return userEmail;
    //});
};

/** Log out the current user
 *  @returns {SpaceGhost} the spaceghost instance (for chaining)
 */
User.prototype.logout = function logout(){
    var spaceghost = this.spaceghost;
    this.spaceghost.openHomePage( function(){
        if( spaceghost.user.loggedInAs() ){
            spaceghost.clickLabel( spaceghost.data.labels.masthead.menus.user );
            spaceghost.clickLabel( spaceghost.data.labels.masthead.userMenu.logout );
            spaceghost.waitForNavigation( 'user/logout', function _toLogoutPage() {
                spaceghost.clickLabel( 'go to the home page' );
                spaceghost.waitForNavigation( '' );
            });
        }
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
        spaceghost.openHomePage().user.login( email, password );

    }, function failedLoginRegister(){
        spaceghost.openHomePage().user.registerUser( email, password, username );
    });
    return spaceghost;
};

// ------------------------------------------------------------------- Admin
/** Gets the admin user data from spaceghost if set and checks the galaxy.ini file for the email.
 *  @returns {Object|null} the admin data object (email, pasword, username)
 *      or null if no admin is set in both the galaxy.ini and spaceghost.
 */
User.prototype.getAdminData = function getAdminData(){
    //TODO: this might be better inside sg
    // check for the setting in sg and the galaxy.ini file
    var adminData = this.spaceghost.options.adminUser,
        iniAdminEmails = this.spaceghost.getUniverseSetting( 'admin_users' );
    iniAdminEmails = ( iniAdminEmails )?
        ( iniAdminEmails.split( ',' ).map( function( email ) { return email.trim(); } ) ):( null );

    //TODO: seems like we only need the wsgi setting - that's the only thing we can't change
    if( adminData ){
        if( iniAdminEmails.indexOf( adminData.email ) !== -1 ){ return adminData; }

    // if not set in options, but there are entries in the ini and a default admin pass:
    //  return the first email with the default pass
    //  Hopefully this is no less secure than the user/pwd in twilltestcase
    } else if( iniAdminEmails.length && this.spaceghost.options.adminPassword ){
        return { email: iniAdminEmails[0], password: this.spaceghost.options.adminPassword };
    }

    return null;
};

/** Logs in the admin user (if available) as the current user.
 *      Note: logs out any other current users.
 *  @throws {GalaxyError} err   if specified user is not admin or no admin found
 *  @returns {SpaceGhost} the spaceghost instance (for chaining)
 */
User.prototype.loginAdmin = function loginAdmin(){
    this.spaceghost.then( function(){
        var adminData = this.user.getAdminData();
        if( !adminData ){
            throw new this.GalaxyError( 'No admin users found' );
        }
        this.info( 'logging in administrator' );
        return this.user.loginOrRegisterUser( adminData.email, adminData.password );
    });
};

/** Is the currently logged in user an admin?
 *  @returns {Boolean} true if the currently logged in user is admin, false if not.
 */
User.prototype.userIsAdmin = function userIsAdmin(){
    // simple test of whether the Admin tab is displayed in the masthead
    return this.spaceghost.jumpToTop( function(){
        if( this.visible( this.data.selectors.masthead.adminLink ) ){
            return true;
        }
        return false;
    });
};


// ------------------------------------------------------------------- Utility
/** Gets a psuedo-random (unique?) email based on the time stamp.
 *      Helpful for testing registration.
 *  @param {String} username    email user (defaults to 'test')
 *  @param {String} domain      email domain (defaults to 'test.test')
 *  @returns {String}           new email as string
 */
User.prototype.getRandomEmail = function getRandomEmail( username, domain ){
    username = username || 'test';
    domain = domain || 'test.test';
    var number = Math.ceil( Math.random() * 10000000000000 );
    // doesn't work so well when creating two users at once
    //var number = Date.now();
    return username + number + '@' + domain;
};

