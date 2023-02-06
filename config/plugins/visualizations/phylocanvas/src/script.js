import * as phylocanvas from "@phylocanvas/phylocanvas.gl";

/* This will be part of the charts/viz standard lib in 23.1 */
const slashCleanup = /(\/)+/g;
function prefixedDownloadUrl(root, path) {
    return `${root}/${path}`.replace(slashCleanup, "/");
}
console.debug(phylocanvas);

_.extend(window.bundleEntries || {}, {
    load: function (options) {
        console.debug("Starting phylocanvas with ", options);
        var chart = options.chart;
        var dataset = options.dataset;
        var settings = options.chart.settings;
        $.ajax({
            url: prefixedDownloadUrl(options.root, dataset.download_url),
            success: function (content) {
                try {
                    const tree = new phylocanvas.PhylocanvasGL(
                        document.getElementById(options.target),
                        {
                            source: content,
                            nodeSize: 20,
                            fontSize: 20,
                            lineWidth: 2,
                            showLabels: settings.get("show_labels") === "true" ? true : false,
                            showLeafLabels: settings.get("show_labels") === "true" ? true : false,
                            interactive: true,
                            nodeShape: settings.get("node_shape"),
                            type: settings.get("tree_type"),
                        },
                        [phylocanvas.plugins.scalebar]
                    );
                    // // Set properties related to labels
                    // tree.alignLabels = settings.get( 'align_labels' ) === "true" ? true : false;
                    // // Set properties related to colors
                    // tree.branchColour = settings.get( 'edge_color' );
                    // tree.highlightColour = settings.get( 'highlighted_color' );
                    // tree.selectedColour = settings.get( 'selected_color' );

                    // tree.showInternalNodeLabels = settings.get( 'show_bootstrap' ) === "true" ? true : false,
                    /*
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
                    */

                    console.debug(tree);
                    chart.state("ok", "Done.");
                    options.process.resolve();
                    // // Adjust the size of tree on window resize
                    // $( window ).resize( function() {
                    //     tree.fitInPanel();
                    //     tree.draw();
                    // } );
                } catch (err) {
                    chart.state("failed", err);
                }
            },
            error: function () {
                chart.state("failed", "Failed to access dataset.");
                options.process.resolve();
            },
        });
    },
});
