define(['plugin/charts/others/heatmap/config'], function(config_default) {

return $.extend(true, {}, config_default, {
    title       : 'Clustered Heatmap',
    category    : 'Data processing (requires \'charts\' tool from Toolshed)',
    execute     : 'heatmap',
    keywords    : 'small medium large'
});

});