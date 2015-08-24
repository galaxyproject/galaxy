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
        x_axis_label : {
            init : 'Breaks'
        },
        y_axis_label : {
            init : 'Density'
        },
        y_axis_type : {
            init : 'f'
        },
        y_axis_precision : {
            init : '2'
        }
    }
});

});