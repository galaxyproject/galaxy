define(['plugin/charts/jqplot/common/config'], function(plot_config) {

return $.extend(true, {}, plot_config, {
    title       : 'Line chart',
    category    : 'Others',
    columns     : {
        x : {
            title       : 'Values for x-axis',
            is_label    : true,
            is_auto     : true,
            is_unique   : true
        },
        y : {
            title   : 'Values for y-axis',
            is_numeric  : true
        }
    }
});

});