define([], function() {
    return {
        title       : 'Example',
        library     : 'Custom',
        tag         : 'svg',
        keywords    : 'others',
        datatypes   : [ 'tabular', 'csv' ],
        use_panels  : 'both',
        description : 'This is a developer example which demonstrates how to implement and configure a basic d3-based plugin for charts.',
        groups      : {
            x : { type : 'data_column', is_numeric : true, label : 'Bubble x-position' },
            y : { type : 'data_column', is_numeric : true, label : 'Bubble y-position' },
            z : { type : 'data_column', is_numeric : true, label : 'Bubble size' }
        }
    }
});