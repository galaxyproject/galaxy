define(['plugin/charts/jqplot/common/config'], function(plot_config) {

return $.extend(true, {}, plot_config, {
    title       : 'Scatter plot',
    category    : 'Others',
    columns     : {
        x : {
            title   : 'Values for x-axis',
            is_numeric  : true
        },
        y : {
            title   : 'Values for y-axis',
            is_numeric  : true
        }
    },
    settings : {
        x_axis_grid : {
            init : 'true'
        }
    }
});

});