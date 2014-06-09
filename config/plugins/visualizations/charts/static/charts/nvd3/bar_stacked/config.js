define(['plugin/charts/nvd3/common/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title       : 'Stacked',
    category    : 'Bar diagrams',
    columns     : {
        y : {
            title   : 'Values for y-axis',
            is_numeric  : true
        }
    }
});

});