define( [ 'plugin/charts/nvd3/common/config' ], function( nvd3_config ) {
    return $.extend( true, {}, nvd3_config, {
        library     : 'NVD3',
        tag         : 'svg',
        title       : 'Histogram',
        category    : 'Data processing (requires \'charts\' tool from Toolshed)',
        execute     : 'histogram',
        keywords    : 'small medium large',
        columns     : {
            y : {
                title       : 'Observations',
                is_numeric  : true
            }
        }
    });
});