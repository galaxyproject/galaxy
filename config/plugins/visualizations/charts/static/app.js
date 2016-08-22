/**
 *  Main application class.
 */
define( [ 'mvc/ui/ui-modal', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc', 'utils/utils', 'plugin/components/storage', 'plugin/components/model', 'utils/deferred', 'plugin/views/viewer', 'plugin/views/editor', 'plugin/charts/types' ],
    function( Modal, Portlet, Ui, Utils, Storage, Chart, Deferred, ViewerView, EditorView, Types ) {
    return Backbone.View.extend({
        initialize: function(options){
            this.options = options;
            this.modal = parent.Galaxy && parent.Galaxy.modal || new Modal.View();
            this.types = new Types();
            this.chart = new Chart();
            this.storage = new Storage( this );
            this.deferred = new Deferred();

            // views
            this.viewer_view = new ViewerView( this );
            this.editor_view = new EditorView( this );
            this.$el.append( this.viewer_view.$el );
            this.$el.append( this.editor_view.$el );

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
            this.viewer_view.hide();
            this.editor_view.hide();
            this[ view_id + '_view' ].show();
        },

        /** Returns root path */
        chartPath: function( chart_type ) {
            var path = chart_type.split( /_(.+)/ );
            if ( path.length >= 2 ) {
                return path[ 0 ] + '/' + path[ 1 ];
            }
            console.debug( 'FAILED app:chartPath() - Invalid format: ' + chart_type );
        },

        /** Message */
        showModal: function( title, body ) {
            var self = this;
            this.modal.show( { title: title, body: body, buttons: { 'Close': function() { self.modal.hide() } } } );
        }
    });
});