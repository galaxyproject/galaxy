define( [ 'visualizations/utilities/tabular-form' ], function( default_config ) {
    return $.extend( true, {}, default_config, {
        title       : 'Pie chart',
        description : 'Renders a pie chart using NVD3 hosted at http://www.nvd3.org.',
        library     : 'NVD3',
        tag         : 'svg',
        keywords    : 'nvd3 default',
        datatypes   : [ 'tabular', 'csv' ],
        exports     : [ 'png', 'svg', 'pdf' ],
        use_panels  : 'yes',
        groups      : {
            label : {
                label       : 'Labels',
                type        : 'data_column',
                is_label    : true,
                is_auto     : true
            },
            y : {
                label       : 'Values',
                type        : 'data_column',
                is_numeric  : true
            }
        },
        settings : {
            donut_ratio : {
                label       : 'Donut ratio',
                help        : 'Determine how large the donut hole will be.',
                type        : 'float',
                value       : 0.5,
                max         : 1,
                min         : 0.0
            },
            show_legend : {
                label       : 'Show legend',
                help        : 'Would you like to add a legend?',
                type        : 'select',
                display     : 'radiobutton',
                value       : 'false',
                data        : [ { label : 'Yes', value : 'true'  }, { label : 'No',  value : 'false' } ]
            },
            label_type  : {
                type        : 'conditional',
                test_param  : {
                    name        : 'type',
                    label       : 'Donut label',
                    type        : 'select',
                    value       : 'percent',
                    help        : 'What would you like to show for each slice?',
                    data        : [ { value : 'hide',    label : '-- Nothing --' },
                                    { value : 'key',     label : 'Label column' },
                                    { value : 'percent', label : 'Percentage' } ]
                },
                cases       : [ { value   : 'hide' },
                                { value   : 'key',     inputs: [ { name     : 'label_outside',
                                                                   label    : 'Show outside',
                                                                   help     : 'Would you like to show labels outside the donut?',
                                                                   type     : 'select',
                                                                   display  : 'radiobutton',
                                                                   value    : 'true',
                                                                   data     : [ { label : 'Yes', value : 'true'  },
                                                                                { label : 'No',  value : 'false' } ] } ] },
                                { value   : 'percent', inputs: [ { name     : 'label_outside',
                                                                   label    : 'Show outside',
                                                                   help     : 'Would you like to show labels outside the donut?',
                                                                   type     : 'select',
                                                                   display  : 'radiobutton',
                                                                   value    : 'true',
                                                                   data     : [ { label : 'Yes', value : 'true'  },
                                                                                { label : 'No',  value : 'false' } ] } ] } ]
            }
        }
    });
});