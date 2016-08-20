define( [ 'plugin/charts/utilities/tabular-utilities', 'plugin/charts/utilities/tabular-jobs', 'plugin/charts/jqplot/common/wrapper' ], function( Utilities, Jobs, Plot ) {
    return Backbone.Model.extend({
        initialize: function( app, options ) {
            Jobs.request( app, 'histogramdiscrete', function( dataset ) {
                var request_dictionary = Utilities.buildRequestDictionary( app.chart, dataset.id );
                var index = 1;
                var tmp_dict = { id : request_dictionary.id, groups : [] };
                _.each( request_dictionary.groups, function( group ) {
                    tmp_dict.groups.push({
                        key     : group.key,
                        columns : { x: { index : 0, is_label : true }, y: { index : index++ } }
                    });
                });
                options.request_dictionary = tmp_dict;
                options.makeConfig = function( groups, plot_config ){
                    $.extend( true, plot_config, {
                        seriesDefaults: { renderer: $.jqplot.BarRenderer },
                        axes: { xaxis: { min : -1 }, yaxis: { pad : 1.2 } }
                    });
                };
                new Plot( app, options );
            });
        }
    });
});