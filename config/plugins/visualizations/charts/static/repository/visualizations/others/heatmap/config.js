define( [ 'visualizations/utilities/tabular-form' ], function( default_config ) {
    return $.extend( true, {}, default_config, {
        title       : 'Heatmap',
        description : 'Renders a heatmap from matrix data provided in 3-column format (x, y, observation).',
        library     : 'Custom',
        tag         : 'svg',
        keywords    : 'others default',
        zoomable    : true,
        exports     : [ 'png', 'svg', 'pdf' ],
        use_panels  : 'yes',
        groups      : {
            x : {
                label       : 'Column labels',
                type        : 'data_column',
                is_label    : true,
                is_numeric  : true
            },
            y : {
                label       : 'Row labels',
                type        : 'data_column',
                is_label    : true,
                is_numeric  : true
            },
            z : {
                label       : 'Observation',
                type        : 'data_column',
                is_numeric  : true
            }
        },
        settings    : {
            color_set : {
                label       : 'Color scheme',
                help        : 'Select a color scheme for your heatmap',
                type        : 'select',
                value       : 'jet',
                data        : [ { label : 'Cold-to-Hot',                value : 'hot' },
                                { label : 'Cool',                       value : 'cool' },
                                { label : 'Copper',                     value : 'copper' },
                                { label : 'Gray scale',                 value : 'gray' },
                                { label : 'Jet',                        value : 'jet' },
                                { label : 'No-Green',                   value : 'no_green' },
                                { label : 'Ocean',                      value : 'ocean' },
                                { label : 'Polar',                      value : 'polar' },
                                { label : 'Red-to-Green',               value : 'redgreen' },
                                { label : 'Red-to-green (saturated)',   value : 'red2green' },
                                { label : 'Relief',                     value : 'relief' },
                                { label : 'Seismograph',                value : 'seis' },
                                { label : 'Sealand',                    value : 'sealand' },
                                { label : 'Split',                      value : 'split' },
                                { label : 'Wysiwyg',                    value : 'wysiwyg' } ]
            },
            url_template: {
                label       : 'Url template',
                help        : 'Enter a url to link the labels with external sources. Use __LABEL__ as placeholder.',
                type        : 'text',
                value       : '',
                placeholder : 'http://someurl.com?id=__LABEL__'
            }
        }
    });
});