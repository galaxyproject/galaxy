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
            '(/)admin(/)groups' : 'show_groups',
            '(/)admin(/)tool_versions' : 'show_tool_versions',
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

        show_groups: function() {
            this.page.display( new GridView( { url_base: Galaxy.root + 'admin/groups_list', url_data: Galaxy.params, dict_format: true } ) );
        },

        show_tool_versions: function() {
            this.page.display( new GridView( { url_base: Galaxy.root + 'admin/tool_versions_list', url_data: Galaxy.params, dict_format: true } ) );
        },

        show_forms : function( form_id ) {
            var form_defs = {
                reset_user_password: {
                    title           : 'Reset passwords',
                    url             : 'admin/reset_user_password?id=' + QueryStringParsing.get( 'id' ),
                    icon            : 'fa-user',
                    submit_title    : 'Save new password',
                    redirect        : 'admin/users'
                },
                manage_roles_and_groups_for_user: {
                    url             : 'admin/manage_roles_and_groups_for_user?id=' + QueryStringParsing.get( 'id' ),
                    icon            : 'fa-users',
                    redirect        : 'admin/users'
                },
                manage_users_and_groups_for_role: {
                    url             : 'admin/manage_users_and_groups_for_role?id=' + QueryStringParsing.get( 'id' ),
                    redirect        : 'admin/roles'
                },
                manage_users_and_roles_for_group: {
                    url             : 'admin/manage_users_and_roles_for_group?id=' + QueryStringParsing.get( 'id' ),
                    redirect        : 'admin/groups'
                },
                create_role: {
                    url             : 'admin/create_role?id=' + QueryStringParsing.get( 'id' ),
                    redirect        : 'admin/roles'
                },
                create_group: {
                    url             : 'admin/create_group?id=' + QueryStringParsing.get( 'id' ),
                    redirect        : 'admin/groups'
                },
                rename_role: {
                    url             : 'admin/rename_role?id=' + QueryStringParsing.get( 'id' ),
                    redirect        : 'admin/roles'
                },
                rename_group: {
                    url             : 'admin/rename_group?id=' + QueryStringParsing.get( 'id' ),
                    redirect        : 'admin/groups'
                },
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