define( [ 'plugin/charts/jqplot/common/config' ], function( plot_config ) {
    return $.extend( true, {}, plot_config, {
        title       : 'Scatter plot',
        category    : 'Others',
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