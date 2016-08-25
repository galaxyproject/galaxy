/**
 *  Main application class.
 */
define( [ 'mvc/ui/ui-modal', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc', 'utils/utils', 'plugin/components/storage', 'plugin/components/model', 'utils/deferred', 'plugin/views/viewer', 'plugin/views/editor', 'plugin/charts/types' ],
    function( Modal, Portlet, Ui, Utils, Storage, Chart, Deferred, Viewer, Editor, Types ) {
    return Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            Utils.get({
                url     : Galaxy.root + 'api/datasets/' + options.config.dataset_id,
                cache   : true,
                success : function( dataset ) {
                    self.dataset = dataset;
                    self._build( options );
                }
            });
        },

        _build: function( options ) {
            this.options = options;
            this.chart = new Chart();
            this.types = Types;
            this.storage = new Storage( this.chart, this.types, options );
            this.deferred = new Deferred();
            this.viewer = new Viewer( this );
            this.editor = new Editor( this );
            this.$el.append( this.viewer.$el );
            this.$el.append( this.editor.$el );
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