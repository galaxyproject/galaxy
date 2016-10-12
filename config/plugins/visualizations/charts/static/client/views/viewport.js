/**
 *  The viewport creates and manages the dom elements used by the visualization plugins to draw the chart.
 *  This is the last class of the charts core classes before handing control over to the visualization plugins.
 */
define( [ 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc', 'utils/utils' ], function( Portlet, Ui, Utils ) {
    return Backbone.View.extend({
        initialize: function( app, options ) {
            var self = this;
            this.app = app;
            this.chart = this.app.chart;
            this.options = options;
            this.setElement( $( '<div/>' ).addClass( 'charts-viewport' )
                                          .append( $( '<div/>' ).addClass( 'info' )
                                                                .append( $( '<span/>' ).addClass( 'icon' ) )
                                                                .append( $( '<span/>' ).addClass( 'text' ) ) ) );
            this.$info = this.$( '.info' );
            this.$icon = this.$( '.icon' );
            this.$text = this.$( '.text' );
            this._fullscreen( this.$el, 55 );
            this._createContainer( 'div' );
            this.chart.on( 'redraw', function() {
                self.app.deferred.execute( function( process ) {
                    self._draw( process, self.chart );
                });
            });
            this.chart.on( 'set:state', function() {
                var $container = self.$( '.charts-viewport-container' );
                var $info = self.$info;
                var $icon = self.$icon;
                var $text = self.$text;
                $icon.removeClass();
                $info.show();
                $text.html( self.chart.get( 'state_info' ) );
                var state = self.chart.get( 'state' );
                switch ( state ) {
                    case 'ok':
                        $info.hide();
                        $container.show();
                        break;
                    case 'failed':
                        $icon.addClass( 'icon fa fa-warning' );
                        $container.hide();
                        break;
                    default:
                        $icon.addClass( 'icon fa fa-spinner fa-spin' );
                        $container.show();
                }
            });
        },

        /** Show rendered chart */
        show: function() {
            this.$el.show();
        },

        /** Hide chart */
        hide: function() {
            this.$el.hide();
        },

        /** Force resize to fullscreen */
        _fullscreen: function( $el, margin ) {
            $el.css( 'height', $( window ).height() - margin );
            $( window ).resize( function() {
                $el.css( 'height', $( window ).height()  - margin );
            });
        },

        /** A chart may contain multiple sub charts/containers which are created here */
        _createContainer: function( tag, n ) {
            tag = tag || 'div';
            n = n || 1;
            this.$( '.charts-viewport-container' ).remove();
            this.targets = [];
            for ( var i = 0; i < n; i++ ) {
                var container_id = Utils.uid();
                var container_el = $( '<div/>' ).addClass( 'charts-viewport-container' )
                                                .width( parseInt( 100 / n ) + '%' )
                                                .append( $( '<' + tag + ' class="charts-viewport-canvas" />' ).attr( 'id', container_id ) );
                this.$el.append( container_el );
                this.targets.push( container_id );
            }
        },

        /** Draws a new chart by loading and executing the corresponding chart wrapper */
        _draw: function( process, chart ) {
            var self = this;
            var n_panels = chart.settings.get( '__use_panels' ) == 'true' ? chart.groups.length : 1;
            this._createContainer( chart.definition.tag, n_panels );
            chart.state( 'wait', 'Please wait...' );
            require( [ 'repository/build/' + chart.get( 'type' ) ], function( ChartView ) {
                new ChartView( { process: process, chart: chart, dataset: self.app.dataset, targets: self.targets } );
            }, function( err ) {
                chart.state( 'failed', 'Please verify that your internet connection works properly. This visualization could not be accessed in the repository. Please contact the Galaxy Team if this error persists.' );
                console.debug( err );
                process.resolve();
            });
        }
    });
});