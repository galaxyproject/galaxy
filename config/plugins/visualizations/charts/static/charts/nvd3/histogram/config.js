define(['plugin/charts/forms/default'], function(config_default) {
return $.extend(true, {}, config_default, {
    library     : 'NVD3',
    tag         : 'svg',
    title       : 'Histogram',
    category    : 'Data processing (requires \'charts\' tool from Toolshed)',
    execute     : 'histogram',
    keywords    : 'small medium large',
    columns     : {
        y : {
            title       : 'Observations',
            is_numeric  : true
        }
    },
    settings    : {
        x_axis_label : {
            init : 'Values'
        },
        y_axis_label : {
            init : 'Density'
        },
        y_axis_type : {
            init : 'f'
        },
        y_axis_precision : {
            init : '.2'
        }
    }
});

});