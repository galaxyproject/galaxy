define( [ 'utilities/utils', 'plugins/cytoscape/cytoscape' ], function( Utils, Cytoscape ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            var chart    = options.chart;
            var dataset  = options.dataset;
            Utils.get( {
                url     : dataset.download_url,
                success : function( content ) {
                    try {
                        Cytoscape( Utils.merge( content, {
                            container: $( '#'  + options.targets[ 0 ] ),
                            layout: {
                                name: 'cose',
                                idealEdgeLength: 100,
                                nodeOverlap: 20
                            },
                            style: Cytoscape.stylesheet()
                                            .selector('node')
                                            .css({
                                                'content': 'data(name)',
                                                'text-valign': 'center',
                                                'color': 'white',
                                                'text-outline-width': 2,
                                                'text-outline-color': '#888'
                                            })
                                            .selector('edge')
                                            .css({
                                                'target-arrow-shape': 'triangle'
                                            })
                                            .selector(':selected')
                                            .css({
                                                'background-color': 'black',
                                                'line-color': 'black',
                                                'target-arrow-color': 'black',
                                                'source-arrow-color': 'black'
                                            })
                                            .selector('.faded')
                                            .css({
                                                'opacity': 0.25,
                                                'text-opacity': 0
                                            })
                        } ) );
                        chart.state( 'ok', 'Chart drawn.' );
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
        }
    });
});