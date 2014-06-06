define(['plugin/charts/highcharts/common/config'], function(config) {

return $.extend(true, {}, config, {
    title       : 'Scatter plot',
    category    : 'Others',
    keywords    : 'highcharts',
    columns     : {
        x : {
            title       : 'Values for x-axis',
            is_numeric  : true
        },
        y : {
            title       : 'Values for y-axis',
            is_numeric  : true
        }
    }
});

});