define( [], function() {
    return {
        title       : 'Cytoscape',
        library     : 'Cytoscape',
        datatypes   : [ 'json' ],
        keywords    : 'cytoscape graph nodes edges',
        description : 'A viewer based on graph theory/ network library for analysis and visualisation hosted at http://js.cytoscape.org.',
        settings    : {
            curve_style : {
                label   : 'Curve style',
                help    : 'Select a curving method used to separate two or more edges between two nodes.',
                type    : 'select',
                display : 'radio',
                value   : 'haystack',
                data    : [ { label : 'Haystack', value : 'haystack' },
                            { label : 'Bezier', value : 'bezier' },
                            { label : 'Unbundled bezier', value : 'unbundled-bezier' },
                            { label : 'Segments', value: 'segments' } ]
            },
            layout_name : {
                label   : 'Layout name',
                help    : 'Select a kind of position of nodes in graph.',
                type    : 'select',
                display : 'radio',
                value   : 'haystack',
                data    : [ { label : 'Breadth First', value : 'breadthfirst' },
                            { label : 'Circle', value : 'circle' },
                            { label : 'Concentric', value : 'concentric' },
                            { label : 'Cose', value : 'cose' },
                            { label : 'Grid', value : 'grid' },
                            { label : 'Null', value: 'null' },
                            { label : 'Preset', value : 'preset' },
                            { label : 'Random', value : 'random' } ]
            }
        }
    }
});
