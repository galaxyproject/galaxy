var User = BaseModel.extend( LoggableMixin ).extend({
    //logger : console,

    defaults : {
        id                      : null,
        username                : "(anonymous user)",
        email                   : "",
        total_disk_usage        : 0,
        nice_total_disk_usage   : "0 bytes"
    },

    initialize : function( data ){
        this.log( 'User.initialize:', data );

        this.on( 'loaded', function( model, resp ){ this.log( this + ' has loaded:', model, resp ); });
        this.on( 'change', function( model, data ){ this.log( this + ' has changed:', model, data.changes ); });
    },

    urlRoot : 'api/users',
    loadFromApi : function( idOrCurrent, options ){
        idOrCurrent = idOrCurrent || User.CURRENT_ID_STR;
        options = options || {};
        var model = this,
            userFn = options.success;
        options.success = function( newModel, response ){
            model.trigger( 'loaded', newModel, response );
            if( userFn ){ userFn( newModel, response ); }
        };
        if( idOrCurrent === User.CURRENT_ID_STR ){
            options.url = this.urlRoot + '/' + User.CURRENT_ID_STR;
        }
        return BaseModel.prototype.fetch.call( this, options );
    },

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
    logger  : console,
    urlRoot : 'api/users'
});
