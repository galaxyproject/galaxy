
define(['plugin/charts/nvd3/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title       : 'Histogram',
    category    : 'Data processing (requires \'charts\' tool from Toolshed)',
    execute     : 'histogram',
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