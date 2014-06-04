define(['plugin/charts/nvd3/common/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title       : 'Line with focus',
    category    : 'Others',
    keywords    : 'default nvd3',
    columns     : {
        y : {
            title       : 'Values for y-axis',
            is_numeric  : true
        }
    }
});

});