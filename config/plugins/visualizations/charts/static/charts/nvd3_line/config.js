define(['plugin/charts/nvd3/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title       : 'Line chart',
    category    : 'Others',
    columns     : {
        x : {
            title   : 'Values for x-axis',
            is_auto : true
        },
        y : {
            title   : 'Values for y-axis'
        }
    }
});

});