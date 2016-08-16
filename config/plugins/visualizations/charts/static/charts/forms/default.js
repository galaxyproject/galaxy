define([], function() {

    var axis_label_inputs = function( prefix ) {
        return {
            name        : prefix + '_axis_label',
            label       : prefix.toUpperCase() + '-Axis label',
            help        : 'Provide a label for the axis.',
            type        : 'text',
            value       : prefix.toUpperCase() + '-axis',
            placeholder : 'Axis label'
        }
    }

    var axis_precision_inputs = [ { name    : 'precision',
                                    label   : 'Axis tick format',
                                    help    : 'Select the tick format for the axis.',
                                    type    : 'select',
                                    value   : '1',
                                    data    : [ { label : '0.00001', value : '5' },
                                                { label : '0.0001',  value : '4' },
                                                { label : '0.001',   value : '3' },
                                                { label : '0.01',    value : '2' },
                                                { label : '0.1',     value : '1' },
                                                { label : '1',       value : '0' } ] } ];

    var axis_type_inputs = function( prefix ) {
        return {
            type        : 'conditional',
            name        : prefix + '_axis_type',
            test_param  : {
                name        : 'type',
                label       : prefix.toUpperCase() + '-Axis value type',
                type        : 'select',
                value       : 'auto',
                help        : 'Select the value type of the axis.',
                data        : [ { value : 'hide',   label : '-- Do not show values --' },
                                { value : 'auto',   label : 'Auto' },
                                { value : 'f',      label : 'Float' },
                                { value : 'd',      label : 'Integer' },
                                { value : 'e',      label : 'Exponent' },
                                { value : 'p',      label : 'Percent' },
                                { value : 's',      label : 'SI-prefix' } ]
            },
            cases       : [ { value   : 'hide' },
                            { value   : 'auto' },
                            { value   : 'f', inputs: axis_precision_inputs },
                            { value   : 'd' },
                            { value   : 'e', inputs: axis_precision_inputs },
                            { value   : 'p', inputs: axis_precision_inputs },
                            { value   : 's' } ]
        }
    }

    var boolean_inputs = function( name, label, help ) {
        return { name        : name,
                 label       : label,
                 help        : help,
                 type        : 'select',
                 display     : 'radiobutton',
                 value       : 'true',
                 data        : [ { label : 'Yes', value : 'true'  },
                                 { label : 'No',  value : 'false' } ] }
    }

    return {
        title       : '',
        category    : '',
        library     : '',
        tag         : '',
        keywords    : '',
        settings    : [ axis_label_inputs( 'x' ), axis_type_inputs( 'x' ),
                        axis_label_inputs( 'y' ), axis_type_inputs( 'y' ),
                        boolean_inputs( 'show_legend', 'Show legend', 'Would you like to add a legend?' ),
                        boolean_inputs( 'use_panels', 'Use multi-panels', 'Would you like to separate your data into individual panels?' ) ],
        series      : [{
            name        : 'key',
            label       : 'Provide a label',
            type        : 'text',
            placeholder : 'Data label'
        }]
    }
});