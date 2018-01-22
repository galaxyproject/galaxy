define( [ 'visualizations/utilities/tabular-form' ], function( default_config ) {
    return $.extend( true, {}, default_config, {
        title       : '',
        library     : 'NVD3',
        tag         : 'svg',
        keywords    : 'nvd3 default',
        exports     : [ 'png', 'svg', 'pdf' ],
        groups      : {
            color: {
                label       : 'Pick a series color',
                type        : 'color'
            },
            tooltip : {
                label       : 'Data point labels',
                type        : 'data_column',
                is_label    : true,
                is_auto     : true
            }
        }
    });
});