define( [ 'visualizations/nvd3/common/config' ], function( nvd3_config ) {
    return $.extend( true, {}, nvd3_config, {
        title       : 'Stacked horizontal',
        description : 'Renders a stacked horizontal bar diagram using NVD3 hosted at http://www.nvd3.org.',
        use_panels  : 'no',
        groups      : {
            x : {
                label       : 'Values for x-axis',
                type        : 'data_column',
                is_label    : true,
                is_auto     : true
            },
            y : {
                label       : 'Values for y-axis',
                type        : 'data_column',
                is_numeric  : true
            }
        }
    });
});