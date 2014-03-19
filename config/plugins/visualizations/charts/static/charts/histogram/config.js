define(['plugin/charts/_nvd3/config'], function(nvd3_config) {

return $.extend(true, {}, nvd3_config, {
    title   : 'Histogram',
    execute : true,
    columns : {
        y : {
            title   : 'Observations'
        }
    },
    settings  : {
        x_axis_label : {
            init : 'Breaks'
        },
        y_axis_label : {
            init : 'Density'
        },
        y_axis_tick : {
            init : '.3'
        },
        separator_custom  : {
            title       : 'Advanced',
            type        : 'separator'
        },
        bin_size : {
            title   : 'Bin size',
            info    : 'Provide the bin size for the histogram.',
            type    : 'select',
            init    : 1,
            data        : [
                {
                    label   : '0.001',
                    value   : '0.001'
                },
                {
                    label   : '0.01',
                    value   : '0.01'
                },
                {
                    label   : '0.1',
                    value   : '0.1'
                },
                {
                    label   : '1',
                    value   : '1'
                },
                {
                    label   : '10',
                    value   : '10'
                },
                {
                    label   : '100',
                    value   : '100'
                },
                {
                    label   : '1000',
                    value   : '1000'
                }
            ]
        }
    }
});

});