define( [], function() {
    var axisLabel = function( name, options ) {
        options = options || {};
        prefix  = name.substr( 0, 1 );
        return {
            name        : name,
            label       : prefix.toUpperCase() + '-Axis label',
            help        : 'Provide a label for the axis.',
            type        : 'text',
            value       : options.value || prefix.toUpperCase() + '-axis',
            placeholder : 'Axis label'
        }
    }
    var axisType = function( name, options ) {
        options = options || {};
        prefix  = name.substr( 0, 1 );
        var axisPrecision = function() {
            return { name    : 'precision',
                     label   : 'Axis tick format',
                     help    : 'Select the tick format for the axis.',
                     type    : 'select',
                     value   : options.precision || 1,
                     data    : [ { label : '0.00001', value : '5' },
                                 { label : '0.0001',  value : '4' },
                                 { label : '0.001',   value : '3' },
                                 { label : '0.01',    value : '2' },
                                 { label : '0.1',     value : '1' },
                                 { label : '1',       value : '0' } ] }
        }
        return {
            name        : prefix + '_axis_type',
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
                            { value   : 'f', inputs: [ axisPrecision() ] },
                            { value   : 'd' },
                            { value   : 'e', inputs: [ axisPrecision() ] },
                            { value   : 'p', inputs: [ axisPrecision() ] },
                            { value   : 's' } ]
        }
    }
    return {
        title       : '',
        library     : '',
        tag         : '',
        keywords    : '',
        datatypes   : [ 'bed', 'bedgraph', 'bedstrict', 'bed6', 'bed12', 'chrint', 'customtrack', 'gff', 'gff3', 'gtf', 'interval', 'encodepeak', 'wig', 'scidx', 'fli', 'csv', 'tsv', 'eland', 'elandmulti', 'picard_interval_list', 'gatk_dbsnp', 'gatk_tranche', 'gatk_recal', 'ct', 'pileup', 'sam', 'taxonomy', 'tabular', 'vcf', 'xls' ],
        use_panels  : 'both',
        settings    : {
            x_axis_label : axisLabel( 'x_axis_label' ),
            x_axis_type  : axisType( 'x_axis_type' ),
            y_axis_label : axisLabel( 'y_axis_label' ),
            y_axis_type  : axisType( 'y_axis_type' ),
            show_legend  : { type: 'boolean', label: 'Show legend', help: 'Would you like to add a legend?' }
        },
        groups      : {
            key: {
                label       : 'Provide a label',
                type        : 'text',
                placeholder : 'Data label',
                value       : 'Data label'
            }
        }
    }
});