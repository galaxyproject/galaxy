define( [ 'plugin/charts/utilities/tabular-form', 'plugin/plugins/nvd3/nv.d3' ], function( default_config ) {
    return $.extend( true, {}, default_config, {
        title       : '',
        category    : '',
        library     : 'NVD3',
        tag         : 'svg',
        keywords    : 'nvd3 default',
        exports     : [ 'svg', 'pdf' ],
        groups      : {
            color: {
                label       : 'Pick a series color',
                type        : 'color'
            },
            tooltip : {
                label       : 'Data point labels',
                type        : 'data_column',
                is_label    : true,
                is_auto     : true,
                is_unique   : true
            }
        }
    });
});