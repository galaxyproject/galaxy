define( [ 'utilities/utils', 'utilities/sifjson', 'plugins/cytoscape/cytoscape' ], function( Utils, SIF, Cytoscape ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            var chart    = options.chart,
                dataset  = options.dataset,
                settings = options.chart.settings,
                data_content = null;
            Utils.get( {
                url     : dataset.download_url,
                success : function( content ) {
                    if( dataset.file_ext === "sif" ) {
                        data_content = SIF.SIFJS.parse( content ).content;
                    }
                    else {
                        data_content = content;
                    }
                    try {
                        var cytoscape = Cytoscape({
			    container: document.getElementById( options.targets[ 0 ] ),
			    boxSelectionEnabled: false,
			    autounselectify: true,
			    layout: {
			        name: settings.get( 'layout_name' )
			    },
                            minZoom: parseFloat( settings.get( 'min_zoom' ) ),
                            maxZoom: parseFloat( settings.get( 'max_zoom' ) ),
			    style: [{
			        selector: 'node',
			        style: {
				    'background-color': '#18e018'
			        }
			    },
			    {
			        selector: 'edge',
			        style: {
				    'curve-style': settings.get( 'curve_style' ),
				    'haystack-radius': 0,
				    'width': 5,
				    'opacity': 1,
				    'line-color': '#ad1a66'
			        }
			    }],
                            elements: data_content
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
