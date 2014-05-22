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
        x : {
            title   : 'Values for x-axis',
            is_label: true,
            is_auto : true
        },
        y : {
            title   : 'Values for y-axis'
        }
    }
});

});