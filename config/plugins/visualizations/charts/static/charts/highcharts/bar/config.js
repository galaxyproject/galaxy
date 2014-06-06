define(['plugin/charts/highcharts/common/config'], function(config) {

return $.extend(true, {}, config, {
    title       : 'Regular',
    category    : 'Bar diagrams',
    keywords    : 'highcharts',
    columns     : {
        x : {
            title       : 'Values for x-axis',
            is_label    : true,
            is_auto     : true
        },
        y : {
            title       : 'Values for y-axis',
            is_numeric  : true
        }
    }
});

});