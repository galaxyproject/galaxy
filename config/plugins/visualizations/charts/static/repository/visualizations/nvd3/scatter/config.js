define( [ 'visualizations/nvd3/common/config' ], function( nvd3_config ) {
    return $.extend( true, {}, nvd3_config, {
        title       : 'Scatter plot',
        description : 'Renders a scatter plot using NVD3 hosted at http://www.nvd3.org.',
        zoomable    : true,
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