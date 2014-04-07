define(['plugin/charts/nvd3/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title   : 'Histogram',
    execute : 'histogram',
    columns : {
        y : {
            title   : 'Observations'
        }
    },
    settings  : {
        x_axis_label : {
            init : 'Breaks'
        },
        y_axis_label : {
            init : 'Density'
        }
    }
});

});