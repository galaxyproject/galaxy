import * as Phylocanvas from "phylocanvas";
_.extend(window.bundleEntries || {}, {
    load: function(options) {
        var chart = options.chart;
        var dataset = options.dataset;
        var settings = options.chart.settings;
        $.ajax( {
            url     : dataset.download_url,
            success : function( content ) {
                try {
                    var tree = Phylocanvas.default.createTree( options.targets[ 0 ] ),
                        node_size = 20,
                        text_size = 20,
                        line_width = 2;

                    // Set different properties of the tree
                    tree.setTreeType( settings.get( 'tree_type' ) );
                    // Set properties related to labels
                    tree.showLabels = settings.get( 'show_labels' ) === "true" ? true : false;
                    tree.alignLabels = settings.get( 'align_labels' ) === "true" ? true : false;
                    // Set properties related to colors
                    tree.branchColour = settings.get( 'edge_color' );
                    tree.highlightColour = settings.get( 'highlighted_color' );
                    tree.selectedColour = settings.get( 'selected_color' );
                    // Set properties related to size
                    tree.setNodeSize( node_size );
                    tree.setTextSize( text_size );
                    tree.lineWidth = line_width;
                    // Show bootstrap confidence levels
                    tree.showBootstrap = settings.get( 'show_bootstrap' ) === "true" ? true : false;
                    tree.showInternalNodeLabels = tree.showBootstrap;
                    // Update font and color for internal nodel labels
                    tree.internalLabelStyle.colour = tree.branchColour;
                    tree.internalLabelStyle.font = tree.font;
                    tree.internalLabelStyle.textSize = tree.textSize;

                    // Register click event on tree
                    tree.on( 'click', function ( e ) {
                        var node = tree.getNodeAtMousePosition( e );
                        // Here collapse action is taking preference.
                        // Whenver collapse and prune both are selected true,
                        // collapse action will be performed
                        // Collapse the selected branch
                        if( settings.get( 'collapse_branch' ) === "true" ) {
                            tree.branches[ node.id ].collapsed = true;
                            tree.draw();
                        }// Prune the selected branch
                        else if( settings.get( 'prune_branch' ) === "true" ) {
                            tree.branches[ node.id ].pruned = true;
                            tree.draw();
                        }
                    });
                    // Draw the phylogenetic tree
                    tree.load( content );
                    // Set node shape
                    for(var j = 0, length = tree.leaves.length; j < length; j++) {
                        tree.leaves[ j ].nodeShape = settings.get( 'node_shape' );
                    }
                    tree.draw();
                    chart.state( 'ok', 'Done.' );
                    options.process.resolve();
                    // Adjust the size of tree on window resize
                    $( window ).resize( function() {
                        tree.fitInPanel( tree.leaves ); tree.draw();
                    } );
                } catch( err ) {
                    chart.state( 'failed', err );
                }
            },
            error: function() {
                chart.state( 'failed', 'Failed to access dataset.' );
                options.process.resolve();
            }
        });
    }
});
