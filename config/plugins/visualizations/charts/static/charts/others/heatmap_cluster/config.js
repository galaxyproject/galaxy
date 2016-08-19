define( [ 'plugin/charts/others/heatmap/config' ], function( default_config ) {
    return $.extend( true, {}, default_config, {
        title       : 'Clustered Heatmap',
        category    : 'Data processing (requires \'charts\' tool from Toolshed)',
        execute     : 'heatmap',
        keywords    : 'small medium large'
    });
});