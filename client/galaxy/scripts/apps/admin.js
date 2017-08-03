var jQuery = require( 'jquery' ),
    $ = jQuery,
    GalaxyApp = require( 'galaxy' ).GalaxyApp,
    AdminPanel = require( './panels/admin-panel' ),
    FormWrapper = require( 'mvc/form/form-wrapper' ),
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
            '(/)admin(/)forms(/)(:form_id)' : 'show_forms'
        },

        authenticate: function( args, name ) {
            return Galaxy.user && Galaxy.user.id && Galaxy.user.get( 'is_admin' );
        },

        show_users: function() {
            this.page.display( new GridView( { url_base: Galaxy.root + 'admin/users_list', url_data: Galaxy.params, dict_format: true } ) );
        },

        show_forms : function( form_id ) {
            var options = {
                title           : 'Reset passwords',
                url             : 'admin/reset_user_password?' + $.param( Galaxy.params ),
                icon            : 'fa-user'
            };
            this.page.display( new FormWrapper.View ( options ) );
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