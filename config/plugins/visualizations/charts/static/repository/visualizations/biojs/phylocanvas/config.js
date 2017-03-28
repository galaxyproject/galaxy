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
                value   : 'radial',
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
            show_label: {
                label   : 'Show/Hide labels',
                help    : 'Select false to hide labels',
                type    : 'select',
                display : 'radio',
                value   : 'true',
                data    : [ { label : 'True', value : 'true' },
                            { label : 'False', value : 'false' } ]
            },
        }
    }
});
