define( [], function() {
    return {
        title       : 'Cytoscape',
        library     : 'Cytoscape',
        datatypes   : [ 'sif', 'json' ],
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
            },
            directed : {
                label   : 'Directed/Undirected',
                help    : 'Select a kind of edge.',
                type    : 'select',
                display : 'radio',
                value   : '',
                data    : [ { label : 'Directed', value : 'triangle' },
                            { label : 'Undirected', value : '' } ]
            },
            search_algorithm : {
                label   : 'Graph algorithms',
                help    : 'Select a search algorithm.',
                type    : 'select',
                display : 'radio',
                value   : '',
                data    : [ { label : 'Breadth First Search', value : 'bfs' },
                            { label : 'Depth First Search', value : 'dfs' },
                            { label : 'Minimum Spanning Tree (Kruskal)', value : 'kruskal' },
                            { label : 'A*', value : 'astar' },
                            { label : 'None', value : '' } ]
            },
            graph_traversal: {
                label   : 'Graph traversal',
                help    : 'Select a graph traversal type.',
                type    : 'select',
                display : 'radio',
                value   : '',
                data    : [ { label : 'Successors', value : 'successors' },
                            { label : 'Predecessors', value : 'predecessors' },
                            { label : 'Outgoers', value : 'outgoers' },
                            { label : 'Incomers', value : 'incomers' },
                            { label : 'Roots', value : 'roots' },
                            { label : 'Leaves', value : 'leaves' },
                            
                            { label : 'None', value : '' } ]
            },
            choose_red : {
                name  : 'choose_red',
                label : 'Red',
                help  : 'Select red component for highlighted edges',
                type  : 'integer',
                min   : 0,
                max   : 255,
                value : 51
            },
            choose_green : {
                name  : 'choose_green',
                label : 'Green',
                help  : 'Select green component for highlighted edges',
                type  : 'integer',
                min   : 0,
                max   : 255,
                value : 102
            },
            choose_blue : {
                name  : 'choose_blue',
                label : 'Blue',
                help  : 'Select blue component for highlighted edges',
                type  : 'integer',
                min   : 0,
                max   : 255,
                value : 153
            },
            min_zoom : {
                name  : 'min_zoom',
                label : 'Minimum zoom',
                help  : 'Select minimum zoom for the display.',
                type  : 'float',
                min   : 1/10,
                max   : 1,
                value : 1/2
            },
            max_zoom : {
                name  : 'max_zoom',
                label : 'Maximum zoom',
                help  : 'Select maximum zoom for the display.',
                type  : 'float',
                min   : 2,
                max   : 20,
                value : 5
            }
        }
    }
});
