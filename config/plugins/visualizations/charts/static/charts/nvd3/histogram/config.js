define( [ 'plugin/charts/forms/default', 'plugin/charts/forms/inputs' ], function( default_config, Inputs ) {
    return $.extend( true, {}, default_config, {
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
        },
        settings    : {
            x_axis_label : Inputs.axisLabel( 'x_axis_label', { value: 'Values' } ),
            y_axis_label : Inputs.axisLabel( 'y_axis_label', { value: 'Density' } ),
            y_axis_type  : Inputs.axisType( 'y_axis_type', { value: 'f', precision: '2' } )
        }
    });
});