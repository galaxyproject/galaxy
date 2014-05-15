define([], function() {

return {
    title       : 'Heatmap',
    category    : 'Data processing (requires \'charts\' tool from Toolshed)',
    library     : '',
    tag         : 'div',
    use_panels  : true,
    execute     : 'heatmap',
    
    // columns
    columns : {
        row_label : {
            title       : 'Row labels',
            is_label    : true
        },
        col_label : {
            title       : 'Column labels',
            is_label    : true
        },
        value : {
            title       : 'Observations'
        },
    },
    
    // settings
    settings: {
        /*limit : {
            title       : 'Limit',
            info        : 'Which to ranked clusters would you like to visualize',
            type        : 'select',
            init        : '20',
            data        : [
                {
                    label   : '20',
                    value   : '20'
                },
                {
                    label   : '30',
                    value   : '30'
                },
                {
                    label   : '40',
                    value   : '40'
                },
                {
                    label   : '50',
                    value   : '50'
                },
                {
                    label   : '60',
                    value   : '60'
                },
                {
                    label   : '70',
                    value   : '70'
                },
                {
                    label   : '80',
                    value   : '80'
                },
                {
                    label   : '90',
                    value   : '90'
                },
                {
                    label   : '100',
                    value   : '100'
                }
            ]
        },*/
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
        },
       
        sorting : {
            title       : 'Sorting',
            info        : 'How should the columns be clustered?',
            type        : 'select',
            init        : 'hclust',
            data        : [
                {
                    label   : 'Read from dataset',
                    value   : 'hclust'
                },
                {
                    label   : 'Sort column and row labels',
                    value   : 'byboth'
                },
                {
                    label   : 'Sort column labels',
                    value   : 'bycolumns'
                },
                {
                    label   : 'Sort by rows',
                    value   : 'byrow'
                }
            ]
        }
    },
    
    // menu definition
    menu : function() {
        return {
            color_set : this.settings.color_set
        }
    }
};

});