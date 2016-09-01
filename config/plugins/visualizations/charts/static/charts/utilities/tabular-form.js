define( [ 'plugin/charts/utilities/tabular-inputs' ], function( Inputs ) {
    return {
        title       : '',
        category    : '',
        library     : '',
        tag         : '',
        keywords    : '',
        datatype    : 'tabular',
        settings    : {
            x_axis_label : Inputs.axisLabel( 'x_axis_label' ),
            x_axis_type  : Inputs.axisType( 'x_axis_type' ),
            y_axis_label : Inputs.axisLabel( 'y_axis_label' ),
            y_axis_type  : Inputs.axisType( 'y_axis_type' ),
            show_legend  : Inputs.boolean( 'show_legend', { label: 'Show legend', help: 'Would you like to add a legend?' } ),
            use_panels   : Inputs.boolean( 'use_panels', { label: 'Use multi-panels', help: 'Would you like to separate your data into individual panels?' } )
        },
        groups      : {
            key: {
                label       : 'Provide a label',
                type        : 'text',
                placeholder : 'Data label',
                value       : 'Data label'
            }
        }
    }
});