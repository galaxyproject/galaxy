define(['plugin/charts/forms/default'], function(config_default) {
return $.extend(true, {}, config_default, {
    library     : 'NVD3',
    tag         : 'svg',
    title       : 'Discrete Histogram',
    category    : 'Data processing (requires \'charts\' tool from Toolshed)',
    execute     : 'histogramdiscrete',
    keywords    : 'small medium large',
    columns     : {
        x : {
            title       : 'Observations',
            is_label    : true
        }
    },
    settings    : {
        x_axis_label : Inputs.axisLabel( 'x_axis_label', { value: 'Breaks' } ),
        y_axis_label : Inputs.axisLabel( 'y_axis_label', { value: 'Density' } ),
        y_axis_type  : Inputs.axisType( 'y_axis_type', { value: 'f', precision: '2' } )
    }
});

});