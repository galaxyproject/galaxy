define( [ 'visualizations/others/heatmap/config' ], function( default_config ) {
    return $.extend( true, {}, default_config, {
        title       : 'Clustered Heatmap',
        description : 'Applies hierarchical clustering to a matrix using R. The data has to be provided in 3-column format. The result is displayed as clustered heatmap.',
        keywords    : 'others default'
    });
});