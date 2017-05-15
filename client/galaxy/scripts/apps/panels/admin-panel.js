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
    },
    {   title : 'Tools and Tool Shed',
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
