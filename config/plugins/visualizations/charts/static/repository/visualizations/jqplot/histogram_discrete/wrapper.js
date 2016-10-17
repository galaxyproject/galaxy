define( [ 'visualizations/utilities/tabular-utilities', 'utilities/jobs', 'visualizations/jqplot/common/wrapper' ], function( Utilities, Jobs, Plot ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            Jobs.request( options.chart, Utilities.buildJobDictionary( options.chart, 'histogramdiscrete' ), function( dataset ) {
                var dataset_groups = new Backbone.Collection();
                options.chart.groups.each( function( group, index ) {
                    dataset_groups.add({
                        __data_columns: { x: { is_label: true }, y: { is_numeric: true } },
                        x     : 0,
                        y     : index + 1,
                        key   : group.get( 'key' )
                    });
                });
                options.dataset_id = dataset.id;
                options.dataset_groups = dataset_groups;
                options.makeConfig = function( groups, plot_config ){
                    $.extend( true, plot_config, {
                        seriesDefaults: { renderer: $.jqplot.BarRenderer },
                        axes: { xaxis: { min : -1 }, yaxis: { pad : 1.2 } }
                    });
                };
                new Plot( options );
            });
        }
    });
});