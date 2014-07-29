define(['plugin/charts/nvd3/common/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title       : 'Line chart',
    category    : 'Others',
    zoomable    : true,
    columns     : {
        x : {
            title       : 'Values for x-axis',
            is_label    : true,
            is_auto     : true,
            is_unique   : true
        },
        y : {
            title       : 'Values for y-axis',
            is_numeric  : true
        }
    }
});

});