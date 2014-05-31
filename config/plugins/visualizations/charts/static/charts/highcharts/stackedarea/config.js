define(['plugin/charts/highcharts/common/config'], function(config) {

return $.extend(true, {}, config, {
    title       : 'Regular',
    category    : 'Area charts',
    columns     : {
        x : {
            title       : 'Values for x-axis',
            is_label    : true,
            is_auto     : true,
            is_numeric  : false
        },
        y : {
            title       : 'Values for y-axis',
            is_numeric  : true
        }
    }
});

});