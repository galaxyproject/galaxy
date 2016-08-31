define( [ 'plugin/charts/nvd3/common/config' ], function( nvd3_config ) {
    return $.extend(true, {}, nvd3_config, {
        title       : 'Regular',
        category    : 'Bar diagrams',
        groups      : {
            x : {
                label       : 'Values for x-axis',
                type        : 'data_column',
                is_label    : true,
                is_auto     : true,
                is_unique   : true
            },
            y : {
                label       : 'Values for y-axis',
                type        : 'data_column',
                is_numeric  : true
            }
        }
    });
});