define( [ 'plugin/charts/jqplot/common/config' ], function( plot_config ) {
    return $.extend( true, {}, plot_config, {
        title       : 'Box plot',
        category    : 'Data processing (requires \'charts\' tool from Toolshed)',
        library     : 'jqPlot',
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