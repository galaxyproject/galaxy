define([], function() {

return {
    title   : 'Heatmap',
    library : '',
    tag     : 'div',
    use_panels  : true,
    columns : {
        col_label : {
            title       : 'Columns',
            is_label    : true
        },
        row_label : {
            title       : 'Rows',
            is_label    : true
        },
        value : {
            title       : 'Observations'
        },
    },
    
    settings: {
        color_set : {
            title       : 'Color scheme',
            info        : 'Select a color scheme for your heatmap',
            type        : 'select',
            init        : 'ocean',
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
                    label   : 'Gebco',
                    value   : 'gebco'
                },
                {
                    label   : 'Globe',
                    value   : 'globe'
                },
                {
                    label   : 'Gray scale',
                    value   : 'gray'
                },
                {
                    label   : 'Haxby',
                    value   : 'haxby'
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
                    label   : 'Rainbow',
                    value   : 'rainbow'
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
                    label   : 'Topo',
                    value   : 'topo'
                },
                {
                    label   : 'Wysiwyg',
                    value   : 'wysiwyg'
                }
            ]
        }
    }
};

});