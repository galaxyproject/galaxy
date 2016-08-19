define( [ 'plugin/charts/jqplot/common/config' ], function( plot_config ) {
    return $.extend( true, {}, plot_config, {
        title       : 'Box plot',
        category    : 'Data processing (requires \'charts\' tool from Toolshed)',
        library     : 'jqPlot',
        tag         : 'div',
        execute     : 'boxplot',
        keywords    : 'jqplot default',
        columns     : {
            y : {
                title       : 'Observations',
                is_numeric  : true
            }
        }
    });
});