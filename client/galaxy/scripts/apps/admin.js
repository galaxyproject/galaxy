var jQuery = require( 'jquery' ),
    $ = jQuery,
    GalaxyApp = require( 'galaxy' ).GalaxyApp,
    AdminPanel = require( './panels/admin-panel' ),
    GridView = require( 'mvc/grid/grid-view' ),
    Ui = require( 'mvc/ui/ui-misc' ),
    Router = require( 'layout/router' ),
    Page = require( 'layout/page' );

window.app = function app( options, bootstrapped ){
    window.Galaxy = new GalaxyApp( options, bootstrapped );
    Galaxy.debug( 'admin app' );
    Galaxy.params = Galaxy.config.params;

    /** Routes */
    var AdminRouter = Router.extend({
        routes: {
            '(/)admin(/)user' : 'show_user'
        },

        authenticate: function( args, name ) {
            return Galaxy.user && Galaxy.user.id && Galaxy.user.get( 'is_admin' );
        },

        show_user: function() {
            this.page.display( new GridView( { url_base: Galaxy.root + 'dataset/list', dict_format: true } ) );
        }
    });

    $(function(){
        _.extend( options.config, { active_view : 'admin' } );
        Galaxy.page = new Page.View( _.extend( options, {
            Left    : AdminPanel,
            Router  : AdminRouter
        } ) );
    });
};