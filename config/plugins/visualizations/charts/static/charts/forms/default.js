define([], function() {

return {
    title       : '',
    category    : '',
    library     : '',
    tag         : '',
    keywords    : '',
    query_limit : 0,
    settings    : {
        separator_x  : {
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
                    label       : '-- Do not show values --',
                    value       : 'hide',
                    operations  : {
                        hide    : ['x_axis_precision']
                    }
                },
                {
                    label   : 'Auto',
                    value   : 'auto',
                    operations  : {
                        hide    : ['x_axis_precision']
                    }
                },
                {
                    label   : 'Float',
                    value   : 'f',
                    operations  : {
                        show    : ['x_axis_precision']
                    }
                },
                {
                    label   : 'Exponent',
                    value   : 'e',
                    operations  : {
                        show    : ['x_axis_precision']
                    }
                },
                {
                    label   : 'Integer',
                    value   : 'd',
                    operations  : {
                        hide    : ['x_axis_precision']
                    }
                },
                {
                    label   : 'Percentage',
                    value   : 'p',
                    operations  : {
                        show    : ['x_axis_precision']
                    }
                },
                {
                    label   : 'SI-prefix',
                    value   : 's',
                    operations  : {
                        hide    : ['x_axis_precision']
                    }
                }
            ]
        },
        x_axis_precision : {
            title       : 'Axis tick format',
            info        : 'Select the tick format for the axis.',
            type        : 'select',
            init        : '1',
            data        : [
                {
                    label   : '0.00001',
                    value   : '5'
                },
                {
                    label   : '0.0001',
                    value   : '4'
                },
                {
                    label   : '0.001',
                    value   : '3'
                },
                {
                    label   : '0.01',
                    value   : '2'
                },
                {
                    label   : '0.1',
                    value   : '1'
                },
                {
                    label   : '1',
                    value   : '0'
                }
            ]

        },
        separator_y  : {
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
                    label       : '-- Do not show values --',
                    value       : 'hide',
                    operations  : {
                        hide    : ['y_axis_precision']
                    }
                },
                {
                    label   : 'Auto',
                    value   : 'auto',
                    operations  : {
                        hide    : ['y_axis_precision']
                    }
                },
                {
                    label   : 'Float',
                    value   : 'f',
                    operations  : {
                        show    : ['y_axis_precision']
                    }
                },
                {
                    label   : 'Exponent',
                    value   : 'e',
                    operations  : {
                        show    : ['y_axis_precision']
                    }
                },
                {
                    label   : 'Integer',
                    value   : 'd',
                    operations  : {
                        hide    : ['y_axis_precision']
                    }
                },
                {
                    label   : 'Percentage',
                    value   : 'p',
                    operations  : {
                        show    : ['y_axis_precision']
                    }
                },
                {
                    label   : 'SI-prefix',
                    value   : 's',
                    operations  : {
                        hide    : ['y_axis_precision']
                    }
                }
            ]
        },
        y_axis_precision : {
            title       : 'Axis tick format',
            info        : 'Select the tick format for the axis.',
            type        : 'select',
            init        : '1',
            data        : [
                {
                    label   : '0.00001',
                    value   : '5'
                },
                {
                    label   : '0.0001',
                    value   : '4'
                },
                {
                    label   : '0.001',
                    value   : '3'
                },
                {
                    label   : '0.01',
                    value   : '2'
                },
                {
                    label   : '0.1',
                    value   : '1'
                },
                {
                    label   : '1',
                    value   : '0'
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