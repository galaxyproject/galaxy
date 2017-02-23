define( [ 'utilities/utils', 'plugins/cytoscape/cytoscape' ], function( Utils, Cytoscape ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            var chart    = options.chart;
            var dataset  = options.dataset;
            Utils.get( {
                url     : dataset.download_url,
                success : function( content ) {
                    try {
                        Cytoscape({
			    container: document.getElementById( options.targets[ 0 ] ),
			    boxSelectionEnabled: false,
			    autounselectify: true,
			    layout: {
			        name: 'grid'
			    },
			    style: [{
			        selector: 'node',
			        style: {
				    'background-color': '#18e018'
			        }
			    },
			    {
			        selector: 'edge',
			        style: {
				    'curve-style': 'haystack',
				    'haystack-radius': 0,
				    'width': 5,
				    'opacity': 0.5,
				    'line-color': '#ad1a66'
			        }
			    }],
                            elements: content
                        });
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
