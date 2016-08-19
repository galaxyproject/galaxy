define( [ 'plugin/charts/forms/default' ], function( default_config ) {
    return $.extend( true, {}, default_config, {
        library     : 'NVD3',
        tag         : 'svg',
        title       : 'Histogram',
        category    : 'Data processing (requires \'charts\' tool from Toolshed)',
        execute     : 'histogram',
        keywords    : 'nvd3 default',
        columns     : {
            y : {
                title       : 'Observations',
                is_numeric  : true
            }
        },
        series      : [{
            name        : 'key',
            label       : 'Provide a label',
            type        : 'text',
            placeholder : 'Data label',
            value       : 'Data label'
        },{
            name        : 'color',
            label       : 'Pick a series color',
            type        : 'color'
        }]
    });
});