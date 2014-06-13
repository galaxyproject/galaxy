define(['plugin/charts/forms/default'], function(config_default) {

return $.extend(true, {}, config_default, {
    title       : 'Heat map',
    //execute     : 'heatmap',
    category    : 'Others',
    query_limit : 5,
    library     : 'Custom',
    tag         : 'div',
    keywords    : 'small',
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
    }
});

});