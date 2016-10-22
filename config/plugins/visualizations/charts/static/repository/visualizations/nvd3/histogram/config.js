define( [ 'visualizations/utilities/tabular-form' ], function( default_config ) {
    return $.extend( true, {}, default_config, {
        library     : 'NVD3',
        tag         : 'svg',
        title       : 'Histogram',
        description : 'Uses the R-based `charts` tool to derive a histogram and displays it as regular or stacked bar diagram using NVD3 hosted at http://www.nvd3.org.',
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