/** Pie chart wrapper */
define( [ 'utilities/utils', 'visualizations/utilities/tabular-datasets', 'plugins/nvd3/nv.d3', 'style!css!plugins/nvd3/nv.d3.css' ], function( Utils, Datasets ) {
    return Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            var chart = options.chart;
            var targets = options.targets;
            var process = options.process;
            Datasets.request({
                dataset_id      : chart.get( 'dataset_id' ),
                dataset_groups  : chart.groups,
                success         : function( groups ) {
                    for ( var group_index in groups ) {
                        var group = groups[ group_index ];
                        self._drawGroup( chart, group, targets[ group_index ] );
                    }
                    chart.state('ok', 'Pie chart has been drawn.');
                    process.resolve();
                }
            });
        },

        /** Draw group */
        _drawGroup: function( chart, group, canvas_id ) {
            try {
                var self = this;
                var canvas = d3.select( '#' + canvas_id );
                var title = canvas.append( 'text' );
                this._fixTitle( chart, canvas, title, group.key );
                var pie_data = [];
                _.each( group.values, function( value ) {
                    pie_data.push( { y : value.y, x : value.label } );
                });

                // add graph to screen
                nv.addGraph(function() {
                    var legend_visible = chart.settings.get( 'show_legend' ) == 'true';
                    var label_outside = chart.settings.get( 'label_outside' ) == 'true';
                    var label_type = chart.settings.get( 'label_type' );
                    var donut_ratio = parseFloat( chart.settings.get( 'donut_ratio' ) );
                    var chart_3d = nv.models.pieChart()
                        .donut( true )
                        .labelThreshold( .05 )
                        .showLegend( legend_visible )
                        .labelType( label_type )
                        .donutRatio( donut_ratio )
                        .donutLabelsOutside( label_outside );
                    canvas.datum( pie_data ).call( chart_3d );
                    nv.utils.windowResize( function() {
                        chart_3d.update();
                        self._fixTitle( chart, canvas, title, group.key );
                    });
                });
            } catch ( err ) {
                console.log( err );
            }
        },

        /** Fix title */
        _fixTitle: function( chart, canvas, title_element, title_text ) {
            var width = parseInt( canvas.style( 'width' ) );
            var height = parseInt( canvas.style( 'height' ) );
            title_element.attr( 'x', width / 2 )
                         .attr( 'y', height - 10 )
                         .attr( 'text-anchor', 'middle' )
                         .text( title_text );
        }
    });
});
