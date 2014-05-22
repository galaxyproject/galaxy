define(['plugin/charts/nvd3/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title       : 'Stacked horizontal',
    category    : 'Bar diagrams',
    settings    : {
        x_axis_type : {
            init : 'hide'
        }
    },
    columns     : {
        y : {
            title   : 'Values for y-axis'
        }
    }
});

});