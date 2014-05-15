define(['plugin/charts/nvd3/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title       : 'Histogram',
    category    : 'Histograms',
    execute     : 'histogram_discrete',
    columns     : {
        y : {
            title   : 'Observations'
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
        y_axis_tick : {
            init : '.2'
        }
    }
});

});