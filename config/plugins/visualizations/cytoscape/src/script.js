import Cytoscape from 'cytoscape';

// Public method. Return graph data as JSON
var parse_sif = function( text ) {
    // Private variables and methods
    var nodes = {}, links = {}, content = [];

    // Add a node
    var _getNode = function( id ) {
        if(!nodes[id]) {
            nodes[id] = {id: id};
        }
        return nodes[id];
    };

    // Parse each line of the SIF file
    var _parse = function( line, i ) {
        var source, interaction, j, length;
        line = ( line.split('\t').length > 1 ) ? line.split('\t') : line.split(' ');
        source = _getNode( line[0] );
        interaction = ( line[1] ? line[1] : "" );
        if( line.length && line.length > 0 && line[0] !== "" ) {
            if( interaction !== "" ) {
                // Get all the target nodes for a source
                for ( j = 2, length = line.length; j < length; j++ ) {
                    if( line[j] !== "" ) {
                        // Create an object for each target for the source
                        var target = _getNode( line[j] ),
                        relation_object = {target: target.id,
                            source: source.id,
                            id: source.id + target.id,
                            relation: interaction.replace(/[''""]+/g, '') }; // Replace quotes in relation
                        if( source < target ) {
                            links[ source.id + target.id + interaction ] = relation_object;
                        } else {
                            links[ target.id + source.id + interaction ] = relation_object;
                        }
                    }
                }
            }
            // Handle the case of single node i.e. no relation with any other node
            // and only the source exists
            else {
                links[ source.id ] = { target: "", source: source.id, id: source.id, relation: "" };
            }
        }
    };

    // Convert to array from objects
    var _toArr = function( obj ) {
        var arr = [];
        for (var key in obj) {
            arr.push( obj[key] );
        }
        return arr;
    };

    // Make content from list of nodes and links
    var _toDataArr = function( nodes, links ) {
        var content = [], node_length, links_length;
        // Make a list of all nodes
        for(var i = 0, node_length = nodes.length; i < node_length; i++) {
            content.push( { 'data': nodes[i] } );
        }
        // Make a list of all relationships among nodes
        for(var i = 0, links_length = links.length; i < links_length; i++) {
            content.push( { 'data': links[i] } );
        }
        return content;
    };

    var lines = text.split('\n'), i, length, nodesarr, linksarr;
    for ( i = 0, length = lines.length; i < length; i++ ) {
        if( lines[i] !== "" ) {
            _parse( lines[i], i );
        }
    }
    nodesarr = _toArr( nodes );
    linksarr = _toArr( links );
    return { content: _toDataArr( nodesarr, linksarr ) };
};

function run_search_algorithm( cytoscape, root_id, type, self ) {
    var algorithm = "", i = 0;
    var selectNextElement = function() {
        if( i < algorithm.path.length ) {
            // Add css class for the selected edge(s)
            algorithm.path[i].addClass( 'searchpath' );
            i++;
            // Animate the edges and nodes coloring 
            // of the path with a delay of 500ms
            setTimeout( selectNextElement, 500 );
        }
    };
    switch( type ) {
        // Breadth First Search
        case "bfs":
            algorithm = cytoscape.elements().bfs( '#' + root_id, function() { }, true );
            selectNextElement();
            break;
        // Depth First Search
        case "dfs":
            algorithm = cytoscape.elements().dfs( '#' + root_id, function() { }, true );
            selectNextElement();
            break;
        // A* search
        case "astar":
            // Choose root and destination for performing A*
            if( !self.astar_root ) {
                self.astar_root = root_id;
            }
            else {
                self.astar_destination = root_id;
            }
            if( self.astar_root && self.astar_destination ) {
                algorithm = cytoscape.elements().aStar({ root: "#" + self.astar_root, goal: "#" + self.astar_destination },function() {}, true);
                selectNextElement();
            }
         default:
            return;
    }
};

