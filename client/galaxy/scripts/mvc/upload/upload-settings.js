/** This renders the content of the settings popup, allowing users to specify flags i.e. for space-to-tab conversion **/
define( [ 'utils/utils' ], function( Utils ) {
    return Backbone.View.extend({
        options: {
            class_check     : 'fa-check-square-o',
            class_uncheck   : 'fa-square-o',
            parameters      : [{
                id          : 'space_to_tab',
                title       : 'Convert spaces to tabs',
            },{
                id          : 'to_posix_lines',
                title       : 'Use POSIX standard'
            }]
        },

        initialize: function( options ) {
            var self = this;
            this.model = options.model;
            this.setElement( $( '<div/>' ).addClass( 'upload-settings' ) );
            this.$el.append( $( '<div/>' ).addClass( 'upload-settings-cover' ) );
            this.$el.append( $( '<table/>' ).addClass( 'upload-settings-table ui-table-striped' ).append( '<tbody/>' ) );
            this.$cover = this.$( '.upload-settings-cover' );
            this.$table = this.$( '.upload-settings-table > tbody' );
            this.listenTo ( this.model, 'change', this.render, this );
            this.model.trigger( 'change' );
        },

        render: function() {
            var self = this;
            this.$table.empty();
            _.each( this.options.parameters, function( parameter ) {
                var $checkbox = $( '<div/>' ).addClass( 'upload-' + parameter.id + ' upload-icon-button fa' )
                                             .addClass( self.model.get( parameter.id ) && self.options.class_check || self.options.class_uncheck )
                                             .on( 'click', function() {
                                                self.model.get( 'enabled' ) && self.model.set( parameter.id, !self.model.get( parameter.id ) )
                                             });
                self.$table.append( $( '<tr/>' ).append( $( '<td/>' ).append( $checkbox ) )
                                                .append( $( '<td/>' ).append( parameter.title ) ) )
            });
            this.$cover[ this.model.get( 'enabled' ) && 'hide' || 'show' ]();
        }
    });
});