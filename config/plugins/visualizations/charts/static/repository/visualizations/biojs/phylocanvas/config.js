define( [], function() {
    return {
        title       : 'Phylogenetic tree visualization',
        library     : 'BioJS',
        datatypes   : [ 'txt', 'nwk' ],
        keywords    : 'biojs phylogenetic tree',
        description : 'A performant, reusable, and extensible tree visualisation library for the web at: http://biojs.io/d/phylocanvas',
        settings    : {
           tree_type : {
                label   : 'Tree types',
                help    : 'Select a tree type.',
                type    : 'select',
                display : 'radio',
                value   : 'rectangular',
                data    : [ { label : 'Circular', value : 'circular' },
                            { label : 'Diagonal', value: 'diagonal' },
                            { label : 'Hierarchial', value : 'hierarchical' },
                            { label : 'Radial', value : 'radial' },
                            { label : 'Rectangular', value : 'rectangular' } ]
            },
            edge_color : {
                label : 'Select a color for the tree',
                type  : 'color',
                value : '#548DB8'
            },
            highlighted_color: {
                label : 'Select a color for the highlighted branch of tree',
                type  : 'color',
                value : '#ff0000'
            },
            selected_color: {
                label : 'Select a color for the selected branch of tree',
                type  : 'color',
                value : '#00b050'
            },
            collapse_branch : {
                label   : 'Collapse the selected branch',
                help    : 'Select true to collapse the selected branch.',
                type    : 'select',
                display : 'radio',
                value   : 'false',
                data    : [ { label : 'True', value : 'true' },
                            { label : 'False', value : 'false' } ]
            },
            prune_branch : {
                label   : 'Prune the selected branch',
                help    : 'Select true to prune the selected branch.',
                type    : 'select',
                display : 'radio',
                value   : 'false',
                data    : [ { label : 'True', value : 'true' },
                            { label : 'False', value : 'false' } ]
            },
            show_labels: {
                label   : 'Show/Hide labels',
                help    : 'Select false to hide labels.',
                type    : 'select',
                display : 'radio',
                value   : 'true',
                data    : [ { label : 'True', value : 'true' },
                            { label : 'False', value : 'false' } ]
            },
            align_labels: {
                label   : 'Align labels',
                help    : 'Select to align the labels of tree. Supported with rectangular, circular, and hierarchical tree types.',
                type    : 'select',
                display : 'radio',
                value   : 'true',
                data    : [ { label : 'True', value : 'true' },
                            { label : 'False', value : 'false' } ]
            },
        }
    }
});
