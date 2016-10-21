define( [ 'visualizations/utilities/tabular-form' ], function( default_config ) {
    return $.extend(true, {}, default_config, {
        library     : 'NVD3',
        tag         : 'svg',
        title       : 'Discrete Histogram',
        description : 'Uses the R-based `charts` tool to derive a histogram for discrete data e.g. text labels. The result is displayed as regular or stacked bar diagram using NVD3 hosted at http://www.nvd3.org.',
        keywords    : 'nvd3',
        datatype    : 'tabular',
        groups      : {
            x : {
                label       : 'Observations',
                type        : 'data_column',
                is_label    : true
            }
        }
    });
});