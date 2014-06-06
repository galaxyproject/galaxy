define(['plugin/charts/highcharts/common/config'], function(config) {

return $.extend(true, {}, config, {
    title       : 'Heatmap',
    category    : 'Others',
    use_panels  : true,
    keywords    : 'highcharts',
    columns: {
        x: {
            title       : 'Column labels',
            is_label    : true,
            is_numeric  : true
        },
        y: {
            title       : 'Row labels',
            is_label    : true,
            is_numeric  : true
        },
        z: {
            title       : 'Observations',
            is_numeric  : true
        }
    },
    settings: {
        y_axis_grid : {
            init        : '0'
        }
    }
});

});