define(['plugin/charts/_nvd3/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title   : 'Histogram',
    execute : true,
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