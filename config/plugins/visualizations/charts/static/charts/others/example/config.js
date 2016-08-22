define([], function() {
    return {
        title       : 'Example',
        category    : 'Developer Examples',
        library     : 'Custom',
        tag         : 'svg',
        keywords    : 'others',
        groups      : {
            x : {
                label       : 'Column labels',
                type        : 'data_column',
                is_label    : true,
                is_auto     : true,
                is_unique   : true
            },
            y : {
                label       : 'Row labels',
                type        : 'data_column',
                is_label    : true,
                is_auto     : true,
                is_unique   : true
            },
            z : {
                label       : 'Observation',
                type        : 'data_column',
                is_numeric  : true
            }
        }
    }
});