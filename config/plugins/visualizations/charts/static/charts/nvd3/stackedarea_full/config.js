define(['plugin/charts/nvd3/common/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title       : 'Expanded',
    zoomable    : 'axis',
    category    : 'Area charts',
    columns     : {
        y : {
            title       : 'Values for y-axis',
            is_numeric  : true
        }
    }
});

});