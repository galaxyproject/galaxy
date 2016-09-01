/**
 *  Main application class.
 */
define( [ 'mvc/ui/ui-modal', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc', 'utils/utils', 'plugin/components/storage', 'plugin/components/model', 'utils/deferred', 'plugin/views/viewer', 'plugin/views/editor', 'plugin/charts/types' ],
    function( Modal, Portlet, Ui, Utils, Storage, Chart, Deferred, Viewer, Editor, Types ) {
    return Backbone.View.extend({
        initialize: function(options){
            this.options = options;
            this.modal = parent.Galaxy && parent.Galaxy.modal || new Modal.View();
            this.types = Types;
            this.chart = new Chart();
            this.storage = new Storage( this );
            this.deferred = new Deferred();

            // views
            this.viewer = new Viewer( this );
            this.editor = new Editor( this );
            this.$el.append( this.viewer.$el );
            this.$el.append( this.editor.$el );

            // pick start screen
            if ( !this.storage.load() ) {
                this.go( 'editor' );
            } else {
                this.go( 'viewer' );
                this.chart.trigger( 'redraw' );
            }
        },

        /** Loads a view and makes sure that all others are hidden */
        go: function( view_id ) {
            $( '.tooltip' ).hide();
            this.viewer.hide();
            this.editor.hide();
            this[ view_id ].show();
        },

        /** Message */
        showModal: function( title, body ) {
            var self = this;
            this.modal.show( { title: title, body: body, buttons: { 'Close': function() { self.modal.hide() } } } );
        },

        /** Split chart type into path components */
        split: function( chart_type ) {
            var path = chart_type.split( /_(.+)/ );
            if ( path.length >= 2 ) {
                return path[ 0 ] + '/' + path[ 1 ];
            } else {
                return chart_type;
            }
        }
    });
});