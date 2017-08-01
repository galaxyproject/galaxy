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

    /** Routes */
    var AdminRouter = Router.extend({
        routes: {
            '(/)admin(/)users' : 'show_users',
            '(/)admin(/)roles' : 'show_roles'
        },

        authenticate: function( args, name ) {
            return Galaxy.user && Galaxy.user.id && Galaxy.user.get( 'is_admin' );
        },

        show_users: function() {
            this.page.display( new GridView( { url_base: Galaxy.root + 'admin/users_list', url_data: Galaxy.params, dict_format: true } ) );
        },

        show_roles: function() {
            this.page.display( new GridView( { url_base: Galaxy.root + 'admin/roles_list', url_data: Galaxy.params, dict_format: true } ) );
        }
    });

    $(function() {
        _.extend( options.config, { active_view : 'admin' } );
        Galaxy.page = new Page.View( _.extend( options, {
            Left    : AdminPanel,
            Router  : AdminRouter
        } ) );
    });
};