define( [ 'plugin/charts/jqplot/common/config' ], function( default_config ) {
    return $.extend( true, {}, default_config, {
        title       : 'Discrete Histogram',
        category    : 'Data processing (requires \'charts\' tool from Toolshed)',
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