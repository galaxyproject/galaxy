// dependencies
define(['plugin/charts/nvd3/bar/config',
        'plugin/charts/nvd3/bar_stacked/config',
        'plugin/charts/nvd3/bar_horizontal/config',
        'plugin/charts/nvd3/bar_horizontal_stacked/config',
        'plugin/charts/nvd3/line_focus/config',
        'plugin/charts/nvd3/pie/config',
        'plugin/charts/nvd3/stackedarea_full/config',
        'plugin/charts/nvd3/stackedarea_stream/config',
        'plugin/charts/nvd3/histogram/config',
        'plugin/charts/nvd3/histogram_discrete/config',
        'plugin/charts/nvd3/line/config',
        'plugin/charts/nvd3/scatter/config',
        'plugin/charts/nvd3/stackedarea/config',
        'plugin/charts/flot/bar/config',
        'plugin/charts/dygraph/bar/config',
        'plugin/charts/others/boxplot/config',
        ], function(nvd3_bar,
                    nvd3_bar_stacked,
                    nvd3_bar_horizontal,
                    nvd3_bar_horizontal_stacked,
                    nvd3_line_focus,
                    nvd3_pie,
                    nvd3_stackedarea_full,
                    nvd3_stackedarea_stream,
                    nvd3_histogram,
                    nvd3_histogram_discrete,
                    nvd3_line,
                    nvd3_scatter,
                    nvd3_stackedarea,
                    flot_bar,
                    dygraph_bar,
                    others_boxplot
            ) {

// widget
return Backbone.Model.extend(
{
    // types
    defaults: {
        'nvd3_bar'                          : nvd3_bar,
        'nvd3_bar_stacked'                  : nvd3_bar_stacked,
        'nvd3_bar_horizontal'               : nvd3_bar_horizontal,
        'nvd3_bar_horizontal_stacked'       : nvd3_bar_horizontal_stacked,
        'nvd3_line_focus'                   : nvd3_line_focus,
        'nvd3_stackedarea'                  : nvd3_stackedarea,
        'nvd3_stackedarea_full'             : nvd3_stackedarea_full,
        'nvd3_stackedarea_stream'           : nvd3_stackedarea_stream,
        'nvd3_pie'                          : nvd3_pie,
        'nvd3_line'                         : nvd3_line,
        'nvd3_scatter'                      : nvd3_scatter,
        'nvd3_histogram'                    : nvd3_histogram,
        'nvd3_histogram_discrete'           : nvd3_histogram_discrete,
        'flot_bar'                          : flot_bar,
        //'dygraph_bar'                       : dygraph_bar,
        //'others_boxplot'                    : others_boxplot
    }
});

});