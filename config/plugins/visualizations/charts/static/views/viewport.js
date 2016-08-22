/**
 *  The viewport creates and manages the dom elements used by the visualization plugins to draw the chart.
 *  Additionally, this class creates default request strings and request dictionaries parsed to the visualization plugins.
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

            // use full screen for viewer
            this._fullscreen( this.$el, 55 );

            // prevent window scrolling
            var initial_overflow = $( 'body' ).css( 'overflow' );
            this.$el.on( 'mouseover', function() {
                $( 'body' ).css( 'overflow', 'hidden' );
            }).on('mouseout', function() {
                $( 'body' ).css( 'overflow', initial_overflow );
            });

            // create container element
            this._createContainer( 'div' );

            // link redraw trigger
            var self = this;
            this.chart.on( 'redraw', function() {
                self.app.deferred.execute( function( process ) {
                    self._draw( process, self.chart );
                });
            });

            // link status handler
            this.chart.on( 'set:state', function() {
                var $container = self.$el.find( '.charts-viewport-container' );
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
            n = n || 1;
            for ( var i in this.container_list ) {
                this.container_list[ i ].remove();
            }
            this.container_list = [];
            this.canvas_list = [];
            for ( var i = 0; i < n; i++ ) {
                var container_id = Utils.uid();
                var container_el = $( '<div/>' ).addClass( 'charts-viewport-container' )
                                                .width( parseInt( 100 / n ) + '%' )
                                                .append( $( '<div/>' ).attr( 'id', 'menu' ) )
                                                .append( $( '<' + tag + ' class="charts-viewport-canvas" />' ).attr( 'id', container_id ) );
                this.$el.append( container_el );
                this.container_list[ i ] = container_el;
                this.canvas_list[ i ] = container_id;
            }
        },

        /** Draws a new chart by loading and executing the corresponding chart wrapper */
        _draw: function( process, chart ) {
            var self = this;
            var n_panels = chart.settings.get( 'use_panels' ) === 'true' ? chart.groups.length : 1;
            this._createContainer( chart.definition.tag, n_panels );
            chart.state( 'wait', 'Please wait...' );
            require( [ 'plugin/charts/' + this.app.chartPath( chart.get( 'type' ) ) + '/wrapper' ], function( ChartView ) {
                new ChartView( self.app, { process : process, chart : chart, canvas_list : self.canvas_list } );
            });
        }
    });
});
