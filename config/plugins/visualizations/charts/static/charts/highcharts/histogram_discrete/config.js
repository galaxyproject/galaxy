define(['plugin/charts/highcharts/common/config'], function(config) {

return $.extend(true, {}, config, {
    title       : 'Discrete Histogram',
    category    : 'Data processing (requires \'charts\' tool from Toolshed)',
    execute     : 'histogramdiscrete',
    keywords    : 'highcharts',
    columns     : {
        y : {
            title       : 'Observations',
            is_label    : true
        }
    },
    settings    : {
        x_axis_label : {
            init : 'Labels'
        },
        y_axis_label : {
            init : 'Density'
        }
    }
});

});