// dependencies
define(['plugin/charts/nvd3_bar/config',
        'plugin/charts/nvd3_bar_stacked/config',
        'plugin/charts/nvd3_bar_horizontal/config',
        'plugin/charts/nvd3_bar_horizontal_stacked/config',
        'plugin/charts/nvd3_histogram/config',
        'plugin/charts/nvd3_histogram_discrete/config',
        'plugin/charts/nvd3_line/config',
        'plugin/charts/nvd3_line_focus/config',
        'plugin/charts/nvd3_pie/config',
        'plugin/charts/nvd3_scatter/config',
        'plugin/charts/nvd3_stackedarea/config',
        'plugin/charts/nvd3_stackedarea_full/config',
        'plugin/charts/nvd3_stackedarea_stream/config',
        'plugin/charts/highcharts_boxplot/config',
        'plugin/charts/heatmap/config',
        ], function(nvd3_bar,
                    nvd3_bar_stacked,
                    nvd3_bar_horizontal,
                    nvd3_bar_horizontal_stacked,
                    nvd3_histogram,
                    nvd3_histogram_discrete,
                    nvd3_line,
                    nvd3_line_focus,
                    nvd3_pie,
                    nvd3_scatter,
                    nvd3_stackedarea,
                    nvd3_stackedarea_full,
                    nvd3_stackedarea_stream,
                    highcharts_boxplot,
                    heatmap
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
        'nvd3_stackedarea'                  : nvd3_stackedarea,
        'nvd3_stackedarea_full'             : nvd3_stackedarea_full,
        'nvd3_stackedarea_stream'           : nvd3_stackedarea_stream,
        'nvd3_line'                         : nvd3_line,
        'nvd3_line_focus'                   : nvd3_line_focus,
        'nvd3_scatter'                      : nvd3_scatter,
        'nvd3_pie'                          : nvd3_pie,
        'nvd3_histogram'                    : nvd3_histogram,
        'nvd3_histogram_discrete'           : nvd3_histogram_discrete,
        'highcharts_boxplot'                : highcharts_boxplot,
        'heatmap'                           : heatmap
    }
});

});