/** @class Model for a Galaxy user (including anonymous users).
 *  @name User
 *
 *  @augments BaseModel
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var User = BaseModel.extend( LoggableMixin ).extend(
/** @lends User.prototype */{

    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,
    
    /** API location for this resource */
    urlRoot : 'api/users',

    /** Model defaults
     *  Note: don't check for anon-users with the username as the default is '(anonymous user)'
     *      a safer method is if( !user.get( 'email' ) ) -> anon user
     */
    defaults : /** @lends User.prototype */{
        id                      : null,
        username                : '(' + _l( "anonymous user" ) + ')',
        email                   : "",
        total_disk_usage        : 0,
        nice_total_disk_usage   : "0 bytes",
        quota_percent           : null
    },

    /** Set up and bind events
     *  @param {Object} data Initial model data.
     */
    initialize : function( data ){
        this.log( 'User.initialize:', data );

        this.on( 'loaded', function( model, resp ){ this.log( this + ' has loaded:', model, resp ); });
        this.on( 'change', function( model, data ){ this.log( this + ' has changed:', model, data.changes ); });
    },

    isAnonymous : function(){
        return ( !this.get( 'email' ) );
    },

    /** Load a user with the API using an id.
     *      If getting an anonymous user or no access to a user id, pass the User.CURRENT_ID_STR
     *      (e.g. 'current') and the API will return the current transaction's user data.
     *  @param {String} idOrCurrent encoded user id or the User.CURRENT_ID_STR
     *  @param {Object} options hash to pass to Backbone.Model.fetch. Can contain success, error fns.
     *  @fires loaded when the model has been loaded from the API, passing the newModel and AJAX response.
     */
    loadFromApi : function( idOrCurrent, options ){
        idOrCurrent = idOrCurrent || User.CURRENT_ID_STR;

        options = options || {};
        var model = this,
            userFn = options.success;

        /** @ignore */
        options.success = function( newModel, response ){
            model.trigger( 'loaded', newModel, response );
            if( userFn ){ userFn( newModel, response ); }
        };

        // requests for the current user must have a sep. constructed url (fetch don't work, ma)
        if( idOrCurrent === User.CURRENT_ID_STR ){
            options.url = this.urlRoot + '/' + User.CURRENT_ID_STR;
        }
        return BaseModel.prototype.fetch.call( this, options );
    },

    /** string representation */
    toString : function(){
        var userInfo = [ this.get( 'username' ) ];
        if( this.get( 'id' ) ){
            userInfo.unshift( this.get( 'id' ) );
            userInfo.push( this.get( 'email' ) );
        }
        return 'User(' + userInfo.join( ':' ) + ')';
    }
});

// string to send to tell server to return this transaction's user (see api/users.py)
User.CURRENT_ID_STR = 'current';

// class method to load the current user via the api and return that model
User.getCurrentUserFromApi = function( options ){
    var currentUser = new User();
    currentUser.loadFromApi( User.CURRENT_ID_STR, options );
    return currentUser;
};

// (stub) collection for users (shouldn't be common unless admin UI)
var UserCollection = Backbone.Collection.extend( LoggableMixin ).extend({
    model   : User,
    urlRoot : 'api/users'
    //logger  : console,
});
