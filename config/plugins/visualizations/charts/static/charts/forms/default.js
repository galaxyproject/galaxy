define( [ 'plugin/charts/forms/inputs' ], function( Inputs ) {
    return {
        title       : '',
        category    : '',
        library     : '',
        tag         : '',
        keywords    : '',
        settings    : {
            x_axis_label : Inputs.axisLabel( 'x' ),
            x_axis_type  : Inputs.axisType( 'x' ),
            y_axis_label : Inputs.axisLabel( 'y' ),
            y_axis_type  : Inputs.axisType( 'y' ),
            show_legend  : Inputs.boolean( 'Show legend', 'Would you like to add a legend?' ),
            use_panels   : Inputs.boolean( 'Use multi-panels', 'Would you like to separate your data into individual panels?' )
        },
        series      : [{
            name        : 'key',
            label       : 'Provide a label',
            type        : 'text',
            placeholder : 'Data label'
        }]
    }
});