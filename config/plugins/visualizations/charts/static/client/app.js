/**
 *  Main application class.
 */
define( [ 'mvc/ui/ui-modal', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc', 'utils/utils', 'plugin/components/model', 'utils/deferred', 'plugin/views/viewer', 'plugin/views/editor' ],
    function( Modal, Portlet, Ui, Utils, Chart, Deferred, Viewer, Editor ) {
    return Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            require( [ 'repository/build/registry' ], function( Registry ) {
                console.debug( 'app::initialize() - Loaded Registry:' );
                console.debug( Registry );
                Utils.get({
                    url     : Galaxy.root + 'api/datasets/' + options.dataset_id,
                    success : function( dataset ) {
                        self.dataset = dataset;
                        self.types = {};
                        _.each( Registry, function( type, type_id ) {
                            if ( !type.datatypes || type.datatypes.indexOf( dataset.file_ext ) != -1  ) {
                                self.types[ type_id ] = type;
                            }
                        });
                        if ( _.size( self.types ) === 0 ) {
                            self.$el.append( $( '<div/>' ).addClass( 'errormessagelarge' )
                                    .append( $( '<p/>' ).text( 'Unfortunately we could not identify a suitable plugin. Feel free to contact us if you are aware of visualizations for this datatype.' )  ) );
                        } else {
                            self._build( options );
                        }
                    }
                });
            }, function( err ) {
                self.$el.append( $( '<div/>' ).addClass( 'errormessagelarge' )
                        .append( $( '<p/>' ).text( 'Unable to access the plugin repository:' ) )
                        .append( $( '<pre/>' ).text( 'charts_repository_url = ' + repository_root ) )
                        .append( $( '<p/>' ).html( 'Please verify that your internet connection works properly and that the above url is correct. Contact your admin if this error persists.' ) ) );
            });
        },

        _build: function( options ) {
            this.options    = options;
            this.modal      = parent.Galaxy && parent.Galaxy.modal || new Modal.View();
            this.chart      = new Chart( {}, options );
            this.deferred   = new Deferred();
            this.viewer     = new Viewer( this );
            this.editor     = new Editor( this );
            this.$el.append( this.viewer.$el );
            this.$el.append( this.editor.$el );
            this.go( this.chart.load() ? 'viewer' : 'editor' );
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