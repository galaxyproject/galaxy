define( [ 'plugin/charts/nvd3/common/config' ], function( nvd3_config ) {
    return $.extend(true, {}, nvd3_config, {
        library     : 'NVD3',
        tag         : 'svg',
        title       : 'Discrete Histogram',
        category    : 'Data processing (requires \'charts\' tool from Toolshed)',
        execute     : 'histogramdiscrete',
        keywords    : 'nvd3 default',
        columns     : {
            x : {
                title       : 'Observations',
                is_label    : true
            }
        }
    });
});