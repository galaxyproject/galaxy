define(['plugin/charts/nvd3/common/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title       : 'Discrete Histogram',
    category    : 'Data processing (requires \'charts\' tool from Toolshed)',
    execute     : 'histogramdiscrete',
    keywords    : 'small medium large',
    query_limit : 10000,
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