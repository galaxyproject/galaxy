define( [ 'plugin/charts/jqplot/common/config' ], function( default_config ) {
    return $.extend( true, {}, default_config, {
        title       : 'Discrete Histogram',
        category    : 'Data processing (requires \'charts\' tool from Toolshed)',
        execute     : 'histogramdiscrete',
        keywords    : 'jqplot default',
        columns     : {
            x : {
                title       : 'Observations',
                is_label    : true
            }
        }
    });
});