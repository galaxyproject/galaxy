var _l = require( 'utils/localization' );

var Categories = [ {
        title : 'Server',
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
    },{
        title : 'Tools and Tool Shed',
        items : [ {
            title   : 'Search Tool Shed',
            url     : 'admin_toolshed/browse_tool_sheds'
        },{
            title   : 'Search Tool Shed (Beta)',
            url     : 'admin_toolshed/browse_toolsheds'
        },{
            title   : 'Monitor installing repositories',
            url     : 'admin_toolshed/monitor_repository_installation'
        },{
            title   : 'Manage installed tools',
            url     : 'admin_toolshed/browse_repositories'
        },{
            title   : 'Download local tool',
            url     : 'admin/package_tool'
        },{
            title   : 'Tool lineage',
            url     : 'admin/tool_versions'
        },{
            title   : 'Reload a tool\'s configuration',
            url     : 'admin/reload_tool'
        },{
            title   : 'Review tool migration stages',
            url     : 'admin/review_tool_migration_stages'
        },{
            title   : 'View Tool Error Logs',
            url     : 'admin/tool_errors'
        },{
            title   : 'Manage Display Whitelist',
            url     : 'admin/sanitize_whitelist'
        },{
            title   : 'Manage Tool Dependencies',
            url     : 'admin/manage_tool_dependencies'
        } ]
    },{
        title : 'User Management',
        items : [ {
            title   : 'Users',
            url     : 'admin/users'
        },{
            title   : 'Groups',
            url     : 'admin/groups'
        },{
            title   : 'Roles',
            url     : 'admin/roles'
        },{
            title   : 'API keys',
            url     : 'userskeys/all_users'
        },{
            title   : 'Impersonate a user',
            url     : 'admin/impersonate'
        } ]
    },{
        title : 'Data',
        items : [ {
            title   : 'Quotas',
            url     : 'admin/quotas'
        },{
            title   : 'Data libraries',
            url     : 'library_admin/browse_libraries'
        },{
            title   : 'Roles',
            url     : 'admin/roles'
        },{
            title   : 'Local data',
            url     : 'data_manager'
        } ]
    },{
        title : 'Form Definitions',
        items : [ {
            title   : 'Form definitions',
            url     : 'forms/browse_form_definitions'
        } ]
    },{
        title : 'Sample Tracking',
        items : [ {
            title   : 'Sequencers and external services',
            url     : 'external_service/browse_external_services'
        },{
            title   : 'Request types',
            url     : 'request_type/browse_request_types'
        },{
            title   : 'Sequencing requests',
            url     : 'requests_admin/browse_requests'
        },{
            title   : 'Find samples',
            url     : 'requests_common/find_samples?cntrller=requests_admin'
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
                var $link = $( '<a/>' ).attr({
                    href    : self.root + item.url,
                    target  : 'galaxy_main'
                });
                $entries.append( $( '<div/>' ).addClass( 'toolTitle' )
                                              .append( $link.text( item.title ) ) );
            });
            self.$menu.append( $section );
        });
    },

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

    _template : function() {
        return [
            '<div class="toolMenuContainer">',
                '<div class="toolMenu"/>',
            '</div>'
        ].join('');
    },

    toString : function() { return 'adminPanel' }
});

module.exports = AdminPanel;
