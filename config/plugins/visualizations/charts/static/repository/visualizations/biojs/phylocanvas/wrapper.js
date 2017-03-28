define( [ 'utilities/utils', 'plugins/biojs/phylocanvas/phylocanvas' ], function( Utils, Phylocanvas ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            var chart    = options.chart,
                dataset  = options.dataset,
                settings = options.chart.settings;

            Utils.get( {
                url     : dataset.download_url,
                success : function( content ) {
                    try {
                        var tree = Phylocanvas.default.createTree( options.targets[ 0 ] );
                        // Set different properties of the tree
                        tree.setTreeType( settings.get( 'tree_type' ) );
                        tree.branchColour = settings.get( 'edge_color' );
                        tree.showLabels = settings.get( 'show_label' ) === "true" ? true : false;
                        // Draw the phylogenetic tree
                        tree.load( content );
                        chart.state( 'ok', 'Done.' );
                        options.process.resolve();
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
});
