define( [], function() {
    return {
        axisLabel : function( prefix ) {
            return {
                name        : 'label',
                label       : prefix.toUpperCase() + '-Axis label',
                help        : 'Provide a label for the axis.',
                type        : 'text',
                value       : prefix.toUpperCase() + '-axis',
                placeholder : 'Axis label'
            }
        },
        axisPrecision : function() {
            return { name    : 'precision',
                     label   : 'Axis tick format',
                     help    : 'Select the tick format for the axis.',
                     type    : 'select',
                     value   : '1',
                     data    : [ { label : '0.00001', value : '5' },
                                 { label : '0.0001',  value : '4' },
                                 { label : '0.001',   value : '3' },
                                 { label : '0.01',    value : '2' },
                                 { label : '0.1',     value : '1' },
                                 { label : '1',       value : '0' } ] }
        },
        axisType : function( prefix, options ) {
            options = options || {};
            return {
                type        : 'conditional',
                test_param  : {
                    name        : 'type',
                    label       : prefix.toUpperCase() + '-Axis value type',
                    type        : 'select',
                    value       : options.value || 'auto',
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
                                { value   : 'f', inputs: [ this.axisPrecision() ] },
                                { value   : 'd' },
                                { value   : 'e', inputs: [ this.axisPrecision() ] },
                                { value   : 'p', inputs: [ this.axisPrecision() ] },
                                { value   : 's' } ]
            }
        },
        boolean : function( label, help, value ) {
            return { label       : label,
                     help        : help,
                     type        : 'select',
                     display     : 'radiobutton',
                     value       : value || 'true',
                     data        : [ { label : 'Yes', value : 'true'  },
                                     { label : 'No',  value : 'false' } ] }
        }
    }
});