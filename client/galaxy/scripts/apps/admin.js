var jQuery = require( 'jquery' ),
    $ = jQuery,
    GalaxyApp = require( 'galaxy' ).GalaxyApp,
    QUERY_STRING = require( 'utils/query-string-parsing' ),
    AdminPanel = require( './panels/admin-panel' ),
    Ui = require( 'mvc/ui/ui-misc' ),
    Page = require( 'layout/page' );

window.app = function app( options, bootstrapped ){
    window.Galaxy = new GalaxyApp( options, bootstrapped );
    Galaxy.debug( 'admin app' );
    Galaxy.params = Galaxy.config.params;

    /** Routes */
    var Router = Backbone.Router.extend({
        // TODO: not many client routes at this point - fill and remove from server.
        // since we're at root here, this may be the last to be routed entirely on the client.
        initialize : function( page, options ){
            this.page = page;
            this.options = options;
        },

        /** helper to push a new navigation state */
        push: function( url, data ) {
            data = data || {};
            data.__identifer = Math.random().toString( 36 ).substr( 2 );
            if ( !$.isEmptyObject( data ) ) {
                url += url.indexOf( '?' ) == -1 ? '?' : '&';
                url += $.param( data , true );
            }
            this.navigate( url, { 'trigger': true } );
        },

        /** override to parse query string into obj and send to each route */
        execute: function( callback, args, name ){
            Galaxy.debug( 'router execute:', callback, args, name );
            var queryObj = QUERY_STRING.parse( args.pop() );
            args.push( queryObj );
            if( callback ){
                if ( this.authenticate( args, name ) ) {
                    callback.apply( this, args );
                } else {
                    this.page.display( new Ui.Message( { status: 'danger', message: 'You must be logged in as admin user to make this request.', persistent: true } ) );
                }
            }
        },

        routes: {
            '(/)admin(/)user' : 'show_user'
        },

        authenticate: function( args, name ) {
            return Galaxy.user && Galaxy.user.id && Galaxy.user.get( 'is_admin' );
        },

        show_user: function() {
        }
    });

    $(function(){
        _.extend( options.config, { active_view : 'admin' } );
        Galaxy.page = new Page.View( _.extend( options, {
            Left    : AdminPanel,
            Router  : Router
        } ) );

        // start the router - which will call any of the routes above
        Backbone.history.start({
            root        : Galaxy.root,
            pushState   : true,
        });
    });
};