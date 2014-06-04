define(['plugin/charts/highcharts/common/config'], function(config) {

return $.extend(true, {}, config, {
    title       : 'Heatmap',
    category    : 'Data processing (requires \'charts\' tool from Toolshed)',
    //execute     : 'heatmap',
    use_panels  : true,
    keywords    : 'default highcharts',
    columns: {
        y: {
            title       : 'Row labels',
            is_label    : true,
            is_numeric  : true
        },
        x: {
            title       : 'Column labels',
            is_label    : true,
            is_numeric  : true
        },
        z: {
            title       : 'Observations',
            is_numeric  : true
        }
    }
});

});