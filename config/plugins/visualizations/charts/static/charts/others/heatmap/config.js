define(['plugin/charts/forms/default'], function(config_default) {

return $.extend(true, {}, config_default, {
    title       : 'Heatmap',
    category    : 'Others',
    query_limit : 2000,
    library     : 'Custom',
    tag         : 'svg',
    keywords    : 'small',
    zoomable    : true,
    columns     : {
        x : {
            title       : 'Column labels',
            is_label    : true,
            is_numeric  : true,
            is_unique   : true
        },
        y : {
            title       : 'Row labels',
            is_label    : true,
            is_numeric  : true,
            is_unique   : true
        },
        z : {
            title       : 'Observation',
            is_numeric  : true
        }
    },
    settings    : {
        use_panels : {
            init        : 'false',
            hide        : true
        }
    }
});

});