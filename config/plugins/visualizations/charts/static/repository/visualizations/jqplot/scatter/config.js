define( [ 'visualizations/jqplot/common/config' ], function( plot_config ) {
    return $.extend( true, {}, plot_config, {
        title       : 'Scatter plot',
        description : 'Renders a scatter plot using jqPlot hosted at http://www.jqplot.com.',
        groups      : {
            x : {
                label       : 'Values for x-axis',
                type        : 'data_column',
                is_numeric  : true
            },
            y : {
                label       : 'Values for y-axis',
                type        : 'data_column',
                is_numeric  : true
            }
        }
    });
});