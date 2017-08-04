var jQuery = require( 'jquery' ),
    $ = jQuery,
    GalaxyApp = require( 'galaxy' ).GalaxyApp,
    AdminPanel = require( './panels/admin-panel' ),
    FormWrapper = require( 'mvc/form/form-wrapper' ),
    GridView = require( 'mvc/grid/grid-view' ),
    Ui = require( 'mvc/ui/ui-misc' ),
    QueryStringParsing = require( 'utils/query-string-parsing' ),
    Router = require( 'layout/router' ),
    Page = require( 'layout/page' );

window.app = function app( options, bootstrapped ){
    window.Galaxy = new GalaxyApp( options, bootstrapped );
    Galaxy.debug( 'admin app' );

    /** Routes */
    var AdminRouter = Router.extend({
        routes: {
            '(/)admin(/)users' : 'show_users',
            '(/)admin(/)roles' : 'show_roles',
            '(/)admin(/)forms(/)(:form_id)' : 'show_forms'
        },

        authenticate: function( args, name ) {
            return Galaxy.user && Galaxy.user.id && Galaxy.user.get( 'is_admin' );
        },

        show_users: function() {
            this.page.display( new GridView( { url_base: Galaxy.root + 'admin/users_list', url_data: Galaxy.params, dict_format: true } ) );
        },

        show_roles: function() {
            this.page.display( new GridView( { url_base: Galaxy.root + 'admin/roles_list', url_data: Galaxy.params, dict_format: true } ) );
        },

        show_forms : function( form_id ) {
            var form_defs = {
                reset_user_password: {
                    title           : 'Reset passwords',
                    url             : 'admin/reset_user_password?id=' + QueryStringParsing.get( 'id' ),
                    icon            : 'fa-user',
                    submit_title    : 'Save new password',
                    redirect        : Galaxy.root + 'admin/users'
                },
                manage_roles_and_groups_for_user: {
                    url             : 'admin/manage_roles_and_groups_for_user?id=' + QueryStringParsing.get( 'id' ),
                    icon            : 'fa-users',
                    redirect        : Galaxy.root + 'admin/users'
                },
                rename_role: {
                    url             : 'admin/rename_role?id=' + QueryStringParsing.get( 'id' ),
                    icon            : 'fa-users',
                    redirect        : Galaxy.root + 'admin/users'
                }
            };
            this.page.display( new FormWrapper.View ( form_defs[ form_id ] ) );
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