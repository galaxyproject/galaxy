define( [ 'plugin/charts/utilities/tabular-form' ], function( default_config ) {
    return $.extend( true, {}, default_config, {
        library     : 'NVD3',
        tag         : 'svg',
        title       : 'Histogram',
        category    : 'Data processing (requires \'charts\' tool from Toolshed)',
        keywords    : 'nvd3 default',
        datatype    : 'tabular',
        groups      : {
            key : {
                label       : 'Provide a label',
                type        : 'text',
                placeholder : 'Data label',
                value       : 'Data label'
            },
            color : {
                label       : 'Pick a series color',
                type        : 'color'
            },
            y : {
                label       : 'Observations',
                type        : 'data_column',
                is_numeric  : true
            }
        }
    });
});