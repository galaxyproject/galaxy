define(['plugin/charts/nvd3/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title       : 'Scatter plot',
    category    : 'Others',
    columns     : {
        x : {
            title   : 'Values for x-axis'
        }
    }
});

});