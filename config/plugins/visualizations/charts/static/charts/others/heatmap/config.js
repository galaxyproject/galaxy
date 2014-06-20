define(['plugin/charts/forms/default'], function(config_default) {

return $.extend(true, {}, config_default, {
    title       : 'Heatmap',
    category    : 'Others',
    query_limit : 1000,
    library     : 'Custom',
    tag         : 'svg',
    keywords    : 'small',
    zoomable    : true,
    columns     : {
        x : {
            title       : 'Column labels',
            is_label    : true,
            is_numeric  : true,
            is_unique   : true
        },
        y : {
            title       : 'Row labels',
            is_label    : true,
            is_numeric  : true,
            is_unique   : true
        },
        z : {
            title       : 'Observation',
            is_numeric  : true
        }
    },
    settings    : {
        use_panels : {
            init        : 'true',
            hide        : true
        },
        color_set : {
            title       : 'Color scheme',
            info        : 'Select a color scheme for your heatmap',
            type        : 'select',
            init        : 'jet',
            data        : [
                {
                    label   : 'Cold-to-Hot',
                    value   : 'hot'
                },
                {
                    label   : 'Cool',
                    value   : 'cool'
                },
                {
                    label   : 'Copper',
                    value   : 'copper'
                },
                {
                    label   : 'Gray scale',
                    value   : 'gray'
                },
                {
                    label   : 'Jet',
                    value   : 'jet'
                },
                {
                    label   : 'No-Green',
                    value   : 'no_green'
                },
                {
                    label   : 'Ocean',
                    value   : 'ocean'
                },
                {
                    label   : 'Polar',
                    value   : 'polar'
                },
                {
                    label   : 'Red-to-Green',
                    value   : 'redgreen'
                },
                {
                    label   : 'Red-to-green (saturated)',
                    value   : 'red2green'
                },
                {
                    label   : 'Relief',
                    value   : 'relief'
                },
                {
                    label   : 'Seismograph',
                    value   : 'seis'
                },
                {
                    label   : 'Sealand',
                    value   : 'sealand'
                },
                {
                    label   : 'Split',
                    value   : 'split'
                },
                {
                    label   : 'Wysiwyg',
                    value   : 'wysiwyg'
                }
            ]
        },
        url_template: {
            title       : 'Url template',
            info        : 'Enter a url to link the labels with external sources. Use __LABEL__ as placeholder.',
            type        : 'text',
            init        : '',
            placeholder : 'http://someurl.com?id=__LABEL__'
        }
    }
});

});