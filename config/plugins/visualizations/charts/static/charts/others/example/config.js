define([], function() {
    return {
        title       : 'Example',
        category    : 'Developer Examples',
        library     : 'Custom',
        tag         : 'svg',
        keywords    : 'others',
        groups      : {
            x : { type : 'data_column', is_numeric : true, label : 'Bubble x-position' },
            y : { type : 'data_column', is_numeric : true, label : 'Bubble y-position' },
            z : { type : 'data_column', is_numeric : true, label : 'Bubble size' }
        },
        settings    : {
            use_panels : { label : 'Use multiple panels', help : 'Do you want to draw all data series into a individual panels?', type : 'boolean' }
        }
    }
});