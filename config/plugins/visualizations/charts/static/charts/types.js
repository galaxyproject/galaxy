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
        'plugin/charts/nvd3/line/config',
        'plugin/charts/nvd3/scatter/config',
        'plugin/charts/nvd3/stackedarea/config',
        'plugin/charts/jqplot/bar/config',
        'plugin/charts/jqplot/line/config',
        'plugin/charts/jqplot/scatter/config',
        'plugin/charts/jqplot/boxplot/config',
        'plugin/charts/jqplot/histogram_discrete/config',
        'plugin/charts/others/heatmap/config',
        'plugin/charts/others/heatmap_cluster/config'
        ], function(nvd3_bar,
                    nvd3_bar_stacked,
                    nvd3_bar_horizontal,
                    nvd3_bar_horizontal_stacked,
                    nvd3_line_focus,
                    nvd3_pie,
                    nvd3_stackedarea_full,
                    nvd3_stackedarea_stream,
                    nvd3_histogram,
                    nvd3_line,
                    nvd3_scatter,
                    nvd3_stackedarea,
                    jqplot_bar,
                    jqplot_line,
                    jqplot_scatter,
                    jqplot_boxplot,
                    jqplot_histogram_discrete,
                    others_heatmap,
                    others_heatmap_cluster
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
        'jqplot_bar'                        : jqplot_bar,
        'jqplot_histogram_discrete'         : jqplot_histogram_discrete,
        'jqplot_line'                       : jqplot_line,
        'jqplot_scatter'                    : jqplot_scatter,
        'jqplot_boxplot'                    : jqplot_boxplot,
        'others_heatmap'                    : others_heatmap,
        'others_heatmap_cluster'            : others_heatmap_cluster
    }
});

});