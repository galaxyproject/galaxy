define( [ 'visualizations/jqplot/common/config' ], function( default_config ) {
    return $.extend( true, {}, default_config, {
        title       : 'Discrete Histogram',
        description : 'Derives a discrete histogram from tabular data using R and renders a regular bar diagram using jqPlot hosted at http://www.jqplot.com.',
        keywords    : 'jqplot default',
        groups      : {
            x : {
                label       : 'Observations',
                type        : 'data_column',
                is_label    : true
            }
        }
    });
});