define(['plugin/charts/highcharts/common/config'], function(config) {

return $.extend(true, {}, config, {
    title       : 'Heatmap',
    category    : 'Data processing (requires \'charts\' tool from Toolshed)',
    execute     : 'heatmap',
    use_panels  : true,
    columns: {
        row_label: {
            title       : 'Row labels',
            is_label    : true
        },
        col_label: {
            title       : 'Column labels',
            is_label    : true
        },
        value: {
            title       : 'Observations',
            is_numeric  : true
        }
    }
});

});