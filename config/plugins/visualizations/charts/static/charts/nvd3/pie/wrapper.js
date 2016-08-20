/** Pie chart wrapper */
define( [ 'utils/utils', 'plugin/charts/utilities/tabular-utilities', 'plugin/charts/utilities/tabular-datasets' ], function( Utils, Utilities, Datasets ) {
    return Backbone.View.extend({
        initialize: function( app, options ) {
            var self = this;
            var chart = app.chart;
            var request_dictionary = Utilities.buildRequestDictionary( app.chart );
            var canvas_list = options.canvas_list;
            var process = options.process;
            request_dictionary.success = function( result ) {
                for ( var group_index in result.groups ) {
                    var group = result.groups[ group_index ];
                    self._drawGroup( chart, group, canvas_list[ group_index ] );
                }
                chart.state('ok', 'Pie chart has been drawn.');
                process.resolve();
            }
            Datasets.request( request_dictionary );
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
