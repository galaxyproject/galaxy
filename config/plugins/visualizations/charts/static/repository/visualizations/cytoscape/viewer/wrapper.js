define( [ 'utilities/utils', 'utilities/sifjson', 'plugins/cytoscape/cytoscape' ], function( Utils, SIF, Cytoscape ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            var self = this,
                chart    = options.chart,
                dataset  = options.dataset,
                settings = options.chart.settings,
                data_content = null,
                cytoscape = null,
                astar_root = "",
                astar_destination = "",
                sif_file_ext = "sif",
                highlighted_color = settings.get( 'color_picker_highlighted' );

            Utils.get( {
                url     : dataset.download_url,
                success : function( content ) {
                    // Select data for the graph
                    if( dataset.file_ext === sif_file_ext ) {
                        data_content = SIF.SIFJS.parse( content ).content;
                    }
                    else {
                        data_content = content.elements ? content.elements : content;
                    }
                    try {
                        cytoscape = Cytoscape({
                            container: document.getElementById( options.targets[ 0 ] ),
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
                                self.run_search_algorithm( cytoscape, ele.id(), search_algorithm, self );
                            }
                            else if( settings.get( 'graph_traversal' ) !== "" ) {
                                self.run_traversal_type( cytoscape, ele.id(), traversal_type );
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
        },
        run_search_algorithm: function( cytoscape, root_id, type, self ) {
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
        },
        run_traversal_type: function( cytoscape, root_id, type ) {
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
        }
    });
});
