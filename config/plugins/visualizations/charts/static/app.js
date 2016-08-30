/**
 *  Main application class.
 */
define( [ 'mvc/ui/ui-modal', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc', 'utils/utils', 'plugin/components/storage', 'plugin/components/model', 'utils/deferred', 'plugin/views/viewer', 'plugin/views/editor' ],
    function( Modal, Portlet, Ui, Utils, Storage, Chart, Deferred, Viewer, Editor ) {
    return Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            require( [ 'remote/build/types' ], function( Types ) {
                self.types = Types;
                Utils.get({
                    url     : Galaxy.root + 'api/datasets/' + options.config.dataset_id,
                    cache   : true,
                    success : function( dataset ) {
                        self.dataset = dataset;
                        self._build( options );
                    }
                });
            }, function( err ) {
                self.$el.append( $( '<div/>' ).addClass( 'errormessagelarge' )
                        .append( $( '<p/>' ).text( 'Unable to access the Charts plugin repository:' ) )
                        .append( $( '<pre/>' ).text( 'charts_plugin_url = ' + remote_root + 'package.json' ) )
                        .append( $( '<p/>' ).html( 'Please verify that your internet connection works properly and that the above base url is correct. Contact your admin if this error persists.' ) ) );
            });
        },

        _build: function( options ) {
            this.options    = options;
            this.modal      = parent.Galaxy && parent.Galaxy.modal || new Modal.View();
            this.chart      = new Chart();
            this.storage    = new Storage( this.chart, this.types, options );
            this.deferred   = new Deferred();
            this.viewer     = new Viewer( this );
            this.editor     = new Editor( this );
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