define([], function() {

return {
    title   : 'Bar diagram',
    columns : {
        y : {
            title   : 'Values for y-axis'
        }
    },
    settings  : {
        x_axis_label : {
            title       : 'Axis label (x)',
            info        : 'Provide a label for the \'x\' axis.',
            type        : 'text',
            init        : '',
            placeholder : 'Axis label'
        },
        y_axis_label : {
            title       : 'Axis label (y)',
            info        : 'Provide a label for the \'y\' axis.',
            type        : 'text',
            init        : '',
            placeholder : 'Axis label'
        }
    }
};

});