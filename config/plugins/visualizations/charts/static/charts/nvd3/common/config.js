define(['plugin/plugins/nvd3/nv.d3'], function() {

return {
    title       : '',
    category    : '',
    library     : 'NVD3',
    tag         : 'svg',
    keywords    : 'default nvd3',
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
        x_axis_type : {
            title       : 'Axis value type',
            info        : 'Select the value type of the axis.',
            type        : 'select',
            init        : 'auto',
            data        : [
                {
                    label   : '-- Do not show values --',
                    value   : 'hide',
                    hide    : ['x_axis_tick']
                },
                {
                    label   : 'Auto',
                    value   : 'auto',
                    hide    : ['x_axis_tick']
                },
                {
                    label   : 'Float',
                    value   : 'f',
                    show    : ['x_axis_tick']
                },
                {
                    label   : 'Exponent',
                    value   : 'e',
                    show    : ['x_axis_tick']
                },
                {
                    label   : 'Integer',
                    value   : 'd',
                    hide    : ['x_axis_tick']
                },
                {
                    label   : 'Percentage',
                    value   : 'p',
                    show    : ['x_axis_tick']
                },
                {
                    label   : 'Rounded',
                    value   : 'r',
                    show    : ['x_axis_tick']
                },
                {
                    label   : 'SI-prefix',
                    value   : 's',
                    show    : ['x_axis_tick']
                }
            ]
        },
        x_axis_tick : {
            title       : 'Axis tick format',
            info        : 'Select the tick format for the axis.',
            type        : 'select',
            init        : '.1',
            data        : [
                {
                    label   : '0.00001',
                    value   : '.5'
                },
                {
                    label   : '0.0001',
                    value   : '.4'
                },
                {
                    label   : '0.001',
                    value   : '.3'
                },
                {
                    label   : '0.01',
                    value   : '.2'
                },
                {
                    label   : '0.1',
                    value   : '.1'
                },
                {
                    label   : '1',
                    value   : '1'
                }
            ]

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
        },
        y_axis_type : {
            title       : 'Axis value type',
            info        : 'Select the value type of the axis.',
            type        : 'select',
            init        : 'auto',
            data        : [
                {
                    label   : '-- Do not show values --',
                    value   : 'hide',
                    hide    : ['y_axis_tick']
                },
                {
                    label   : 'Auto',
                    value   : 'auto',
                    hide    : ['y_axis_tick']
                },
                {
                    label   : 'Float',
                    value   : 'f',
                    show    : ['y_axis_tick']
                },
                {
                    label   : 'Exponent',
                    value   : 'e',
                    show    : ['y_axis_tick']
                },
                {
                    label   : 'Integer',
                    value   : 'd',
                    hide    : ['y_axis_tick']
                },
                {
                    label   : 'Percentage',
                    value   : 'p',
                    show    : ['y_axis_tick']
                },
                {
                    label   : 'Rounded',
                    value   : 'r',
                    show    : ['y_axis_tick']
                },
                {
                    label   : 'SI-prefix',
                    value   : 's',
                    show    : ['y_axis_tick']
                }
            ]
        },
        y_axis_tick : {
            title       : 'Axis tick format',
            info        : 'Select the tick format for the axis.',
            type        : 'select',
            init        : '.1',
            data        : [
                {
                    label   : '0.00001',
                    value   : '.5'
                },
                {
                    label   : '0.0001',
                    value   : '.4'
                },
                {
                    label   : '0.001',
                    value   : '.3'
                },
                {
                    label   : '0.01',
                    value   : '.2'
                },
                {
                    label   : '0.1',
                    value   : '.1'
                },
                {
                    label   : '1',
                    value   : '1'
                }
            ]

        },
        separator_legend : {
            title       : 'Others',
            type        : 'separator'
        },
        show_legend : {
            title       : 'Show legend',
            info        : 'Would you like to add a legend?',
            type        : 'radiobutton',
            init        : 'true',
            data        : [
                {
                    label   : 'Yes',
                    value   : 'true'
                },
                {
                    label   : 'No',
                    value   : 'false'
                }
            ]
        },
        use_panels : {
            title       : 'Use multi-panels',
            info        : 'Would you like to separate your data into individual panels?',
            type        : 'radiobutton',
            init        : 'false',
            data        : [
                {
                    label   : 'Yes',
                    value   : 'true'
                },
                {
                    label   : 'No',
                    value   : 'false'
                }
            ]
        }
    }
};

});