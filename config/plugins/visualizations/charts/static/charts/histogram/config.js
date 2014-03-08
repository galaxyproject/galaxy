define(['plugin/charts/_nvd3/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title   : 'Histogram',
    mode    : 'execute',
    columns : {
        x : {
            title   : 'Values for x-axis'
        }
    },
    settings  : {
        x_axis_label : {
            init : 'Breaks'
        },
        y_axis_label : {
            init : 'Density'
        },
        y_axis_tick : {
            init : '.3'
        },
        separator_custom  : {
            title       : 'Advanced',
            type        : 'separator'
        },
        bin_size : {
            title   : 'Number of bins',
            info    : 'Provide the number of histogram bins. The parsed data will be evenly distributed into bins according to the minimum and maximum values of the dataset.',
            type    : 'slider',
            init    : 10,
            min     : 10,
            max     : 1000,
        }
    }
});

});