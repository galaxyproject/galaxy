define( [ 'plugin/charts/nvd3/common/config', 'plugin/charts/forms/inputs' ], function( nvd3_config, Inputs ) {
    return $.extend( true, {}, nvd3_config, {
        title       : 'Stacked horizontal',
        category    : 'Bar diagrams',
        settings    : {
            x_axis_type : Inputs.axisType( 'x_axis_type', { value: 'hide' } )
        },
        columns     : {
            x : {
                title       : 'Values for x-axis',
                is_label    : true,
                is_auto     : true,
                is_unique   : true
            },
            y : {
                title       : 'Values for y-axis',
                is_numeric  : true
            }
        }
    });
});