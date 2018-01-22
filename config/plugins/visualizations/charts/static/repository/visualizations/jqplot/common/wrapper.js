/** This is the common wrapper for jqplot based visualizations. */
define( [ 'visualizations/jqplot/common/plot-config', 'visualizations/utilities/tabular-utilities', 'plugins/jqplot/jquery.jqplot', 'plugins/jqplot/jquery.jqplot.plugins', 'style!css!plugins/jqplot/jquery.jqplot.css' ], function( configmaker, Utilities ) {
    return Backbone.View.extend({
        initialize: function( options ) {
            this.options = options;
            var self = this;
            options.render = function( canvas_id, groups ) {
                return self.render( canvas_id, groups )
            };
            Utilities.panelHelper( options );
        },

        /** Draw all data into a single canvas */
        render: function( canvas_id, groups ) {
            var chart               = this.options.chart;
            var makeCategories      = this.options.makeCategories;
            var makeSeries          = this.options.makeSeries;
            var makeSeriesLabels    = this.options.makeSeriesLabels;
            var makeConfig          = this.options.makeConfig;
            var plot_config = configmaker( chart );
            var plot_data = [];
            try {
                this._makeAxes( groups, plot_config, chart.settings );
                if ( makeSeriesLabels ) {
                    plot_config.series = makeSeriesLabels( groups, plot_config );
                } else {
                    plot_config.series = this._makeSeriesLabels( groups );
                }
                if ( makeSeries ) {
                    plot_data = makeSeries( groups, plot_config );
                } else {
                    plot_data = Utilities.makeSeries( groups );
                }
                if ( makeConfig ) {
                    makeConfig( groups, plot_config );
                }
                if ( chart.get( 'state' ) == 'failed' ) {
                    return false;
                }

                // draw graph with default options, overwriting with passed options
                function drawGraph ( opts ) {
                    var canvas = $( '#' + canvas_id );
                    if ( canvas.length == 0 ) {
                        return;
                    }
                    canvas.empty();
                    var plot_cnf = _.extend( _.clone( plot_config ), opts || {} );
                    return plot = $.jqplot( canvas_id, plot_data, plot_cnf );
                }

                // draw plot
                var plot = drawGraph();
                $( window ).on( 'resize', function () { drawGraph() } );
                return true;
            } catch ( err ) {
                this._handleError( chart, err );
                return false;
            }
        },

        /** Make series labels */
        _makeSeriesLabels: function( groups, plot_config ) {
            var series = [];
            for ( var group_index in groups ) {
                series.push( { label: groups[ group_index ].key } );
            }
            return series;
        },

        /** Create axes formatting */
        _makeAxes: function( groups, plot_config, settings ) {
            var makeCategories = this.options.makeCategories;
            var categories = makeCategories ? makeCategories( groups ) : Utilities.makeCategories( groups, [ 'x', 'y' ] );
            function makeAxis (id) {
                Utilities.makeTickFormat({
                    categories  : categories.array[ id ],
                    type        : settings.get( id + '_axis_type|type' ),
                    precision   : settings.get( id + '_axis_type|precision' ),
                    formatter   : function( formatter ) {
                        if ( formatter ) {
                            plot_config.axes[ id + 'axis' ].tickOptions.formatter = function( format, value ) {
                                return formatter( value );
                            };
                        }
                    }
                });
            };
            makeAxis( 'x' );
            makeAxis( 'y' );
        },

        /** Handle error */
        _handleError: function( chart, err ) {
            chart.state( 'failed', err );
        }
    });
});