function run_traversal_type( cytoscape, root_id, type ) {
    var node_collection;
    switch( type ) {
        // Recursively get edges (and their sources) coming into the nodes in a collection
        case "predecessors":
             node_collection = cytoscape.$( '#' + root_id ).predecessors();
             break;
        // Recursively get edges (and their targets) coming out of the nodes in a collection
        case "successors":
             node_collection = cytoscape.$( '#' + root_id ).successors();
             break;
        // Get edges (and their targets) coming out of the nodes in a collection.
        case "outgoers":
             node_collection = cytoscape.$( '#' + root_id ).outgoers();
             break;
        // Get edges (and their sources) coming into the nodes in a collection.
        case "incomers":
             node_collection = cytoscape.$( '#' + root_id ).incomers();
             break;
        // From the set of calling nodes, get the nodes which are roots
        case "roots":
             node_collection = cytoscape.$( '#' + root_id ).roots();
             break;
        // From the set of calling nodes, get the nodes which are leaves
        case "leaves":
             node_collection = cytoscape.$( '#' + root_id ).leaves();
             break;
        default:
             return;
    }
    // Add CSS class for selected nodes and edges
    node_collection.edges().addClass( 'searchpath' );
    node_collection.nodes().addClass( 'searchpath' );
};

window.bundleEntries = window.bundleEntries || {};
window.bundleEntries.load = function (options) {
    var self = this,
    chart    = options.chart,
    dataset  = options.dataset,
    settings = options.chart.settings,
    data_content = null,
    cytoscape = null,
    sif_file_ext = "sif",
    highlighted_color = settings.get( 'color_picker_highlighted' );
    $.ajax({
        url     : dataset.download_url,
        success : function( content ) {
            // Select data for the graph
            if( dataset.file_ext === sif_file_ext ) {
                data_content = parse_sif( content ).content;
            }
            else {
                data_content = content.elements ? content.elements : content;
            }
            try {
                cytoscape = Cytoscape({
                    container: document.getElementById( options.target ),
                    layout: {
                        name: settings.get( 'layout_name' ),
                        idealEdgeLength: 100,
                        nodeOverlap: 20
                    },
                    minZoom: 0.1,
                    maxZoom: 20,
                    style: [{
                        selector: 'node',
                        style: {
                            'background-color': settings.get( 'color_picker_nodes' ),
                            'opacity': 1,
                            'content': 'data(id)',
                            'text-valign': 'center',
                        }
                    },
                    {
                        selector: 'core',
                        style: {
                                'selection-box-color':'#AAD8FF',
                                'selection-box-border-color':'#8BB0D0',
                                'selection-box-opacity':'0.5'
                        }
                    },
                    {
                        selector: 'edge',
                        style: {
                            'curve-style': settings.get( 'curve_style' ),
                            'haystack-radius': 0,
                            'width': 3,
                            'opacity': 1,
                            'line-color': settings.get( 'color_picker_edges' ),
                            'target-arrow-shape': settings.get( 'directed' ),
                            "overlay-padding":"3px"
                        }
                    },
                    {
                        selector:'node:selected',
                        style: {
                            "border-width": "6px",
                            "border-color": "#AAD8FF",
                            "border-opacity": "0.5",
                            "background-color": "#77828C",
                            "text-outline-color": "#77828C"
                        }
                    },
                    {
                        selector: '.searchpath',
                        style: {
                            'background-color': highlighted_color,
                            'line-color': highlighted_color,
                            'target-arrow-color': highlighted_color,
                            'transition-property': 'background-color, line-color, target-arrow-color',
                            'transition-duration': '0.5s'
                    }
                    }],
                    elements: data_content // Set the JSON data for viewing
                });
                // Highlight the minimum spanning tree found using Kruskal algorithm
                if( settings.get( 'search_algorithm' ) === "kruskal" ) {
                    var kruskal = cytoscape.elements().kruskal();
                    kruskal.edges().addClass( 'searchpath' );
                }
                // Register tap (clicking a node) event on graph nodes
                // On tapping any node, BFS or DFS start from that node
                cytoscape.$( 'node' ).on('tap', function( e ) {
                    var ele = e.cyTarget,
                        search_algorithm = settings.get( 'search_algorithm' ), 
                        traversal_type = settings.get( 'graph_traversal' );
                    // If search algorithm and traversal both are chosen,
                    // search algorithm will take preference
                    if( settings.get( 'search_algorithm' ) !== "" ) {
                        run_search_algorithm( cytoscape, ele.id(), search_algorithm, self );
                    }
                    else if( settings.get( 'graph_traversal' ) !== "" ) {
                        run_traversal_type( cytoscape, ele.id(), traversal_type );
                    }
                });
                chart.state( 'ok', 'Chart drawn.' );
                // Re-renders the graph view when window is resized
                $( window ).resize( function() { cytoscape.layout(); } );
            } catch( err ) {
                chart.state( 'failed', err );
            }
            options.process.resolve();
        },
        error: function() {
            chart.state( 'failed', 'Failed to access dataset.' );
            options.process.resolve();
        }
    });
};
