define([], function() {

return {
    title   : 'Histogram',
    mode    : 'execute',
    columns : {
        y : {
            title   : 'Derive frequencies'
        }
    },
    settings  : {
        x_axis_label : {
            title   : 'Axis label (x)',
            info    : 'Provide a label for the \'x\' axis.',
            type    : 'text',
            init    : 'Breaks',
            placeholder : 'Axis label'
        },
        bin_size : {
            title   : 'Number of Bins',
            info    : 'Provide the number of histogram bins. The parsed data will be evenly distributed into bins according to the minimum and maximum values of the dataset.',
            type    : 'slider',
            init    : 10,
            min     : 10,
            max     : 1000,
        }
    }
};

});