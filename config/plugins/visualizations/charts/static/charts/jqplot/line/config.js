define( [ 'plugin/charts/jqplot/common/config' ], function( plot_config ) {
    return $.extend( true, {}, plot_config, {
        title       : 'Line chart',
        category    : 'Others',
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