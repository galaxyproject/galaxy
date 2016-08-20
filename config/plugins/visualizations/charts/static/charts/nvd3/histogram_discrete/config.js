define( [ 'plugin/charts/utilities/tabular-form' ], function( default_config ) {
    return $.extend(true, {}, default_config, {
        library     : 'NVD3',
        tag         : 'svg',
        title       : 'Discrete Histogram',
        category    : 'Data processing (requires \'charts\' tool from Toolshed)',
        keywords    : 'nvd3',
        datatype    : 'tabular',
        columns     : {
            x : {
                title       : 'Observations',
                is_label    : true
            }
        }
    });
});