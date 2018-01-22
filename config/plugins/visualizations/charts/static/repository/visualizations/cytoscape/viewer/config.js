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
                help    : 'Select a search algorithm. For Breadth First Search and Depth First Search, please click on any node of the graph. For A*, please click on two nodes, one for the root and another for the destination.',
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
                help    : 'To select a graph traversal type, please click on any node of the graph',
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
            color_picker_nodes : {
                label : 'Select a color for nodes',
                type  : 'color',
                value : '#548DB8'
            },
            color_picker_edges : {
                label : 'Select a color for edges',
                type  : 'color',
                value : '#A5A5A5'
            },
            color_picker_highlighted : {
                label : 'Select a color for highlighted nodes and edges',
                type  : 'color',
                value : '#C00000'
            }
        }
    }
});
