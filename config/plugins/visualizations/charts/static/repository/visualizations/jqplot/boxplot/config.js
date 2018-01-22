define( [ 'visualizations/jqplot/common/config' ], function( plot_config ) {
    return $.extend( true, {}, plot_config, {
        title       : 'Box plot',
        library     : 'jqPlot',
        description : 'Processes tabular data using R and renders a box plot using jqPlot hosted at http://www.jqplot.com.',
        tag         : 'div',
        keywords    : 'jqplot default',
        groups      : {
            y : {
                label       : 'Observations',
                type        : 'data_column',
                is_numeric  : true
            }
        }
    });
});