define(['plugin/charts/jqplot/common/config'], function(default_config) {

return $.extend(true, {}, default_config, {
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
        }
    }
});

});