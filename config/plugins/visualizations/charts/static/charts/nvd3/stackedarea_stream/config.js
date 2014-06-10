define(['plugin/charts/nvd3/common/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title       : 'Stream',
    category    : 'Area charts',
    zoomable    : 'axis',
    keywords    : 'default small',
    showmaxmin  : true,
    columns     : {
        y : {
            title       : 'Values for y-axis',
            is_numeric  : true
        }
    }
});

});