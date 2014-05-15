define([], function() {

return {
    title       : 'Box plot',
    category    : 'Data processing (requires \'charts\' tool from Toolshed)',
    library     : 'highcharts.js',
    tag         : 'div',
    execute     : 'boxplot',
    columns     : {
        y : {
            title   : 'Observations'
        }
    },
    settings    : {
        separator_label  : {
            title       : 'X axis',
            type        : 'separator'
        },
        x_axis_label : {
            title       : 'Axis label',
            info        : 'Provide a label for the axis.',
            type        : 'text',
            init        : 'X-axis',
            placeholder : 'Axis label'
        },
        separator_tick  : {
            title       : 'Y axis',
            type        : 'separator'
        },
        y_axis_label : {
            title       : 'Axis label',
            info        : 'Provide a label for the axis.',
            type        : 'text',
            init        : 'Y-axis',
            placeholder : 'Axis label'
        }
    }
};

});