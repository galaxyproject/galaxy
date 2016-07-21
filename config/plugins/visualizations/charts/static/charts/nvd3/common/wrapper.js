/**
 *  This is the common wrapper for nvd3 based visualizations.
 */
define( [ 'plugin/charts/tools' ], function( Tools ) {
    return Backbone.View.extend({
        initialize: function( app, options ) {
            var self = this;
            this.options = options;
            options.render = function( canvas_id, groups ) {
                return self.render( canvas_id, groups )
            };
            Tools.panelHelper( app, options );
        },

        render: function( canvas_id, groups ) {
            var self = this;
            var chart       = this.options.chart;
            var type        = this.options.type;
            var makeConfig  = this.options.makeConfig;
            var d3chart = nv.models[ type ]();
            nv.addGraph( function() {
                try {
                    d3chart.xAxis.axisLabel( chart.settings.get( 'x_axis_label' ) );
                    d3chart.yAxis.axisLabel( chart.settings.get( 'y_axis_label' ) ).axisLabelDistance( 30 );
                    d3chart.options( { showControls: false } );
                    d3chart.showLegend && d3chart.showLegend(chart.settings.get('show_legend') == 'true');
                    self._makeAxes( d3chart, groups, chart.settings );
                    makeConfig && makeConfig( d3chart );
                    chart.settings.get( 'use_panels' ) === 'true' && d3chart.options( { showControls: false } );
                    d3chart.xAxis.showMaxMin( false );
                    d3chart.yAxis.showMaxMin( chart.definition.showmaxmin );
                    d3chart.tooltipContent( function( key, x, y, graph ) {
                        return '<h3>' + ( graph.point.tooltip || key ) + '</h3>';
                    });
                    if ( $( '#' + canvas_id ).length > 0 ) {
                        var canvas = d3.select( '#' + canvas_id );
                        canvas.datum( groups ).call( d3chart );
                        if ( chart.definition.zoomable && chart.definition.zoomable != 'native' ) {
                            d3chart.clipEdge && d3chart.clipEdge( true );
                            Tools.addZoom({
                                xAxis  : d3chart.xAxis,
                                yAxis  : d3chart.yAxis,
                                yDomain: d3chart.yDomain,
                                xDomain: d3chart.xDomain,
                                redraw : function() { d3chart.update() },
                                svg    : canvas
                            });
                        }
                        nv.utils.windowResize( d3chart.update );
                    }
                } catch ( err ) {
                    chart.state( 'failed', err );
                }
            });
            return true;
        },

        /** Format axes ticks */
        _makeAxes: function( d3chart, groups, settings ) {
            var categories = Tools.makeCategories( groups );
            function makeTickFormat( id ) {
                Tools.makeTickFormat({
                    categories  : categories.array[ id ],
                    type        : settings.get( id + '_axis_type' ),
                    precision   : settings.get( id + '_axis_precision' ),
                    formatter   : function( formatter ) {
                        formatter && d3chart[ id + 'Axis' ].tickFormat( function( value ) {
                            return formatter( value );
                        });
                    }
                });
            };
            makeTickFormat( 'x' );
            makeTickFormat( 'y' );
        }
    });
});