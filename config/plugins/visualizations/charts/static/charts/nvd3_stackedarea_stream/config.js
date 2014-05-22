define(['plugin/charts/nvd3/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title       : 'Stream',
    category    : 'Area charts',
    columns     : {
        y : {
            title   : 'Values for y-axis'
        }
    }
});

});