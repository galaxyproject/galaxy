var _l = require( 'utils/localization' );

var Categories = [
    {   title : 'Server',
        items : [ {
            title   : 'Data types registry',
            url     : 'admin/view_datatypes_registry'
        },{
            title   : 'Data tables registry',
            url     : 'admin/view_tool_data_tables'
        },{
            title   : 'Display applications',
            url     : 'admin/display_applications'
        },{
            title   : 'Manage jobs',
            url     : 'admin/jobs'
        } ]
    }
];

var AdminPanel = Backbone.View.extend({
    initialize: function( page, options ) {
        var config = options.config;
        this.root  = options.root;
            this.model = new Backbone.Model({
            title   : _l( 'Administration' )
        });
        this.setElement( this._template() );
        this.$menu = this.$( '.toolMenu' );
    },

    render : function() {
        var self = this;
        this.$menu.empty();
        _.each( Categories, function( categories ) {
            var $section = $( self._templateSection( categories ) );
            var $entries = $section.find( '.toolSectionBg' );
            _.each( categories.items, function( item ) {
                var $title = $( '<div/>' ).addClass( 'toolTitle' ).text( item.title );
                $entries.append( $title );
                //var $link = $( '<a/>' ).set;
                //'<div class="toolTitle"><a href="${h.url_for( controller="admin", action="view_datatypes_registry" )}" target="galaxy_main">Data types registry</a></div>'
            });
            self.$menu.append( $section );
        });
    },

    /** override to include inital menu dom and workflow section */
    _templateSection : function( options ) {
        return [
            '<div class="toolSectionList">',
                '<div class="toolSectionTitle">' + options.title + '</div>',
                '<div class="toolSectionBody">',
                    '<div class="toolSectionBg"/>',
                '</div>',
            '</div>'
        ].join('');
    },

    /** override to include inital menu dom and workflow section */
    _template : function() {
        return [
            '<div class="toolMenuContainer">',
                '<div class="toolMenu"/>',
            '</div>'


                /*<div class="toolSectionPad"></div>
                <div class="toolSectionTitle">Tools and Tool Shed</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                    %if trans.app.tool_shed_registry and trans.app.tool_shed_registry.tool_sheds:
                        <div class="toolTitle"><a href="${h.url_for( controller='admin_toolshed', action='browse_tool_sheds' )}" target="galaxy_main">Search Tool Shed</a></div>
                        %if trans.app.config.enable_beta_ts_api_install:
                            <div class="toolTitle"><a href="${h.url_for( controller='admin_toolshed', action='browse_toolsheds' )}" target="galaxy_main">Search Tool Shed (Beta)</a></div>
                        %endif
                    %endif
                    %if installing_repository_ids:
                        <div class="toolTitle"><a href="${h.url_for( controller='admin_toolshed', action='monitor_repository_installation', tool_shed_repository_ids=installing_repository_ids )}" target="galaxy_main">Monitor installing repositories</a></div>
                    %endif
                    %if is_repo_installed:
                        <div class="toolTitle"><a href="${h.url_for( controller='admin_toolshed', action='browse_repositories' )}" target="galaxy_main">Manage installed tools</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin_toolshed', action='reset_metadata_on_selected_installed_repositories' )}" target="galaxy_main">Reset metadata</a></div>
                    %endif
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='package_tool' )}" target="galaxy_main">Download local tool</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='tool_versions' )}" target="galaxy_main">Tool lineage</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='reload_tool' )}" target="galaxy_main">Reload a tool's configuration</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='review_tool_migration_stages' )}" target="galaxy_main">Review tool migration stages</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='tool_errors' )}" target="galaxy_main">View Tool Error Logs</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='sanitize_whitelist' )}" target="galaxy_main">Manage Display Whitelist</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='manage_tool_dependencies' )}" target="galaxy_main">Manage Tool Dependencies</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">User Management</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='users' )}" target="galaxy_main">Users</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='groups' )}" target="galaxy_main">Groups</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='admin', action='roles' )}" target="galaxy_main">Roles</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='userskeys', action='all_users' )}" target="galaxy_main">API keys</a></div>
                        %if trans.app.config.allow_user_impersonation:
                            <div class="toolTitle"><a href="${h.url_for( controller='admin', action='impersonate' )}" target="galaxy_main">Impersonate a user</a></div>
                        %endif
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">Data</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        %if trans.app.config.enable_quotas:
                            <div class="toolTitle"><a href="${h.url_for( controller='admin', action='quotas' )}" target="galaxy_main">Quotas</a></div>
                        %endif
                        <div class="toolTitle"><a href="${h.url_for( controller='library_admin', action='browse_libraries' )}" target="galaxy_main">Data libraries</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='data_manager' )}" target="galaxy_main">Local data</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">Form Definitions</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a href="${h.url_for( controller='forms', action='browse_form_definitions' )}" target="galaxy_main">Form definitions</a></div>
                    </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">Sample Tracking</div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a href="${h.url_for( controller='external_service', action='browse_external_services' )}" target="galaxy_main">Sequencers and external services</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='request_type', action='browse_request_types' )}" target="galaxy_main">Request types</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='requests_admin', action='browse_requests' )}" target="galaxy_main">Sequencing requests</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='requests_common', action='find_samples', cntrller='requests_admin' )}" target="galaxy_main">Find samples</a></div>
                    </div>
                </div>
            </div>
        </div>
    </div>*/

        ].join('');
    },

    toString : function() { return 'adminPanel' }
});

module.exports = AdminPanel;
