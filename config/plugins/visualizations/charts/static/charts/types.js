// dependencies
define(['plugin/charts/nvd3_bardiagram/config',
        'plugin/charts/nvd3_histogram/config',
        'plugin/charts/nvd3_horizontal/config',
        'plugin/charts/nvd3_line/config',
        'plugin/charts/nvd3_linewithfocus/config',
        'plugin/charts/nvd3_piechart/config',
        'plugin/charts/nvd3_scatterplot/config',
        'plugin/charts/nvd3_stackedarea/config',
        'plugin/charts/highcharts_boxplot/config',
        'plugin/charts/heatmap/config',
        ], function(nvd3_bardiagram,
                    nvd3_histogram,
                    nvd3_horizontal,
                    nvd3_line,
                    nvd3_linewithfocus,
                    nvd3_piechart,
                    nvd3_scatterplot,
                    nvd3_stackedarea,
                    highcharts_boxplot,
                    heatmap
            ) {

// widget
return Backbone.Model.extend(
{
    // types
    defaults: {
        'nvd3_bardiagram'       : nvd3_bardiagram,
        'heatmap'               : heatmap,
        'nvd3_horizontal'       : nvd3_horizontal,
        'nvd3_histogram'        : nvd3_histogram,
        'nvd3_line'             : nvd3_line,
        'nvd3_linewithfocus'    : nvd3_linewithfocus,
        'nvd3_piechart'         : nvd3_piechart,
        'nvd3_scatterplot'      : nvd3_scatterplot,
        'nvd3_stackedarea'      : nvd3_stackedarea,
        'highcharts_boxplot'    : highcharts_boxplot
    }
});

});